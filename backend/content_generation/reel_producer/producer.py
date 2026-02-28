"""
Reel Producer — lecture-clip reels with blurred background effect.

Layout:
- Background: blurred, zoomed-in lecture video filling the vertical frame
- Center: clear lecture video (professor + slides) at native aspect ratio
- Subtitles: karaoke-style word-by-word highlighting, properly synced

Lecture formats:
- zoom:             slides are embedded in the video (default)
- classroom-slides: classroom recording + separate PDF slides (PiP overlay)
- classroom:        classroom recording only, no slides
- slides-only:      PDF slides + MiniMax TTS voiceover (no lecture video)

Audio is the PROFESSOR'S OWN VOICE for video-based formats,
or MiniMax AI voiceover for slides-only mode.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Literal

from .video_compositor import VideoCompositor
from .minimax_video import MinimaxVideoGenerator
from .minimax_tts import MinimaxTTS
from .subtitle_generator import transcribe_clip_words, generate_subtitles_multi

LectureFormat = Literal["zoom", "classroom-slides", "classroom", "slides-only"]


class ReelProducer:

    def __init__(
        self,
        use_minimax_video: bool = False,
        lecture_format: LectureFormat = "zoom",
        slides_pdf: str | None = None,
    ):
        self.compositor = VideoCompositor()
        self.minimax_video = MinimaxVideoGenerator()
        self.tts = MinimaxTTS()
        self.use_minimax_video = use_minimax_video and self.minimax_video.available
        self.lecture_format: LectureFormat = lecture_format
        self.slides_pdf = slides_pdf
        self._source_video: str | None = None
        self._topic_segments: list[dict] = []
        self._transcript_segments: list[dict] = []
        self._slide_renderer = None

    def produce_from_file(
        self,
        pipeline_json: str | Path,
        output_dir: str | Path = "content_generation/output/reels",
        max_reels: int | None = None,
        reel_indices: list[int] | None = None,
    ) -> list[Path]:
        with open(pipeline_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.produce(data, output_dir, max_reels, reel_indices)

    def produce(
        self,
        pipeline_data: dict,
        output_dir: str | Path = "content_generation/output/reels",
        max_reels: int | None = None,
        reel_indices: list[int] | None = None,
    ) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        metadata = pipeline_data.get("metadata", {})
        reel_scripts = pipeline_data.get("reel_scripts", [])
        self._topic_segments = pipeline_data.get("topic_segments", [])
        self._transcript_segments = pipeline_data.get("transcript_segments", [])

        slides_path = self.slides_pdf or metadata.get("slides_path", "")
        slides_path = str(self._resolve_legacy_path(slides_path))

        if self.lecture_format == "slides-only":
            self._init_slide_renderer(slides_path)
            if self._slide_renderer is None:
                raise RuntimeError(
                    f"slides-only mode requires a valid slides PDF. Got: '{slides_path}'"
                )
            if not self.tts.available:
                raise RuntimeError(
                    "slides-only mode requires MiniMax TTS. "
                    "Set MINIMAX_API_KEY and ensure MINIMAX_MOCK is not true."
                )
        else:
            video_path = str(self._resolve_legacy_path(metadata.get("video_path", "")))
            if not video_path or not Path(video_path).exists():
                raise RuntimeError(f"Lecture video required. Got: '{video_path}'")
            self._source_video = str(Path(video_path).resolve())

            if self.lecture_format == "classroom-slides":
                self._init_slide_renderer(slides_path)

        print(f"  Format: {self.lecture_format}")
        if self.lecture_format == "slides-only":
            print(f"  Slides: {slides_path}")
            print(f"  TTS voice: {self.tts.voice_id}")
        else:
            print(f"  Lecture: {metadata.get('video_path', '')}")
            if self.lecture_format == "classroom-slides":
                print(f"  Slides: {slides_path or 'NONE'}")
            print(f"  Transcript: {len(self._transcript_segments)} segments")
        print(f"  MiniMax Video: {'ON' if self.use_minimax_video else 'off'}")

        if reel_indices:
            selected = [(i, reel_scripts[i]) for i in reel_indices if i < len(reel_scripts)]
        else:
            selected = list(enumerate(reel_scripts))
            if max_reels:
                selected = selected[:max_reels]

        total = len(selected)
        produced: list[Path] = []

        print(f"\n{'='*60}")
        print(f"  Producing {total} Reels")
        print(f"{'='*60}")

        t0 = time.time()

        for seq, (idx, script) in enumerate(selected):
            topic = script.get("topic", f"reel_{idx}")
            safe = re.sub(r'[^\w\-]', '_', topic)[:40]
            name = f"reel_{idx:02d}_{safe}"
            print(f"\n[{seq+1}/{total}] {topic}")

            try:
                path = self._produce_reel(script, idx, name, output_dir)
                produced.append(path)
                print(f"  >>> {path.name}")
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()

        elapsed = time.time() - t0
        print(f"\n{'='*60}")
        print(f"  Done: {len(produced)}/{total} reels ({elapsed:.0f}s)")
        print(f"  Output: {output_dir}")
        print(f"{'='*60}\n")

        self._save_manifest(produced, output_dir)
        return produced

    # ------------------------------------------------------------------
    # Per-reel
    # ------------------------------------------------------------------

    def _produce_reel(
        self, script: dict, idx: int, name: str, output_dir: Path
    ) -> Path:
        if self.lecture_format == "slides-only":
            return self._produce_reel_slides_only(script, idx, name, output_dir)

        work = output_dir / f"_work_{name}"
        work.mkdir(parents=True, exist_ok=True)

        visual_dirs = script.get("visual_directions", [])
        source_time = script.get("source_time_range", "")
        target_dur = script.get("target_duration_sec", 30)

        range_start = self._parse_start(source_time)
        range_end = self._parse_end(source_time)
        if range_start <= 0:
            range_start = 60.0
        if range_end <= range_start:
            range_end = range_start + target_dur

        total_range = range_end - range_start
        reel_dur = min(target_dur + 10, 70)

        print(f"  -> {self._fmt(range_start)} - {self._fmt(range_end)} ({total_range:.0f}s) -> {reel_dur}s reel")

        finished_clips, raw_clips, reel_offsets = self._build_clips(
            visual_dirs, range_start, range_end, reel_dur, work, script,
        )

        # Concatenate
        print(f"  -> Stitching {len(finished_clips)} clip(s)...")
        if len(finished_clips) == 1:
            combined = finished_clips[0]
        else:
            combined = work / "combined.mp4"
            self.compositor.concatenate(finished_clips, combined)

        # Word-level subtitles from raw clips
        final = output_dir / f"{name}.mp4"
        self._add_subtitles(combined, raw_clips, reel_offsets, work, final)

        self._cleanup(work)
        return final

    # ------------------------------------------------------------------
    # Slides-only reel production
    # ------------------------------------------------------------------

    def _produce_reel_slides_only(
        self, script: dict, idx: int, name: str, output_dir: Path
    ) -> Path:
        """Produce a reel from slides + MiniMax TTS voiceover (no lecture video)."""
        work = output_dir / f"_work_{name}"
        work.mkdir(parents=True, exist_ok=True)

        narration = script.get("narration_text", "")
        if not narration:
            narration = script.get("hook", "") + " " + script.get("key_takeaway", "")
        narration = narration.strip()
        if not narration:
            narration = f"Let me explain {script.get('topic', 'this concept')} to you."

        # 1) Generate TTS audio
        print(f"  -> Generating TTS voiceover ({len(narration)} chars)...")
        tts_audio = work / "voiceover.mp3"
        tts_result = self.tts.generate(narration, tts_audio)
        if tts_result is None:
            raise RuntimeError("TTS generation failed — check MINIMAX_API_KEY")

        # 2) Render the relevant slide(s) as image
        slide_img = self._get_slide_for_reel(script, 0, work)
        if slide_img is None:
            slide_nums = script.get("related_slide_nums", [])
            page = slide_nums[0] if slide_nums else 1
            slide_img = work / f"slide_{page}.png"
            self._slide_renderer.render_page(page, slide_img)

        # 3) Create video: slide image + TTS audio
        print(f"  -> Compositing slide + audio...")
        raw_video = work / "raw_slide_video.mp4"
        self.compositor.slide_image_to_video(slide_img, tts_audio, raw_video)

        # 4) Subtitles from the TTS audio
        final = output_dir / f"{name}.mp4"
        print("  -> Generating word-level subtitles from TTS audio...")
        words = transcribe_clip_words(raw_video)
        if words:
            from .subtitle_generator import generate_subtitles_multi
            ass_path = work / "subtitles.ass"
            generate_subtitles_multi([(0.0, words)], ass_path)
            print("  -> Burning subtitles...")
            try:
                self.compositor.burn_subtitles(raw_video, ass_path, final)
            except Exception as e:
                print(f"  -> Subtitle burn failed ({e}), skipping")
                shutil.copy2(str(raw_video), str(final))
        else:
            print("  -> No words detected, skipping subtitles")
            shutil.copy2(str(raw_video), str(final))

        self._cleanup(work)
        return final

    # ------------------------------------------------------------------
    # Slide renderer (for classroom-slides mode)
    # ------------------------------------------------------------------

    def _init_slide_renderer(self, slides_path: str):
        if not slides_path or not Path(slides_path).exists():
            print(f"  WARNING: classroom-slides mode but no slides PDF found at '{slides_path}'")
            print(f"           Falling back to classroom (no slides) mode")
            self.lecture_format = "classroom"
            return

        from .slide_renderer import SlideRenderer
        self._slide_renderer = SlideRenderer()
        n = self._slide_renderer.load_pdf(slides_path)
        print(f"  Loaded {n} slides from {slides_path}")

    def _get_slide_for_reel(self, script: dict, seg_idx: int, work: Path) -> Path | None:
        """Render the most relevant slide for this reel/segment."""
        if self._slide_renderer is None:
            return None

        slide_nums = script.get("related_slide_nums", [])
        if not slide_nums:
            topic_segs = self._topic_segments
            for ts in topic_segs:
                if ts.get("topic_name", "") == script.get("topic", ""):
                    slide_nums = ts.get("related_slide_nums", [])
                    break

        if not slide_nums:
            return None

        page = slide_nums[min(seg_idx, len(slide_nums) - 1)]
        out = work / f"slide_{page}.png"
        if out.exists():
            return out

        try:
            self._slide_renderer.render_page(page, out)
            return out
        except Exception as e:
            print(f"      [slides] render failed for page {page}: {e}")
            return None

    # ------------------------------------------------------------------
    # Clip builder
    # ------------------------------------------------------------------

    def _build_clips(
        self,
        visual_dirs: list[dict],
        range_start: float,
        range_end: float,
        reel_dur: float,
        work: Path,
        script: dict | None = None,
    ) -> tuple[list[Path], list[Path], list[float]]:
        """
        Build clips and return (finished_clips, raw_clips, reel_offsets).

        raw_clips: the extracted raw clips (before blur) — used to transcribe
                   for word-level subtitles
        reel_offsets: cumulative time offset of each clip in the final reel
        """
        finished: list[Path] = []
        raws: list[Path] = []
        offsets: list[float] = []
        total_range = range_end - range_start
        script = script or {}

        if not visual_dirs:
            dur = min(reel_dur, total_range)
            clip = work / "clip_default.mp4"
            self._make_clip(clip, range_start, dur, work, script, 0)
            raw = work / "_raw_clip_default.mp4"
            if not raw.exists():
                raw = clip
            finished.append(clip)
            raws.append(raw)
            offsets.append(0.0)
            return finished, raws, offsets

        n_segs = len(visual_dirs)
        seg_dur = reel_dur / n_segs
        reel_cursor = 0.0

        for i, vd in enumerate(visual_dirs):
            actual_dur = max(3, min(seg_dur, reel_dur - reel_cursor))
            if actual_dur < 2:
                break

            lecture_offset = range_start + (i / n_segs) * total_range
            if lecture_offset + actual_dur > range_end:
                lecture_offset = max(range_start, range_end - actual_dur)

            vtype = vd.get("visual_type", "text_overlay")

            clip = work / f"clip_{i:03d}.mp4"
            self._make_clip(clip, lecture_offset, actual_dur, work, script, i)

            raw = work / f"_raw_clip_{i:03d}.mp4"
            if not raw.exists():
                raw = clip

            finished.append(clip)
            raws.append(raw)
            offsets.append(reel_cursor)
            reel_cursor += actual_dur

            print(f"    [{i+1}/{n_segs}] {self._fmt(lecture_offset)} +{actual_dur:.0f}s | {vtype}")

        if not finished:
            dur = min(reel_dur, total_range)
            clip = work / "clip_fallback.mp4"
            self._make_clip(clip, range_start, dur, work, script, 0)
            raw = work / "_raw_clip_fallback.mp4"
            if not raw.exists():
                raw = clip
            finished.append(clip)
            raws.append(raw)
            offsets.append(0.0)

        return finished, raws, offsets

    def _make_clip(
        self, out: Path, start: float, dur: float,
        work: Path, script: dict, seg_idx: int,
    ):
        """Produce one clip using the appropriate layout for the lecture format."""
        if self.lecture_format == "classroom-slides":
            slide_img = self._get_slide_for_reel(script, seg_idx, work)
            if slide_img:
                self.compositor.lecture_blurred_bg_with_slide(
                    self._source_video, start, dur, slide_img, out,
                )
                return

        self.compositor.lecture_blurred_bg(
            self._source_video, start, dur, out,
        )

    # ------------------------------------------------------------------
    # Subtitles
    # ------------------------------------------------------------------

    def _add_subtitles(
        self,
        video: Path,
        raw_clips: list[Path],
        reel_offsets: list[float],
        work: Path,
        final: Path,
    ):
        """
        Transcribe each raw clip with stable-ts for word-level timestamps,
        then generate and burn perfectly synced subtitles.
        """
        print("  -> Generating word-level subtitles...")

        clip_word_lists: list[tuple[float, list[dict]]] = []
        for clip_path, offset in zip(raw_clips, reel_offsets):
            words = transcribe_clip_words(clip_path)
            if words:
                clip_word_lists.append((offset, words))

        if not clip_word_lists:
            print("  -> No words found, skipping subtitles")
            shutil.copy2(str(video), str(final))
            return

        ass_path = work / "subtitles.ass"
        result = generate_subtitles_multi(clip_word_lists, ass_path)

        if result is None:
            shutil.copy2(str(video), str(final))
            return

        print("  -> Burning subtitles...")
        try:
            self.compositor.burn_subtitles(video, ass_path, final)
        except Exception as e:
            print(f"  -> Subtitle burn failed ({e}), skipping")
            shutil.copy2(str(video), str(final))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_legacy_path(self, path: str) -> Path | str:
        """Resolve paths from old 'backend' folder to 'content_generation'."""
        if not path or not path.strip():
            return path
        resolved = path.replace("backend\\", "content_generation\\").replace("backend/", "content_generation/")
        p = Path(resolved)
        if p.exists():
            return str(p.resolve())
        return resolved

    def _parse_ts(self, ts: str) -> float:
        parts = ts.strip().split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0.0

    def _parse_start(self, s: str) -> float:
        if not s:
            return 0.0
        m = re.match(r'([\d:]+)', s)
        return self._parse_ts(m.group(1)) if m else 0.0

    def _parse_end(self, s: str) -> float:
        if not s:
            return 0.0
        m = re.search(r'-\s*([\d:]+)', s)
        return self._parse_ts(m.group(1)) if m else 0.0

    def _fmt(self, sec: float) -> str:
        h, remainder = divmod(int(sec), 3600)
        m, s = divmod(remainder, 60)
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

    def _cleanup(self, d: Path):
        shutil.rmtree(str(d), ignore_errors=True)

    def _save_manifest(self, produced: list[Path], out: Path):
        with open(out / "manifest.json", "w") as f:
            json.dump({
                "reels": [{"file": p.name, "path": str(p)} for p in produced],
                "count": len(produced),
            }, f, indent=2)

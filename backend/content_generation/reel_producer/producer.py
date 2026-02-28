"""
Reel Producer — lecture-clip reels with blurred background effect.

Layout:
- Background: blurred, zoomed-in lecture video filling the vertical frame
- Center: clear lecture video (professor + slides) at native aspect ratio
- Subtitles: karaoke-style word-by-word highlighting, properly synced

Lecture formats:
- video:       any recording where the professor is speaking (Zoom, classroom,
               screen share, etc.). Audio comes from the video itself.
- slides-only: PDF slides + MiniMax TTS voiceover (no lecture video)
- character:   AI-animated character (top half) + slides (bottom half) + TTS voiceover.
               Character is generated via MiniMax Image-to-Video from a reference image.
"""

from __future__ import annotations

import json
import random
import re
import shutil
import time
from pathlib import Path
from typing import Literal

from .video_compositor import VideoCompositor
from .minimax_video import MinimaxVideoGenerator
from .minimax_tts import MinimaxTTS
from .subtitle_generator import transcribe_clip_words, generate_subtitles_multi

LectureFormat = Literal["video", "slides-only", "character", "asmr"]

_CHARACTERS_DIR = Path(__file__).resolve().parent.parent / "input" / "characters"

_ASMR_STYLES: dict[str, str] = {
    "soap_cutting": (
        "Slow satisfying ASMR extreme close-up of a sharp knife slicing through "
        "a colorful bar of soap, crumbling into perfect pieces. Bright lighting, "
        "clean background. [Static shot]"
    ),
    "kinetic_sand": (
        "Satisfying ASMR close-up of hands pressing and cutting through brightly "
        "colored kinetic sand, smooth silky texture, slow deliberate movements. "
        "[Static shot]"
    ),
    "pressure_wash": (
        "Satisfying ASMR pressure washing a dirty concrete surface, a clean bright "
        "stripe appearing with each slow pass of the nozzle. [Static shot]"
    ),
    "slime": (
        "Satisfying ASMR hands slowly stretching and folding glossy iridescent slime, "
        "smooth motion, soft colors. [Static shot]"
    ),
    "sand_cutting": (
        "Satisfying ASMR wire cutting through a perfectly smooth block of colored "
        "kinetic sand, clean straight slices falling away. [Static shot]"
    ),
}


class ReelProducer:

    def __init__(
        self,
        slides_pdf: str | None = None,
        video_path: str | None = None,
        use_minimax_video: bool = False,
    ):
        self.compositor = VideoCompositor()
        self.minimax_video = MinimaxVideoGenerator()
        self.tts = MinimaxTTS()
        self.use_minimax_video = use_minimax_video and self.minimax_video.available
        self.slides_pdf = slides_pdf
        self.video_path_override = video_path
        self._source_video: str | None = None
        self._topic_segments: list[dict] = []
        self._transcript_segments: list[dict] = []
        self._slide_renderer = None
        self._character_image: Path | None = None
        self._available_characters: list[Path] = []

    def produce_from_file(
        self,
        pipeline_json: str | Path,
        output_dir: str | Path = "content_generation/output/reels",
        max_reels: int | None = None,
        reel_indices: list[int] | None = None,
        character_override: list[str] | None = None,
    ) -> list[Path]:
        with open(pipeline_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.produce(
            data, output_dir, max_reels, reel_indices,
            character_override=character_override,
        )

    def produce(
        self,
        pipeline_data: dict,
        output_dir: str | Path = "content_generation/output/reels",
        max_reels: int | None = None,
        reel_indices: list[int] | None = None,
        character_override: list[str] | None = None,
    ) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        metadata = pipeline_data.get("metadata", {})
        reel_scripts = pipeline_data.get("reel_scripts", [])
        self._topic_segments = pipeline_data.get("topic_segments", [])
        self._transcript_segments = pipeline_data.get("transcript_segments", [])

        slides_path = self.slides_pdf or metadata.get("slides_path", "")
        slides_path = str(self._resolve_legacy_path(slides_path))

        raw_video_path = self.video_path_override or metadata.get("video_path", "")
        raw_video_path = str(self._resolve_legacy_path(raw_video_path)) if raw_video_path else ""

        # Detect which formats are needed from the scripts themselves
        active_formats: set[str] = {
            s.get("format", "slides-only") for s in reel_scripts
        }

        # Check if any script actually references slides (has slide_number
        # in visual_directions). Character reels from notes won't have any.
        any_script_has_slides = any(
            any(vd.get("slide_number") for vd in s.get("visual_directions", []))
            for s in reel_scripts
        )
        needs_slides = bool(active_formats & {"slides-only", "asmr"}) or (
            bool(active_formats & {"character"}) and any_script_has_slides
        )
        needs_video = "video" in active_formats
        needs_minimax_video = bool(active_formats & {"character", "asmr"})
        needs_tts = bool(active_formats & {"slides-only", "character", "asmr"})

        if needs_slides:
            self._init_slide_renderer(slides_path)
            if self._slide_renderer is None:
                raise RuntimeError(
                    f"slides/character/asmr mode requires a valid slides PDF. Got: '{slides_path}'"
                )

        if needs_tts and not self.tts.available:
            raise RuntimeError(
                "AI-voiced formats require MiniMax TTS. "
                "Set MINIMAX_API_KEY and ensure MINIMAX_MOCK is not true."
            )

        if needs_video:
            if not raw_video_path or not Path(raw_video_path).exists():
                raise RuntimeError(
                    f"video format requires a lecture video. Got: '{raw_video_path}'. "
                    "Pass --video <path> to override."
                )
            self._source_video = str(Path(raw_video_path).resolve())

        if needs_minimax_video and not self.minimax_video.available:
            raise RuntimeError(
                "character/asmr mode requires MiniMax Video API. "
                "Set MINIMAX_API_KEY and ensure MINIMAX_MOCK is not true."
            )

        # Pre-load available characters
        if "character" in active_formats:
            self._available_characters = self._get_available_characters()
            if not self._available_characters:
                raise RuntimeError(
                    f"character mode requires at least one image in {_CHARACTERS_DIR}/"
                )

        print(f"  Formats in pipeline: {sorted(active_formats)}")
        if needs_slides:
            print(f"  Slides: {slides_path}")
            print(f"  TTS voice: {self.tts.voice_id}")
        if needs_video:
            print(f"  Lecture: {raw_video_path}")
            print(f"  Transcript: {len(self._transcript_segments)} segments")

        if reel_indices:
            selected = [(i, reel_scripts[i]) for i in reel_indices if i < len(reel_scripts)]
        else:
            selected = list(enumerate(reel_scripts))
            if max_reels:
                selected = selected[:max_reels]

        total = len(selected)
        produced: list[Path] = []
        char_override_idx = 0

        print(f"\n{'='*60}")
        print(f"  Producing {total} Reels")
        print(f"{'='*60}")

        t0 = time.time()

        for seq, (idx, script) in enumerate(selected):
            topic = script.get("topic", f"reel_{idx}")
            fmt = script.get("format", "slides-only")
            char_name = script.get("character", "")

            # CLI --characters override: use instead of script's character
            if fmt == "character" and character_override:
                char_name = character_override[char_override_idx % len(character_override)]
                char_override_idx += 1

            safe = re.sub(r'[^\w\-]', '_', topic)[:40]
            name = f"reel_{idx:02d}_{safe}_{fmt.replace('-', '_')}"

            # Resolve character image for this script
            if fmt == "character" and char_name:
                self._character_image = self._resolve_character_image(char_name)
            elif fmt == "character" and self._available_characters:
                self._character_image = random.choice(self._available_characters)

            char_tag = f" — {char_name}" if char_name else ""
            print(f"\n[{seq+1}/{total}] {topic}  [{fmt}{char_tag}]")

            try:
                path = self._produce_reel(script, idx, name, output_dir, format_override=fmt)
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
        self, script: dict, idx: int, name: str, output_dir: Path,
        format_override: LectureFormat | None = None,
    ) -> Path:
        fmt = format_override or script.get("format", "slides-only")
        if fmt == "character":
            return self._produce_reel_character(script, idx, name, output_dir)
        if fmt == "asmr":
            return self._produce_reel_asmr(script, idx, name, output_dir)
        if fmt == "slides-only":
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
        voice = script.get("voice", "")
        print(f"  -> Generating TTS voiceover ({len(narration)} chars, voice={voice or 'default'})...")
        tts_audio = work / "voiceover.mp3"
        tts_result = self.tts.generate(narration, tts_audio, voice_id=voice)
        if tts_result is None:
            raise RuntimeError("TTS generation failed — check MINIMAX_API_KEY")

        audio_duration = self.compositor.get_duration(tts_audio)

        # 2) Build slide segments from visual_directions
        slide_segments = self._build_slide_segments(script, audio_duration, work)

        # 3) Create video: slide images timed to TTS audio
        raw_video = work / "raw_slide_video.mp4"
        if len(slide_segments) > 1:
            print(f"  -> Compositing {len(slide_segments)} slide segments + audio...")
            self.compositor.multi_slide_video(slide_segments, tts_audio, raw_video)
        else:
            slide_img = slide_segments[0][0] if slide_segments else self._fallback_slide(script, work)
            print(f"  -> Compositing slide + audio...")
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
    # Character reel production
    # ------------------------------------------------------------------

    def _produce_reel_character(
        self, script: dict, idx: int, name: str, output_dir: Path
    ) -> Path:
        """Produce a reel with AI character (top) + slides (bottom) + TTS voiceover."""
        work = output_dir / f"_work_{name}"
        work.mkdir(parents=True, exist_ok=True)

        narration = script.get("narration_text", "")
        if not narration:
            narration = script.get("hook", "") + " " + script.get("key_takeaway", "")
        narration = narration.strip()
        if not narration:
            narration = f"Let me explain {script.get('topic', 'this concept')} to you."

        # 1) Generate TTS audio
        voice = script.get("voice", "")
        print(f"  -> Generating TTS voiceover ({len(narration)} chars, voice={voice or 'default'})...")
        tts_audio = work / "voiceover.mp3"
        tts_result = self.tts.generate(narration, tts_audio, voice_id=voice)
        if tts_result is None:
            raise RuntimeError("TTS generation failed — check MINIMAX_API_KEY")

        audio_duration = self.compositor.get_duration(tts_audio)

        # 2) Generate character video via MiniMax I2V
        print(f"  -> Generating AI character video from {self._character_image.name}...")
        char_clip = work / "character_raw.mp4"
        char_prompt = (
            "A character speaking directly to the camera with clearly visible "
            "mouth movements, opening and closing their mouth as if talking. "
            "Subtle head nods and natural hand gestures while explaining. "
            "Upper body framing, steady camera, looking at the viewer."
        )
        char_result = self.minimax_video.generate_from_image(
            self._character_image, char_prompt, char_clip,
            duration=10, max_wait_sec=400,
        )
        if char_result is None:
            raise RuntimeError("Character video generation failed — check MiniMax API")

        # 3) Loop character clip to match TTS audio duration
        print(f"  -> Looping character clip to {audio_duration:.1f}s...")
        char_looped = work / "character_looped.mp4"
        self.compositor.pingpong_loop(char_clip, audio_duration, char_looped)

        # 4) Composite — check if we have slides or it's a notes-only reel
        has_slide_refs = any(
            vd.get("slide_number") for vd in script.get("visual_directions", [])
        )
        fullscreen = not has_slide_refs or self._slide_renderer is None

        raw_video = work / "raw_character_video.mp4"
        if fullscreen:
            # Notes-only: full-screen character + audio
            print(f"  -> Compositing full-screen character + audio...")
            self.compositor.character_fullscreen(char_looped, tts_audio, raw_video)
        else:
            slide_segments = self._build_slide_segments(script, audio_duration, work)
            if len(slide_segments) > 1:
                print(f"  -> Compositing character + {len(slide_segments)} slides + audio...")
                self.compositor.character_with_multi_slides(
                    char_looped, slide_segments, tts_audio, raw_video,
                )
            else:
                slide_img = slide_segments[0][0] if slide_segments else self._fallback_slide(script, work)
                print(f"  -> Compositing character + slide + audio...")
                self.compositor.character_with_slides(
                    char_looped, slide_img, tts_audio, raw_video,
                )

        # 5) Subtitles
        final = output_dir / f"{name}.mp4"
        print("  -> Generating word-level subtitles from TTS audio...")
        words = transcribe_clip_words(raw_video)
        if words:
            ass_path = work / "subtitles.ass"
            if fullscreen:
                generate_subtitles_multi([(0.0, words)], ass_path)
            else:
                generate_subtitles_multi([(0.0, words)], ass_path, alignment=8, margin_v=80)
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
    # ASMR reel production
    # ------------------------------------------------------------------

    def _produce_reel_asmr(
        self, script: dict, idx: int, name: str, output_dir: Path
    ) -> Path:
        """Produce a reel with AI satisfying/ASMR video (top) + slides (bottom) + TTS voiceover."""
        import random

        work = output_dir / f"_work_{name}"
        work.mkdir(parents=True, exist_ok=True)

        narration = script.get("narration_text", "")
        if not narration:
            narration = script.get("hook", "") + " " + script.get("key_takeaway", "")
        narration = narration.strip()
        if not narration:
            narration = f"Let me explain {script.get('topic', 'this concept')} to you."

        # 1) Generate TTS audio
        voice = script.get("voice", "")
        print(f"  -> Generating TTS voiceover ({len(narration)} chars, voice={voice or 'default'})...")
        tts_audio = work / "voiceover.mp3"
        tts_result = self.tts.generate(narration, tts_audio, voice_id=voice)
        if tts_result is None:
            raise RuntimeError("TTS generation failed — check MINIMAX_API_KEY")

        audio_duration = self.compositor.get_duration(tts_audio)

        # 2) Generate ASMR clip via MiniMax T2V
        asmr_prompt = self._build_asmr_prompt()
        print(f"  -> Generating ASMR video clip...")
        print(f"     Prompt: {asmr_prompt[:80]}...")
        asmr_clip = work / "asmr_raw.mp4"
        asmr_result = self.minimax_video.generate(
            asmr_prompt, asmr_clip, duration=10, max_wait_sec=400,
        )
        if asmr_result is None:
            raise RuntimeError("ASMR video generation failed — check MiniMax API")

        # 3) Ping-pong loop to match TTS audio duration
        print(f"  -> Looping ASMR clip to {audio_duration:.1f}s...")
        asmr_looped = work / "asmr_looped.mp4"
        self.compositor.pingpong_loop(asmr_clip, audio_duration, asmr_looped)

        # 4) Build slide segments
        slide_segments = self._build_slide_segments(script, audio_duration, work)

        # 5) Composite: ASMR clip (top) + slides (bottom) + TTS audio
        raw_video = work / "raw_asmr_video.mp4"
        if len(slide_segments) > 1:
            print(f"  -> Compositing ASMR + {len(slide_segments)} slides + audio...")
            self.compositor.character_with_multi_slides(
                asmr_looped, slide_segments, tts_audio, raw_video,
            )
        else:
            slide_img = slide_segments[0][0] if slide_segments else self._fallback_slide(script, work)
            print(f"  -> Compositing ASMR + slide + audio...")
            self.compositor.character_with_slides(
                asmr_looped, slide_img, tts_audio, raw_video,
            )

        # 6) Subtitles — top of frame so they don't cover the slides below
        final = output_dir / f"{name}.mp4"
        print("  -> Generating word-level subtitles from TTS audio...")
        words = transcribe_clip_words(raw_video)
        if words:
            ass_path = work / "subtitles.ass"
            generate_subtitles_multi([(0.0, words)], ass_path, alignment=8, margin_v=80)
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

    def _build_asmr_prompt(self) -> str:
        """Return a random T2V prompt for the ASMR clip."""
        import random
        return random.choice(list(_ASMR_STYLES.values()))

    def _resolve_character_image(self, name: str = "") -> Path | None:
        """Find a character reference image by name from the characters directory."""
        if not name:
            return None

        direct = Path(name)
        if direct.exists() and direct.is_file():
            return direct.resolve()

        _CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            candidate = _CHARACTERS_DIR / f"{name}{ext}"
            if candidate.exists():
                return candidate.resolve()

        candidate = _CHARACTERS_DIR / name
        if candidate.exists():
            return candidate.resolve()

        return None

    def _get_available_characters(self) -> list[Path]:
        """Return all character images in the characters directory."""
        _CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
        exts = {".png", ".jpg", ".jpeg", ".webp"}
        return sorted(p for p in _CHARACTERS_DIR.iterdir() if p.suffix.lower() in exts)

    # ------------------------------------------------------------------

    def _build_slide_segments(
        self, script: dict, audio_duration: float, work: Path
    ) -> list[tuple[Path, float]]:
        """
        Parse visual_directions for slide_number references and build
        a list of (slide_image_path, duration_sec) segments.

        Proportionally scales durations to match the actual audio length.
        """
        visual_dirs = script.get("visual_directions", [])

        segments_raw: list[tuple[int, float]] = []
        for vd in visual_dirs:
            slide_num = vd.get("slide_number")
            if slide_num is None:
                source = vd.get("source_reference", "")
                m = re.match(r'slide\s+(\d+)', source, re.IGNORECASE)
                if m:
                    slide_num = int(m.group(1))
            dur = float(vd.get("duration_sec", 5))
            if slide_num is not None:
                segments_raw.append((int(slide_num), dur))

        if not segments_raw:
            fallback_img = self._fallback_slide(script, work)
            return [(fallback_img, audio_duration)]

        total_scripted = sum(d for _, d in segments_raw)
        if total_scripted <= 0:
            total_scripted = len(segments_raw) * 5.0

        result: list[tuple[Path, float]] = []
        for slide_num, dur in segments_raw:
            scaled_dur = (dur / total_scripted) * audio_duration
            scaled_dur = max(scaled_dur, 1.5)

            img_path = work / f"slide_raw_{slide_num}.png"
            if not img_path.exists():
                try:
                    self._slide_renderer.render_page_raw(slide_num, img_path)
                except Exception as e:
                    print(f"      [slides] render failed for page {slide_num}: {e}")
                    img_path = self._fallback_slide(script, work)

            result.append((img_path, scaled_dur))
            print(f"    slide {slide_num} → {scaled_dur:.1f}s")

        return result

    def _fallback_slide(self, script: dict, work: Path) -> Path:
        """Render a default slide when no slide_number is available."""
        slide_nums = script.get("related_slide_nums", [])
        if not slide_nums:
            for ts in self._topic_segments:
                if ts.get("topic_name", "") == script.get("topic", ""):
                    slide_nums = ts.get("related_slide_nums", [])
                    break
        page = slide_nums[0] if slide_nums else 1
        img = work / f"slide_raw_{page}.png"
        if not img.exists():
            self._slide_renderer.render_page_raw(page, img)
        return img

    # ------------------------------------------------------------------
    # Slide renderer
    # ------------------------------------------------------------------

    def _init_slide_renderer(self, slides_path: str):
        if not slides_path or not Path(slides_path).exists():
            self._slide_renderer = None
            return

        from .slide_renderer import SlideRenderer
        self._slide_renderer = SlideRenderer()
        n = self._slide_renderer.load_pdf(slides_path)
        print(f"  Loaded {n} slides from {slides_path}")

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
        """Produce one clip: blurred background with clear lecture video centered."""
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
        """Resolve a path from pipeline JSON, handling both absolute and relative forms."""
        if not path or not path.strip():
            return path

        p = Path(path)
        if p.exists():
            return str(p.resolve())

        # Relative path: resolve against the backend/ directory (parent of content_generation/)
        backend_dir = Path(__file__).resolve().parent.parent.parent
        candidate = backend_dir / path
        if candidate.exists():
            return str(candidate.resolve())

        # Try just the filename in the standard input directory
        input_dir = backend_dir / "content_generation" / "input"
        by_name = input_dir / Path(path).name
        if by_name.exists():
            return str(by_name.resolve())

        return path

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

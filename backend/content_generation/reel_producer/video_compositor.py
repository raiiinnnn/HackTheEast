"""
Video compositor for lecture-clip-based reels.

Main effect: blurred background from the lecture video, with the clear
lecture centered in the middle — exactly like how TikTok/Reels show
landscape videos in a vertical frame.
"""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

REEL_WIDTH = 1080
REEL_HEIGHT = 1920


def _run(args: list[str], label: str = ""):
    import sys
    import time as _time
    print(f"      [ffmpeg:{label}] running...", end="", flush=True)
    t0 = _time.time()
    try:
        result = subprocess.run(
            args, capture_output=True, text=True,
            timeout=120,
        )
        elapsed = _time.time() - t0
        if result.returncode != 0:
            stderr = result.stderr[-800:] if result.stderr else "no output"
            print(f" FAILED ({elapsed:.1f}s)", flush=True)
            raise RuntimeError(f"FFmpeg [{label}]: {stderr}")
        print(f" done ({elapsed:.1f}s)", flush=True)
    except subprocess.TimeoutExpired:
        print(f" TIMED OUT (120s)", flush=True)
        raise RuntimeError(f"FFmpeg [{label}]: timed out after 120s")


class VideoCompositor:

    def __init__(self, fps: int = 30):
        self.fps = fps

    def _extract_raw(
        self, video_path: str | Path, start_sec: float, duration_sec: float, out: Path,
    ) -> Path:
        """Fast extract: seek + copy a short clip from the big lecture file."""
        out.parent.mkdir(parents=True, exist_ok=True)
        _run([
            "ffmpeg", "-y",
            "-ss", f"{start_sec:.2f}",
            "-i", str(video_path),
            "-t", f"{duration_sec:.2f}",
            "-c", "copy",
            str(out),
        ], "extract")
        return out

    def lecture_blurred_bg(
        self,
        video_path: str | Path,
        start_sec: float,
        duration_sec: float,
        output_path: str | Path,
    ) -> Path:
        """
        Extract a lecture clip with the blurred-background vertical effect.

        Step 1: fast-extract a short clip from the big file
        Step 2: apply blur effect to the short clip (instant)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 1: extract short clip (fast stream copy)
        raw = output_path.parent / f"_raw_{output_path.stem}.mp4"
        self._extract_raw(video_path, start_sec, duration_sec, raw)

        # Step 2: apply blurred bg to the short clip
        # bg: scale-to-fill 1080x1920 (crop excess), then blur — proper TikTok effect
        fc = (
            f"[0:v]scale={REEL_WIDTH}:{REEL_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={REEL_WIDTH}:{REEL_HEIGHT},boxblur=20:3,setsar=1[bg];"
            f"[0:v]scale={REEL_WIDTH}:-2:"
            f"force_original_aspect_ratio=decrease,setsar=1[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[out]"
        )

        _run([
            "ffmpeg", "-y",
            "-i", str(raw),
            "-filter_complex", fc,
            "-map", "[out]", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-preset", "ultrafast",
            str(output_path),
        ], "blur")

        # Keep raw clip around — producer uses it for subtitle transcription
        return output_path

    def lecture_blurred_bg_with_panel(
        self,
        video_path: str | Path,
        start_sec: float,
        duration_sec: float,
        panel_path: str | Path,
        output_path: str | Path,
        panel_is_video: bool = False,
        panel_height: int = 380,
        panel_y: int = 1420,
    ) -> Path:
        """
        Blurred-bg lecture clip with a visual panel overlaid at the bottom.

        Step 1: fast-extract clip
        Step 2: apply blur + overlay panel
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        panel_width = REEL_WIDTH - 80
        panel_x = 40

        # Step 1: extract short clip
        raw = output_path.parent / f"_raw_{output_path.stem}.mp4"
        self._extract_raw(video_path, start_sec, duration_sec, raw)

        # Step 2: blur + panel overlay on the short clip
        if panel_is_video:
            fc = (
                f"[0:v]scale={REEL_WIDTH}:{REEL_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={REEL_WIDTH}:{REEL_HEIGHT},boxblur=20:3,setsar=1[bg];"
                f"[0:v]scale={REEL_WIDTH}:-2:"
                f"force_original_aspect_ratio=decrease,setsar=1[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[main];"
                f"[1:v]scale={panel_width}:{panel_height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={panel_width}:{panel_height}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a1900[panel];"
                f"[main][panel]overlay={panel_x}:{panel_y}:shortest=1[out]"
            )
            _run([
                "ffmpeg", "-y",
                "-i", str(raw),
                "-i", str(panel_path),
                "-filter_complex", fc,
                "-map", "[out]", "-map", "0:a?",
                "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-r", str(self.fps),
                "-shortest", "-preset", "ultrafast",
                str(output_path),
            ], "blur+panel_vid")
        else:
            fc = (
                f"[0:v]scale={REEL_WIDTH}:{REEL_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={REEL_WIDTH}:{REEL_HEIGHT},boxblur=20:3,setsar=1[bg];"
                f"[0:v]scale={REEL_WIDTH}:-2:"
                f"force_original_aspect_ratio=decrease,setsar=1[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[main];"
                f"[1:v]scale={panel_width}:{panel_height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={panel_width}:{panel_height}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a1900[panel];"
                f"[main][panel]overlay={panel_x}:{panel_y}[out]"
            )
            _run([
                "ffmpeg", "-y",
                "-i", str(raw),
                "-loop", "1", "-i", str(panel_path),
                "-filter_complex", fc,
                "-map", "[out]", "-map", "0:a?",
                "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-r", str(self.fps),
                "-shortest", "-preset", "ultrafast",
                str(output_path),
            ], "blur+panel_img")

        return output_path

    def lecture_blurred_bg_with_slide(
        self,
        video_path: str | Path,
        start_sec: float,
        duration_sec: float,
        slide_image: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        Classroom-slides layout: blurred bg, classroom video in top half,
        slide image in bottom half.

        Top ~55%: classroom recording (clear, centered on blurred bg)
        Bottom ~40%: rendered slide image with a thin separator
        Leaves room at very bottom for subtitles.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        raw = output_path.parent / f"_raw_{output_path.stem}.mp4"
        self._extract_raw(video_path, start_sec, duration_sec, raw)

        vid_h = int(REEL_HEIGHT * 0.52)   # ~998px for classroom video
        slide_h = int(REEL_HEIGHT * 0.38)  # ~730px for slide
        slide_y = vid_h + 20               # 20px gap

        fc = (
            # Blurred background from lecture (scale-to-fill + blur)
            f"[0:v]scale={REEL_WIDTH}:{REEL_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={REEL_WIDTH}:{REEL_HEIGHT},boxblur=20:3,setsar=1[bg];"
            # Clear classroom video, fit into top region
            f"[0:v]scale={REEL_WIDTH}:{vid_h}:"
            f"force_original_aspect_ratio=decrease,setsar=1[vid];"
            # Slide image, fit into bottom region
            f"[1:v]scale={REEL_WIDTH - 60}:{slide_h}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH - 60}:{slide_h}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a2e[slide];"
            # Stack: bg + video (centered top) + slide (below)
            f"[bg][vid]overlay=(W-w)/2:30[tmp];"
            f"[tmp][slide]overlay=30:{slide_y}[out]"
        )

        _run([
            "ffmpeg", "-y",
            "-i", str(raw),
            "-loop", "1", "-i", str(slide_image),
            "-filter_complex", fc,
            "-map", "[out]", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            "-shortest", "-preset", "ultrafast",
            str(output_path),
        ], "blur+slide")

        return output_path

    def multi_slide_video(
        self,
        slide_segments: list[tuple[str | Path, float]],
        audio_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        Create a video from multiple slide images timed to an audio track.

        Each entry in slide_segments is (slide_image_path, duration_sec).
        The slides are shown sequentially; total duration matches the audio.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if len(slide_segments) <= 1:
            img = str(slide_segments[0][0]) if slide_segments else ""
            return self.slide_image_to_video(img, audio_path, output_path)

        inputs: list[str] = []
        filter_parts: list[str] = []
        concat_inputs: list[str] = []

        for i, (img_path, dur) in enumerate(slide_segments):
            inputs.extend(["-loop", "1", "-t", f"{dur:.2f}", "-i", str(img_path)])

            filter_parts.append(
                f"[{i}:v]scale=54:96,scale={REEL_WIDTH}:{REEL_HEIGHT}:flags=bicubic[bg{i}];"
                f"[{i}:v]scale={REEL_WIDTH}:-2:"
                f"force_original_aspect_ratio=decrease[fg{i}];"
                f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2[slide{i}]"
            )
            concat_inputs.append(f"[slide{i}]")

        audio_idx = len(slide_segments)
        inputs.extend(["-i", str(audio_path)])

        fc = ";".join(filter_parts)
        fc += f";{''.join(concat_inputs)}concat=n={len(slide_segments)}:v=1:a=0[out]"

        _run([
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", fc,
            "-map", "[out]", "-map", f"{audio_idx}:a",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            "-shortest",
            "-preset", "ultrafast",
            str(output_path),
        ], "multi_slide")

        return output_path

    def slide_image_to_video(
        self,
        slide_image: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        Create a video from a static slide image + audio track.

        Same layout as lecture videos: slide fills the width, blurred
        background visible above and below. Duration matches the audio.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fc = (
            f"[0:v]scale=54:96,scale={REEL_WIDTH}:{REEL_HEIGHT}:flags=bicubic[bg];"
            f"[0:v]scale={REEL_WIDTH}:-2:"
            f"force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
        )

        _run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(slide_image),
            "-i", str(audio_path),
            "-filter_complex", fc,
            "-map", "[out]", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            "-shortest",
            "-preset", "ultrafast",
            str(output_path),
        ], "slide+audio")

        return output_path

    def burn_subtitles(
        self,
        video_path: str | Path,
        ass_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """Burn ASS subtitles onto video."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ass_str = str(Path(ass_path).resolve()).replace("\\", "/")
        ass_str = ass_str.replace(":", "\\:")

        vf = f"subtitles='{ass_str}'"

        _run([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264", "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            str(output_path),
        ], "burn_subs")

        return output_path

    def concatenate(
        self, clips: list[str | Path], output_path: str | Path
    ) -> Path:
        """Concatenate clips into one video."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if len(clips) == 1:
            shutil.copy2(str(clips[0]), str(output_path))
            return output_path

        list_file = output_path.parent / f"_concat_{output_path.stem}.txt"
        with open(list_file, "w") as f:
            for c in clips:
                p = str(Path(c).resolve()).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{p}'\n")

        _run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-preset", "ultrafast",
            str(output_path),
        ], "concat")

        list_file.unlink(missing_ok=True)
        return output_path

    def pingpong_loop(
        self,
        video_path: str | Path,
        target_duration: float,
        output_path: str | Path,
    ) -> Path:
        """
        Ping-pong loop: play forward then reversed, then stream-loop that
        unit to fill target_duration. The stitch is seamless because the
        last frame of forward == first frame of reversed (and vice versa).
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work = output_path.parent / f"_pp_{output_path.stem}"
        work.mkdir(parents=True, exist_ok=True)

        # 1) Normalize the source clip to fixed fps/format
        norm_clip = work / "norm.mp4"
        _run([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"fps={self.fps},format=yuv420p",
            "-an", "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            str(norm_clip),
        ], "pp_norm")

        # 2) Reverse
        reversed_clip = work / "reversed.mp4"
        _run([
            "ffmpeg", "-y",
            "-i", str(norm_clip),
            "-vf", "reverse",
            "-an", "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-preset", "ultrafast",
            str(reversed_clip),
        ], "pp_reverse")

        # 3) Concat forward + reversed into one seamless ping-pong unit
        concat_list = work / "concat.txt"
        concat_list.write_text(
            f"file '{norm_clip.as_posix()}'\nfile '{reversed_clip.as_posix()}'\n",
            encoding="utf-8",
        )
        pingpong_unit = work / "pingpong.mp4"
        _run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-an",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-preset", "ultrafast",
            str(pingpong_unit),
        ], "pp_concat")

        # 4) Stream-loop the ping-pong unit to fill the target duration
        _run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(pingpong_unit),
            "-t", f"{target_duration:.2f}",
            "-c:v", "libx264", "-an",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-preset", "ultrafast",
            str(output_path),
        ], "pp_loop")

        shutil.rmtree(str(work), ignore_errors=True)
        return output_path

    def character_with_slides(
        self,
        character_video: str | Path,
        slide_image: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        Split-screen layout: AI character video on top, slide image on bottom.

        Top ~55%: character video (scaled to fill width, cropped to fit)
        Bottom ~45%: slide with blurred background
        Audio: TTS voiceover from audio_path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        char_h = int(REEL_HEIGHT * 0.55)
        slide_h = REEL_HEIGHT - char_h
        slide_inner_w = REEL_WIDTH - 40
        slide_inner_h = slide_h - 20

        fc = (
            # Character: scale + pad to exact dimensions, force pixel format
            f"[0:v]scale={REEL_WIDTH}:{char_h}:force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH}:{char_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,format=yuv420p[char];"
            # Slide: blurred background for the bottom region
            f"[1:v]scale=54:96,scale={REEL_WIDTH}:{slide_h}:flags=bicubic,"
            f"format=yuv420p[slidebg];"
            # Slide: clear foreground, fit within padded area
            f"[1:v]scale={slide_inner_w}:{slide_inner_h}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH}:{slide_h}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a1900,"
            f"format=yuv420p[slidefg];"
            # Blend slide bg + fg
            f"[slidebg][slidefg]overlay=0:0,setsar=1[slide];"
            # Stack character on top, slide on bottom
            f"[char][slide]vstack[out]"
        )

        _run([
            "ffmpeg", "-y",
            "-i", str(character_video),
            "-loop", "1", "-i", str(slide_image),
            "-i", str(audio_path),
            "-filter_complex", fc,
            "-map", "[out]", "-map", "2:a",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            "-shortest",
            "-preset", "ultrafast",
            str(output_path),
        ], "char+slide")

        return output_path

    def character_with_multi_slides(
        self,
        character_video: str | Path,
        slide_segments: list[tuple[str | Path, float]],
        audio_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        Split-screen with multiple timed slides in the bottom half.

        Renders each slide segment as a separate video, concatenates them,
        then composites with the character video on top.
        """
        output_path = Path(output_path)
        work = output_path.parent / f"_charslide_{output_path.stem}"
        work.mkdir(parents=True, exist_ok=True)

        if len(slide_segments) <= 1:
            img = str(slide_segments[0][0]) if slide_segments else ""
            return self.character_with_slides(
                character_video, img, audio_path, output_path,
            )

        char_h = int(REEL_HEIGHT * 0.55)
        slide_h = REEL_HEIGHT - char_h
        slide_inner_w = REEL_WIDTH - 40
        slide_inner_h = slide_h - 20

        # Build per-slide bottom-half clips and concatenate
        inputs: list[str] = []
        filter_parts: list[str] = []
        concat_inputs: list[str] = []

        for i, (img_path, dur) in enumerate(slide_segments):
            inputs.extend(["-loop", "1", "-t", f"{dur:.2f}", "-i", str(img_path)])
            filter_parts.append(
                f"[{i}:v]scale=54:96,scale={REEL_WIDTH}:{slide_h}:flags=bicubic[sbg{i}];"
                f"[{i}:v]scale={slide_inner_w}:{slide_inner_h}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={REEL_WIDTH}:{slide_h}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a1900[sfg{i}];"
                f"[sbg{i}][sfg{i}]overlay=0:0[s{i}]"
            )
            concat_inputs.append(f"[s{i}]")

        slide_strip = work / "slide_strip.mp4"
        fc = ";".join(filter_parts)
        fc += f";{''.join(concat_inputs)}concat=n={len(slide_segments)}:v=1:a=0[out]"

        _run([
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", fc,
            "-map", "[out]",
            "-c:v", "libx264", "-an",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            "-preset", "ultrafast",
            str(slide_strip),
        ], "slide_strip")

        # Now composite: character video (top) + slide strip (bottom) + audio
        # Force both to exact pixel dimensions and pixel format before vstack
        fc2 = (
            f"[0:v]scale={REEL_WIDTH}:{char_h}:force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH}:{char_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,format=yuv420p[char];"
            f"[1:v]scale={REEL_WIDTH}:{slide_h}:force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH}:{slide_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,format=yuv420p[slide];"
            f"[char][slide]vstack[out]"
        )

        _run([
            "ffmpeg", "-y",
            "-i", str(character_video),
            "-i", str(slide_strip),
            "-i", str(audio_path),
            "-filter_complex", fc2,
            "-map", "[out]", "-map", "2:a",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            "-shortest",
            "-preset", "ultrafast",
            str(output_path),
        ], "char+multi_slide")

        shutil.rmtree(str(work), ignore_errors=True)
        return output_path

    def character_fullscreen(
        self,
        character_video: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """Full-screen character video (1080x1920) with audio overlay.

        Used for notes-only reels where there are no slides to display.
        The character video is scaled to fill the frame with a blurred
        background if the aspect ratio doesn't match.
        """
        output_path = Path(output_path)
        filter_complex = (
            f"[0:v]scale={REEL_WIDTH}:{REEL_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={REEL_WIDTH}:{REEL_HEIGHT},boxblur=20:3,setsar=1[bg];"
            f"[0:v]scale={REEL_WIDTH}:{REEL_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH}:{REEL_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black@0,"
            f"setsar=1,format=yuva420p[fg];"
            f"[bg][fg]overlay=0:0,format=yuv420p[v]"
        )
        _run([
            "ffmpeg", "-y",
            "-i", str(character_video),
            "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ], "char_fullscreen")
        return output_path

    def get_duration(self, path: str | Path) -> float:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(path)],
                capture_output=True, text=True, check=True,
            )
            return float(r.stdout.strip())
        except Exception:
            return 30.0

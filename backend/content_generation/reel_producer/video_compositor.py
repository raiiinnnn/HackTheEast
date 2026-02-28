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
        fc = (
            f"[0:v]scale=54:96,scale={REEL_WIDTH}:{REEL_HEIGHT}:flags=bicubic[bg];"
            f"[0:v]scale={REEL_WIDTH}:-2:"
            f"force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
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
                f"[0:v]scale=54:96,scale={REEL_WIDTH}:{REEL_HEIGHT}:flags=bicubic[bg];"
                f"[0:v]scale={REEL_WIDTH}:-2:"
                f"force_original_aspect_ratio=decrease[fg];"
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
                f"[0:v]scale=54:96,scale={REEL_WIDTH}:{REEL_HEIGHT}:flags=bicubic[bg];"
                f"[0:v]scale={REEL_WIDTH}:-2:"
                f"force_original_aspect_ratio=decrease[fg];"
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
            # Blurred background from lecture
            f"[0:v]scale=54:96,scale={REEL_WIDTH}:{REEL_HEIGHT}:flags=bicubic[bg];"
            # Clear classroom video, fit into top region
            f"[0:v]scale={REEL_WIDTH}:{vid_h}:"
            f"force_original_aspect_ratio=decrease[vid];"
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

    def slide_image_to_video(
        self,
        slide_image: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        Create a video from a static slide image + audio track.

        Blurred background from the slide itself, clear slide centered.
        Duration matches the audio file length.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        slide_h = int(REEL_HEIGHT * 0.55)
        fc = (
            # Blurred background from slide image
            f"[0:v]scale=54:96,scale={REEL_WIDTH}:{REEL_HEIGHT}:flags=bicubic[bg];"
            # Clear slide, fit into center
            f"[0:v]scale={REEL_WIDTH - 60}:{slide_h}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={REEL_WIDTH - 60}:{slide_h}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a1900[fg];"
            # Center the slide on the blurred bg
            f"[bg][fg]overlay=30:({REEL_HEIGHT}-{slide_h})/2[out]"
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

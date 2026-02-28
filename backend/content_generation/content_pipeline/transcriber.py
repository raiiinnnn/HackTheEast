"""
Video transcription with word/segment-level timestamps using OpenAI Whisper.

Extracts audio from video via ffmpeg, then runs Whisper to get a timestamped transcript.
Falls back to a simple stub if whisper is not installed.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TranscriptSegment:
    """A single segment of the transcript with timing info."""
    start_sec: float
    end_sec: float
    text: str

    @property
    def duration(self) -> float:
        return self.end_sec - self.start_sec

    @property
    def start_formatted(self) -> str:
        return _fmt_time(self.start_sec)

    @property
    def end_formatted(self) -> str:
        return _fmt_time(self.end_sec)

    def to_dict(self) -> dict:
        return {
            "start_sec": round(self.start_sec, 2),
            "end_sec": round(self.end_sec, 2),
            "start_formatted": self.start_formatted,
            "end_formatted": self.end_formatted,
            "text": self.text,
        }


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class Transcriber:
    """
    Transcribes video/audio files into timestamped segments.

    Uses OpenAI Whisper for high-quality transcription.
    Requires: pip install openai-whisper, and ffmpeg installed on system.
    """

    def __init__(self, model_size: str = "base", language: str | None = "en"):
        """
        Args:
            model_size: Whisper model size — "tiny", "base", "small", "medium", "large".
                        "base" is a good speed/quality tradeoff for hackathon use.
            language: Language code (e.g. "en"). None = auto-detect.
        """
        self.model_size = model_size
        self.language = language
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            import whisper
            print(f"  Loading Whisper model '{self.model_size}'...")
            self._model = whisper.load_model(self.model_size)
            print(f"  ✓ Whisper model loaded.")
        except ImportError:
            raise ImportError(
                "openai-whisper is required for video transcription.\n"
                "Install it with: pip install openai-whisper\n"
                "Also ensure ffmpeg is installed on your system."
            )

    def transcribe_file(self, file_path: str | Path) -> list[TranscriptSegment]:
        """
        Transcribe a video or audio file.

        Supports any format ffmpeg can handle: .mp4, .mkv, .avi, .wav, .mp3, etc.
        Returns list of TranscriptSegment with timestamps.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        audio_path = self._extract_audio(file_path)

        try:
            self._load_model()
            return self._transcribe_whisper(audio_path)
        finally:
            if audio_path != file_path and Path(audio_path).exists():
                Path(audio_path).unlink(missing_ok=True)

    def _extract_audio(self, file_path: Path) -> str:
        """Extract audio from video using ffmpeg. Returns path to wav file."""
        suffix = file_path.suffix.lower()
        if suffix in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
            return str(file_path)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        try:
            subprocess.run(
                [
                    "ffmpeg", "-i", str(file_path),
                    "-vn",              # no video
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",     # 16kHz for Whisper
                    "-ac", "1",         # mono
                    "-y",               # overwrite
                    tmp.name,
                ],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install it:\n"
                "  Windows: winget install ffmpeg  OR  choco install ffmpeg\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: sudo apt install ffmpeg"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr.decode()}")

        return tmp.name

    def _transcribe_whisper(self, audio_path: str) -> list[TranscriptSegment]:
        """Run Whisper on audio file, return timestamped segments."""
        print(f"  Transcribing with Whisper ({self.model_size})...")

        options = {"fp16": False, "verbose": False}
        if self.language:
            options["language"] = self.language

        result = self._model.transcribe(audio_path, **options)

        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                start_sec=seg["start"],
                end_sec=seg["end"],
                text=seg["text"].strip(),
            ))

        print(f"  ✓ Transcribed {len(segments)} segments, "
              f"total duration: {_fmt_time(segments[-1].end_sec if segments else 0)}")
        return segments

    def get_full_transcript(self, segments: list[TranscriptSegment]) -> str:
        """Combine all segments into a single timestamped transcript string."""
        lines = []
        for seg in segments:
            lines.append(f"[{seg.start_formatted} - {seg.end_formatted}] {seg.text}")
        return "\n".join(lines)

    def get_plain_text(self, segments: list[TranscriptSegment]) -> str:
        """Combine all segments into plain text without timestamps."""
        return " ".join(seg.text for seg in segments)

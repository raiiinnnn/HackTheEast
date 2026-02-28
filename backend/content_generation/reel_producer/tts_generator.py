"""
TTS narration generator using MiniMax speech API.

Generates MP3 audio files from reel narration scripts.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _pkg_dir = Path(__file__).resolve().parent.parent
    load_dotenv(_pkg_dir / ".env")
    load_dotenv(_pkg_dir.parent / ".env")
    load_dotenv()
except ImportError:
    pass


class TTSGenerator:
    """Generate voice narration audio using MiniMax TTS API."""

    VOICES = [
        "English_expressive_narrator",
        "English_Trustworthy_Man",
        "English_Calm_Woman",
        "English_Gentle_Woman",
        "English_Lively_Girl",
    ]

    def __init__(self, voice_id: str | None = None):
        self.voice_id = voice_id or os.getenv(
            "MINIMAX_VOICE_ID", "English_expressive_narrator"
        )
        self.api_key = os.getenv("MINIMAX_API_KEY", "")
        self.base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io")
        self.model = os.getenv("MINIMAX_TTS_MODEL", "speech-02-hd")
        self._mock = os.getenv("MINIMAX_MOCK", "false").lower() in ("1", "true", "yes")

    def generate(self, text: str, output_path: str | Path) -> Path:
        """
        Generate narration audio from text and save to file.

        Returns: Path to the generated MP3 file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self._mock or not self.api_key:
            return self._generate_mock(text, output_path)

        return self._generate_live(text, output_path)

    def _generate_live(self, text: str, output_path: Path) -> Path:
        import httpx

        body = {
            "model": self.model,
            "text": text[:10000],
            "stream": False,
            "output_format": "hex",
            "voice_setting": {
                "voice_id": self.voice_id,
                "speed": 1.05,
                "vol": 1,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=120) as client:
            r = client.post(
                f"{self.base_url}/v1/t2a_v2",
                headers=headers,
                json=body,
            )
            r.raise_for_status()
            data = r.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            msg = data.get("base_resp", {}).get("status_msg", "unknown")
            raise RuntimeError(f"TTS error: {msg}")

        audio_hex = data.get("data", {}).get("audio")
        if not audio_hex:
            raise RuntimeError("TTS returned no audio data")

        audio_bytes = bytes.fromhex(audio_hex)
        output_path.write_bytes(audio_bytes)
        return output_path

    def _generate_mock(self, text: str, output_path: Path) -> Path:
        """Generate a silent MP3 of appropriate duration using ffmpeg."""
        import subprocess

        words = len(text.split())
        duration_sec = max(5, words / 2.5)

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", f"anullsrc=r=32000:cl=mono",
                    "-t", str(duration_sec),
                    "-c:a", "libmp3lame", "-b:a", "128k",
                    str(output_path),
                ],
                capture_output=True, check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            output_path.write_bytes(b"\xff\xfb\x90\x00" * 1000)

        return output_path

    def get_audio_duration(self, audio_path: str | Path) -> float:
        """Get duration of an audio file in seconds using ffprobe."""
        import subprocess
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0",
                    str(audio_path),
                ],
                capture_output=True, text=True, check=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 30.0

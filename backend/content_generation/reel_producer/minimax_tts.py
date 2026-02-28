"""
MiniMax TTS client — generates voiceover audio from text.

Uses the T2A v2 API (non-streaming) to produce MP3 audio files.
Default voice and settings tuned for engaging, professor-style narration.
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

# Defaults tuned for engaging, human-like professor narration
_DEFAULT_VOICE = "English_expressive_narrator"
_DEFAULT_SPEED = 1.2
_DEFAULT_MODEL = "speech-02-hd"


class MinimaxTTS:
    """Generate voiceover audio via MiniMax T2A v2."""

    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY", "")
        self.base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io")
        self.model = os.getenv("MINIMAX_TTS_MODEL", _DEFAULT_MODEL)
        self.voice_id = os.getenv("MINIMAX_VOICE_ID", _DEFAULT_VOICE)
        raw_speed = os.getenv("MINIMAX_TTS_SPEED", str(_DEFAULT_SPEED))
        self.speed = max(0.5, min(2.0, float(raw_speed)))
        self.mock = os.getenv("MINIMAX_MOCK", "false").lower() in ("1", "true", "yes")

    @property
    def available(self) -> bool:
        return bool(self.api_key) and not self.mock

    def generate(
        self,
        text: str,
        output_path: str | Path,
        speed: float | None = None,
    ) -> Path | None:
        """
        Generate speech audio from text.

        Args:
            text: The narration script to speak (up to 10k chars)
            output_path: Where to save the MP3 file
            speed: Speech speed multiplier (0.5-2.0). If None, uses MINIMAX_TTS_SPEED or default 1.2.

        Returns:
            Path to the MP3 file, or None on failure.
        """
        if not self.available:
            print(f"    [TTS] Not available (mock={self.mock}, key={'set' if self.api_key else 'missing'})")
            return None

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        actual_speed = speed if speed is not None else self.speed
        try:
            return self._call_api(text[:10000], output_path, actual_speed)
        except Exception as e:
            print(f"    [TTS] Error: {e}")
            return None

    def _call_api(self, text: str, output_path: Path, speed: float) -> Path | None:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": self.model,
            "text": text,
            "stream": False,
            "language_boost": "English",
            "voice_setting": {
                "voice_id": self.voice_id,
                "speed": speed,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }

        print(f"    [TTS] Generating voice ({len(text)} chars, {self.voice_id}, speed={speed})...",
              end="", flush=True)

        with httpx.Client(timeout=60) as client:
            r = client.post(
                f"{self.base_url}/v1/t2a_v2",
                headers=headers,
                json=body,
            )
            r.raise_for_status()
            data = r.json()

        if data.get("base_resp", {}).get("status_code", 0) != 0:
            msg = data.get("base_resp", {}).get("status_msg", "unknown error")
            print(f" FAILED: {msg}", flush=True)
            return None

        audio_hex = data.get("data", {}).get("audio", "")
        if not audio_hex:
            # Try alternative response shapes
            audio_hex = data.get("audio_file", "") or data.get("audio", "")

        if not audio_hex:
            print(f" FAILED: no audio in response", flush=True)
            return None

        audio_bytes = bytes.fromhex(audio_hex)
        output_path.write_bytes(audio_bytes)
        dur_kb = len(audio_bytes) / 1024
        print(f" done ({dur_kb:.0f}KB)", flush=True)
        return output_path

"""
MiniMax TTS client — generates voiceover audio from text.

Uses the T2A v2 API (non-streaming) to produce MP3 audio files.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    _pkg_dir = Path(__file__).resolve().parent.parent
    load_dotenv(_pkg_dir / ".env")
    load_dotenv(_pkg_dir.parent / ".env")
    load_dotenv()
except ImportError:
    pass


class MinimaxTTS:
    """Generate voiceover audio via MiniMax T2A v2."""

    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY", "")
        self.base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io")
        self.model = os.getenv("MINIMAX_TTS_MODEL", "speech-02-hd")
        self.voice_id = os.getenv("MINIMAX_VOICE_ID", "male-qn-qingse")
        self.mock = os.getenv("MINIMAX_MOCK", "false").lower() in ("1", "true", "yes")

    @property
    def available(self) -> bool:
        return bool(self.api_key) and not self.mock

    def generate(
        self,
        text: str,
        output_path: str | Path,
        speed: float = 1.0,
        voice_id: str = "",
    ) -> Path | None:
        """
        Generate speech audio from text.

        Args:
            text: The narration script to speak (up to 10k chars)
            output_path: Where to save the MP3 file
            speed: Speech speed multiplier (0.5-2.0)
            voice_id: Override voice for this call (uses default if empty)

        Returns:
            Path to the MP3 file, or None on failure.
        """
        if not self.available:
            print(f"    [TTS] Not available (mock={self.mock}, key={'set' if self.api_key else 'missing'})")
            return None

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            return self._call_api(text[:10000], output_path, speed, voice_id=voice_id)
        except Exception as e:
            print(f"    [TTS] Error: {e}")
            return None

    @staticmethod
    def _prepare_text(text: str) -> str:
        """Clean narration text for natural TTS pronunciation."""
        t = text

        # Strip markdown formatting
        t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
        t = re.sub(r'\*(.+?)\*', r'\1', t)
        t = re.sub(r'`(.+?)`', r'\1', t)

        # Strip quoted code snippets (e.g. 'int& r1 = j;')
        t = re.sub(r"'[^']*[;&={}\[\]<>]+[^']*'", '', t)
        t = re.sub(r'"[^"]*[;&={}\[\]<>]+[^"]*"', '', t)

        # Remove stray C/C++ syntax characters
        t = re.sub(r'[{}\[\];]', '', t)
        t = re.sub(r'(?<!\w)&(?!\w)', '', t)

        # Expand common CS / academic abbreviations that confuse TTS
        _abbrevs = {
            r'\bOOP\b': 'Object-Oriented Programming',
            r'\bAPI\b': 'A P I',
            r'\bAPIs\b': 'A P Is',
            r'\bUI\b': 'U I',
            r'\bCSS\b': 'C S S',
            r'\bHTML\b': 'H T M L',
            r'\bSQL\b': 'S Q L',
            r'\bJSON\b': 'Jason',
            r'\bGUI\b': 'gooey',
            r'\bC\+\+\b': 'C plus plus',
            r'\bint\b': 'integer',
            r'\bbool\b': 'boolean',
            r'\bstd::': 'standard ',
            r'\bnullptr\b': 'null pointer',
            r'\be\.g\.': 'for example',
            r'\bi\.e\.': 'that is',
            r'\betc\.': 'etcetera',
            r'\bvs\.?\b': 'versus',
        }
        for pat, repl in _abbrevs.items():
            t = re.sub(pat, repl, t, flags=re.IGNORECASE)

        # Collapse multiple spaces / newlines into single space
        t = re.sub(r'\s+', ' ', t).strip()

        # Remove stray bullet characters
        t = re.sub(r'[•◦▪▸►]', '', t)

        return t

    def _call_api(
        self, text: str, output_path: Path, speed: float, voice_id: str = "",
    ) -> Path | None:
        import httpx

        text = self._prepare_text(text)
        effective_voice = voice_id or self.voice_id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": self.model,
            "text": text,
            "stream": False,
            "language_boost": "English",
            "text_normalization": True,
            "voice_setting": {
                "voice_id": effective_voice,
                "speed": speed,
                "vol": 1.0,
                "pitch": 0,
                "emotion": "neutral",
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }

        print(f"    [TTS] Generating voice ({len(text)} chars, voice={effective_voice})...",
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

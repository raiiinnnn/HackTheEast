"""
MiniMax video generation — generates short AI video clips from text prompts.

Used for "hero" visual moments: animated diagrams, concept visualizations,
things that can't be captured from slides or lecture video alone.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    _pkg_dir = Path(__file__).resolve().parent.parent
    load_dotenv(_pkg_dir / ".env")
    load_dotenv(_pkg_dir.parent / ".env")
    load_dotenv()
except ImportError:
    pass


class MinimaxVideoGenerator:
    """Generate short AI video clips using MiniMax Hailuo API."""

    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY", "")
        self.base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io")
        self.model = os.getenv("MINIMAX_VIDEO_MODEL", "T2V-01")
        self.mock = os.getenv("MINIMAX_MOCK", "false").lower() in ("1", "true", "yes")

    @property
    def available(self) -> bool:
        return bool(self.api_key) and not self.mock

    def generate(
        self,
        prompt: str,
        output_path: str | Path,
        duration: int = 6,
        max_wait_sec: int = 300,
    ) -> Path | None:
        """
        Generate a video clip from a text prompt.

        Args:
            prompt: Description of what the video should show
            output_path: Where to save the downloaded MP4
            duration: 6 or 10 seconds (MiniMax constraint)
            max_wait_sec: Max time to wait for generation

        Returns:
            Path to the MP4 file, or None if generation failed/timed out.
        """
        if not self.available:
            print(f"    [MiniMax Video] Not available (mock={self.mock}, key={'set' if self.api_key else 'missing'})")
            return None

        try:
            task_id = self._submit(prompt, duration)
            return self._poll_and_download(task_id, output_path, max_wait_sec)
        except Exception as e:
            print(f"    [MiniMax Video] Error: {e}")
            return None

    def _submit(self, prompt: str, duration: int) -> str:
        import httpx

        duration = 10 if duration >= 10 else 6
        body = {
            "model": self.model,
            "prompt": prompt[:2000],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30) as client:
            r = client.post(
                f"{self.base_url}/v1/video_generation",
                headers=headers,
                json=body,
            )
            r.raise_for_status()
            data = r.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            msg = data.get("base_resp", {}).get("status_msg", "unknown")
            raise RuntimeError(f"Video submit error: {msg}")

        task_id = data.get("task_id")
        if not task_id:
            raise RuntimeError("No task_id returned")

        print(f"    [MiniMax Video] Submitted task: {task_id}")
        return task_id

    def _poll_and_download(
        self, task_id: str, output_path: str | Path, max_wait_sec: int
    ) -> Path | None:
        import httpx

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start = time.time()
        poll_interval = 5

        while time.time() - start < max_wait_sec:
            with httpx.Client(timeout=30) as client:
                r = client.get(
                    f"{self.base_url}/v1/query/video_generation",
                    params={"task_id": task_id},
                    headers=headers,
                )
                r.raise_for_status()
                data = r.json()

            status = data.get("status", "Fail")

            if status == "Success":
                file_id = data.get("file_id")
                if file_id:
                    return self._download_file(file_id, output_path, headers)
                print(f"    [MiniMax Video] Success but no file_id")
                return None

            if status == "Fail":
                print(f"    [MiniMax Video] Generation failed")
                return None

            elapsed = int(time.time() - start)
            if elapsed % 10 < poll_interval:
                print(f"    [MiniMax Video] Waiting... {elapsed}s ({status})")

            time.sleep(poll_interval)

        print(f"    [MiniMax Video] Timed out after {max_wait_sec}s")
        return None

    def _download_file(
        self, file_id: str, output_path: Path, headers: dict
    ) -> Path | None:
        import httpx

        try:
            with httpx.Client(timeout=30) as client:
                r = client.get(
                    f"{self.base_url}/v1/files/retrieve",
                    params={"file_id": file_id},
                    headers=headers,
                )
                r.raise_for_status()
                file_data = r.json()

            download_url = file_data.get("file", {}).get("download_url", "")
            if not download_url:
                return None

            with httpx.Client(timeout=120) as client:
                r = client.get(download_url)
                r.raise_for_status()
                output_path.write_bytes(r.content)

            print(f"    [MiniMax Video] Downloaded: {output_path.name}")
            return output_path

        except Exception as e:
            print(f"    [MiniMax Video] Download error: {e}")
            return None

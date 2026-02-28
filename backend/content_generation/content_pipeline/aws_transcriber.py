"""
AWS Transcribe-based transcription — fast, server-side, with word-level timestamps.

Costs ~$0.024/min ($1.44/hr). A 2-hour lecture runs about $2.88.
Requires: boto3, an S3 bucket, and AWS credentials.

Env vars:
    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY  (or use `aws configure`)
    AWS_REGION          – e.g. us-east-1
    AWS_S3_BUCKET       – bucket name for temp audio uploads
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .transcriber import TranscriptSegment, _fmt_time


class AWSTranscriber:
    """
    Transcribes video/audio via AWS Transcribe.

    Same public interface as the local Whisper-based Transcriber so it can
    be swapped in as a drop-in replacement.
    """

    def __init__(self, language: str | None = "en"):
        self.language = language or "en-US"
        if len(self.language) == 2:
            _MAP = {"en": "en-US", "es": "es-US", "fr": "fr-FR", "de": "de-DE",
                    "zh": "zh-CN", "ja": "ja-JP", "ko": "ko-KR", "ar": "ar-SA"}
            self.language = _MAP.get(self.language, f"{self.language}-{self.language.upper()}")

        self._region = os.getenv("AWS_REGION", "us-east-1")
        self._bucket = os.getenv("AWS_S3_BUCKET", "")
        if not self._bucket:
            raise ValueError(
                "AWS_S3_BUCKET env var is required for AWS Transcribe.\n"
                "Create an S3 bucket and set AWS_S3_BUCKET=<bucket-name> in .env"
            )

    def _get_clients(self):
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 is required for AWS Transcribe. Install: pip install boto3")

        session = boto3.Session(region_name=self._region)
        return session.client("s3"), session.client("transcribe")

    def transcribe_file(self, file_path: str | Path) -> list[TranscriptSegment]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        s3, transcribe = self._get_clients()

        audio_path = self._extract_audio(file_path)
        s3_key = f"doomlearn-tmp/{uuid.uuid4().hex}.wav"

        try:
            print(f"  Uploading audio to s3://{self._bucket}/{s3_key} ...")
            s3.upload_file(str(audio_path), self._bucket, s3_key)
            print(f"  Upload complete.")

            segments = self._run_transcription(transcribe, s3_key)
            return segments
        finally:
            if audio_path != str(file_path) and Path(audio_path).exists():
                Path(audio_path).unlink(missing_ok=True)
            try:
                s3.delete_object(Bucket=self._bucket, Key=s3_key)
            except Exception:
                pass

    def _extract_audio(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
            return str(file_path)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        try:
            subprocess.run(
                [
                    "ffmpeg", "-i", str(file_path),
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1", "-y",
                    tmp.name,
                ],
                capture_output=True, check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install it:\n"
                "  Windows: winget install ffmpeg\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: sudo apt install ffmpeg"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr.decode()}")

        return tmp.name

    def _run_transcription(self, transcribe, s3_key: str) -> list[TranscriptSegment]:
        job_name = f"doomlearn-{uuid.uuid4().hex[:12]}"
        media_uri = f"s3://{self._bucket}/{s3_key}"

        print(f"  Starting AWS Transcribe job '{job_name}' ...")
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            MediaFormat="wav",
            LanguageCode=self.language,
            Settings={"ShowSpeakerLabels": False, "ShowAlternatives": False},
        )

        elapsed = 0
        while True:
            resp = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            status = resp["TranscriptionJob"]["TranscriptionJobStatus"]

            if status == "COMPLETED":
                print(f"  Transcription complete ({elapsed}s)")
                break
            elif status == "FAILED":
                reason = resp["TranscriptionJob"].get("FailureReason", "unknown")
                raise RuntimeError(f"AWS Transcribe job failed: {reason}")

            if elapsed % 10 == 0:
                print(f"  Waiting... {elapsed}s (status: {status})", flush=True)
            time.sleep(5)
            elapsed += 5

        result_uri = resp["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]

        import urllib.request
        with urllib.request.urlopen(result_uri) as r:
            data = json.loads(r.read().decode())

        try:
            transcribe.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception:
            pass

        return self._parse_results(data)

    def _parse_results(self, data: dict) -> list[TranscriptSegment]:
        """Parse AWS Transcribe JSON into TranscriptSegment list."""
        items = data.get("results", {}).get("items", [])
        if not items:
            return []

        segments: list[TranscriptSegment] = []
        current_words: list[str] = []
        seg_start: float | None = None
        seg_end: float = 0.0

        for item in items:
            content = item["alternatives"][0]["content"]
            item_type = item["type"]

            if item_type == "pronunciation":
                start = float(item["start_time"])
                end = float(item["end_time"])

                if seg_start is None:
                    seg_start = start

                # Break into segments roughly every 10-30 seconds of speech
                if current_words and (start - seg_end) > 1.5:
                    segments.append(TranscriptSegment(
                        start_sec=seg_start,
                        end_sec=seg_end,
                        text=" ".join(current_words),
                    ))
                    current_words = []
                    seg_start = start

                current_words.append(content)
                seg_end = end

            elif item_type == "punctuation":
                if current_words:
                    current_words[-1] += content
                    # Sentence-ending punctuation is a natural segment break
                    if content in ".!?" and seg_start is not None:
                        segments.append(TranscriptSegment(
                            start_sec=seg_start,
                            end_sec=seg_end,
                            text=" ".join(current_words),
                        ))
                        current_words = []
                        seg_start = None

        if current_words and seg_start is not None:
            segments.append(TranscriptSegment(
                start_sec=seg_start,
                end_sec=seg_end,
                text=" ".join(current_words),
            ))

        print(f"  Parsed {len(segments)} segments, "
              f"total duration: {_fmt_time(segments[-1].end_sec if segments else 0)}")
        return segments

    def get_full_transcript(self, segments: list[TranscriptSegment]) -> str:
        lines = []
        for seg in segments:
            lines.append(f"[{seg.start_formatted} - {seg.end_formatted}] {seg.text}")
        return "\n".join(lines)

    def get_plain_text(self, segments: list[TranscriptSegment]) -> str:
        return " ".join(seg.text for seg in segments)

"""
CLI test script for the content pipeline.

Usage:
    # Auto-scan content_generation/input for videos and PDFs
    python -m content_generation.scripts.test_pipeline

    # Or specify files manually
    python -m content_generation.scripts.test_pipeline --video lecture.mp4 --slides slides.pdf

    # Skip re-transcription — reuse existing transcript from a previous pipeline JSON
    python -m content_generation.scripts.test_pipeline --from-json content_generation/output/pipeline_result.json

    # With options
    python -m content_generation.scripts.test_pipeline --input content_generation/input \
        --duration 60 --max-reels 5 --whisper-model small --output content_generation/output/result.json
"""

import argparse
import json
import sys
import os
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PKG_ROOT = _SCRIPT_DIR.parent                     # content_generation/
_REPO_ROOT = _PKG_ROOT.parent                      # parent repo root

sys.path.insert(0, str(_REPO_ROOT))

from content_generation.content_pipeline import ContentPipeline
from content_generation.content_pipeline.transcriber import TranscriptSegment
from content_generation.content_pipeline.slide_analyzer import SlideContent
from content_generation.content_pipeline.pipeline import PipelineResult
from content_generation.content_pipeline.topic_segmenter import TopicSegmenter
from content_generation.content_pipeline.script_generator import ScriptGenerator

_DEFAULT_INPUT = str(_PKG_ROOT / "input")
_DEFAULT_OUTPUT = str(_PKG_ROOT / "output" / "pipeline_result.json")

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}
SLIDE_EXTENSIONS = {".pdf"}


def scan_folder(folder: str | Path) -> tuple[str | None, str | None]:
    """Scan a folder and auto-detect the first video and first PDF."""
    folder = Path(folder)
    if not folder.is_dir():
        print(f"Error: '{folder}' is not a directory.")
        sys.exit(1)

    video_path = None
    slides_path = None

    files = sorted(folder.iterdir())
    for f in files:
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in VIDEO_EXTENSIONS and video_path is None:
            video_path = str(f)
        elif ext in SLIDE_EXTENSIONS and slides_path is None:
            slides_path = str(f)

    if video_path:
        print(f"  Found video: {video_path}")
    if slides_path:
        print(f"  Found slides: {slides_path}")
    if not video_path and not slides_path:
        print(f"  No video or PDF files found in '{folder}'.")
        print(f"  Supported video formats: {', '.join(VIDEO_EXTENSIONS)}")
        print(f"  Supported slide formats: {', '.join(SLIDE_EXTENSIONS)}")
        sys.exit(1)

    return video_path, slides_path


def main():
    parser = argparse.ArgumentParser(
        description="DoomLearn Content Pipeline — analyze lecture content and generate reel scripts"
    )
    parser.add_argument(
        "--input", "-i", default=_DEFAULT_INPUT,
        help=f"Path to input folder (auto-detects videos and PDFs inside). Default: {_DEFAULT_INPUT}"
    )
    parser.add_argument("--video", "-v", help="Path to lecture video file (.mp4, .mkv, etc.)")
    parser.add_argument("--slides", "-s", help="Path to slides PDF file")
    parser.add_argument(
        "--duration", "-d", type=int, default=30, choices=[15, 30, 60],
        help="Target reel duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-reels", "-n", type=int, default=10,
        help="Maximum number of reels to generate (default: 10)"
    )
    parser.add_argument(
        "--max-topics", type=int, default=None,
        help="Limit to N topics (for testing — generates fewer scripts). Default: no limit"
    )
    parser.add_argument(
        "--whisper-model", "-w", default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size for transcription (default: base)"
    )
    parser.add_argument(
        "--language", "-l", default="en",
        help="Language code for transcription (default: en, use 'auto' for auto-detect)"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help=f"Path to save output JSON (default: {_DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--transcriber", "-t", default="whisper",
        choices=["whisper", "aws"],
        help="Transcription backend: 'whisper' (local, free, slow) or 'aws' (fast, ~$0.024/min)"
    )
    parser.add_argument(
        "--from-json", default=None,
        help="Skip transcription — reuse transcript+slides from an existing pipeline JSON. "
             "Only re-runs topic segmentation and script generation."
    )
    parser.add_argument(
        "--no-print-scripts", action="store_true",
        help="Don't print scripts to console"
    )

    args = parser.parse_args()

    output_path = args.output or _DEFAULT_OUTPUT

    # ------------------------------------------------------------------
    # Fast path: reuse existing transcript, just redo topics + scripts
    # ------------------------------------------------------------------
    if args.from_json:
        _rescript(args.from_json, output_path, args.duration, args.max_reels, args.max_topics, args.no_print_scripts)
        return

    # ------------------------------------------------------------------
    # Normal path: full pipeline from video/slides
    # ------------------------------------------------------------------
    video_path = args.video
    slides_path = args.slides

    input_dir = Path(args.input)
    if input_dir.is_dir():
        print(f"\nScanning input folder: {args.input}")
        found_video, found_slides = scan_folder(args.input)
        video_path = video_path or found_video
        slides_path = slides_path or found_slides

    if not video_path and not slides_path:
        parser.error(
            f"No video or PDF found. Put files in '{args.input}/' or use --video / --slides."
        )

    lang = args.language if args.language != "auto" else None

    pipeline = ContentPipeline(
        reel_duration=args.duration,
        max_reels=args.max_reels,
        whisper_model=args.whisper_model,
        language=lang,
        transcriber_backend=args.transcriber,
    )

    result = pipeline.run(
        video_path=video_path,
        slides_path=slides_path,
        output_path=output_path,
        max_topics=args.max_topics,
    )

    result.print_summary()

    if not args.no_print_scripts:
        result.print_scripts()

    print(f"\nDone! Full result saved to: {output_path}")


def _rescript(from_json: str, output_path: str, duration: int, max_reels: int, max_topics: int | None, no_print: bool):
    """Load transcript + slides from an existing JSON, re-run only topics + scripts."""
    import time

    from_json = Path(from_json)
    if not from_json.exists():
        print(f"Error: '{from_json}' not found.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  DoomLearn — Re-generating topics + scripts")
    print(f"  Source: {from_json}")
    print(f"{'='*60}")

    with open(from_json, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    video_path = meta.get("video_path", "")
    slides_path = meta.get("slides_path", "")

    raw_segs = data.get("transcript_segments", [])
    transcript_segments = [
        TranscriptSegment(
            start_sec=s["start_sec"],
            end_sec=s["end_sec"],
            text=s["text"],
        )
        for s in raw_segs
    ]
    print(f"\n  Loaded {len(transcript_segments)} transcript segments (skipping re-transcription)")

    raw_slides = data.get("slides", [])
    slides = [
        SlideContent(
            page_num=s.get("page_num", 0),
            raw_text=s.get("raw_text", ""),
            title=s.get("title", ""),
            bullet_points=s.get("bullet_points", []),
            has_diagram=s.get("has_diagram", False),
            has_formula=s.get("has_formula", False),
            diagram_hint=s.get("diagram_hint", ""),
            key_terms=s.get("key_terms", []),
        )
        for s in raw_slides
    ]
    print(f"  Loaded {len(slides)} slides")

    t0 = time.time()

    print(f"\n[1/2] SEGMENTING TOPICS")
    segmenter = TopicSegmenter()
    topic_segments = segmenter.segment(transcript_segments, slides if slides else None)

    if max_topics is not None:
        topic_segments = topic_segments[:max_topics]
        print(f"  (Limited to {max_topics} topic(s) for testing)")

    print(f"\n[2/2] GENERATING REEL SCRIPTS")
    generator = ScriptGenerator(reel_duration=duration, max_reels=max_reels)
    reel_scripts = generator.generate_scripts(topic_segments, slides if slides else None)

    result = PipelineResult(
        transcript_segments=transcript_segments,
        slides=slides,
        topic_segments=topic_segments,
        reel_scripts=reel_scripts,
        processing_time_sec=time.time() - t0,
        video_path=video_path,
        slides_path=slides_path,
    )

    result.save(output_path)
    result.print_summary()

    if not no_print:
        result.print_scripts()

    print(f"\nDone! Saved to: {output_path}")


if __name__ == "__main__":
    main()

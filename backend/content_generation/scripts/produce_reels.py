"""
CLI script to produce lecture-clip reels from pipeline output.

Usage:
    # Produce all reels
    python -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json

    # Produce first 3 reels only
    python -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json --max 3

    # Produce specific reels by index
    python -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json --reels 0 2 5

    # Enable MiniMax AI video for hero visuals
    python -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json --use-minimax-video
"""

import argparse
import sys
import os
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PKG_ROOT = _SCRIPT_DIR.parent                     # content_generation/
_REPO_ROOT = _PKG_ROOT.parent                      # parent repo root

sys.path.insert(0, str(_REPO_ROOT))

from content_generation.reel_producer import ReelProducer

_DEFAULT_OUTPUT = str(_PKG_ROOT / "output" / "reels")


def main():
    parser = argparse.ArgumentParser(
        description="DoomLearn Reel Producer — lecture clip-based vertical reels"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to pipeline_result.json"
    )
    parser.add_argument(
        "--output", "-o", default=_DEFAULT_OUTPUT,
        help=f"Output directory for reel videos (default: {_DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--max", "-n", type=int, default=None,
        help="Maximum number of reels to produce (default: all)"
    )
    parser.add_argument(
        "--reels", type=int, nargs="+", default=None,
        help="Specific reel indices to produce (0-based)"
    )
    parser.add_argument(
        "--use-minimax-video", action="store_true",
        help="Use MiniMax to generate AI video clips for hero visuals"
    )
    parser.add_argument(
        "--lecture-format", default="zoom",
        choices=["zoom", "classroom-slides", "classroom", "slides-only"],
        help="Lecture type: zoom (slides in video), classroom-slides (separate PDF), "
             "classroom (no slides), slides-only (PDF + AI voiceover, no video)"
    )
    parser.add_argument(
        "--slides", default=None,
        help="Path to slides PDF (for classroom-slides or slides-only format). "
             "If omitted, uses slides_path from pipeline JSON."
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        parser.error(f"Input file not found: {args.input}")

    producer = ReelProducer(
        use_minimax_video=args.use_minimax_video,
        lecture_format=args.lecture_format,
        slides_pdf=args.slides,
    )

    produced = producer.produce_from_file(
        pipeline_json=args.input,
        output_dir=args.output,
        max_reels=args.max,
        reel_indices=args.reels,
    )

    print(f"\nProduced {len(produced)} reels:")
    for p in produced:
        print(f"  {p}")


if __name__ == "__main__":
    main()

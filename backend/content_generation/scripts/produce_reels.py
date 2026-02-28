"""
CLI script to produce lecture-clip reels from pipeline output.

Format is already decided per-script in the pipeline JSON — no need to specify
format flags here. Just point at the JSON and go.

Usage:
    # Produce all reels from the pipeline
    py -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json

    # First 5 only
    py -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json --max 5

    # Specific reel indices
    py -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json --reels 0 2 4

    # Force a specific character for character-format reels
    py -m content_generation.scripts.produce_reels -i content_generation/output/pipeline_result.json --max 1 --characters smeshariki
"""

import argparse
import sys
import os

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PKG_ROOT = _SCRIPT_DIR.parent                     # content_generation/
_REPO_ROOT = _PKG_ROOT.parent                      # parent repo root

sys.path.insert(0, str(_REPO_ROOT))

from content_generation.reel_producer import ReelProducer

_DEFAULT_OUTPUT = str(_PKG_ROOT / "output" / "reels")


def main():
    parser = argparse.ArgumentParser(
        description="FocusFeed Reel Producer — produce reels from pipeline JSON"
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

    # --- Optional overrides (rarely needed — pipeline JSON has everything) ---
    parser.add_argument(
        "--slides", default=None,
        help="Override slides PDF path (if different from pipeline JSON)"
    )
    parser.add_argument(
        "--video", default=None,
        help="Override lecture video path (if different from pipeline JSON)"
    )
    parser.add_argument(
        "--characters", nargs="+", default=None,
        help="Override character(s) for character-format reels. "
             "One name = use for all; multiple = round-robin. "
             "Example: --characters smeshariki"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        parser.error(f"Input file not found: {args.input}")

    producer = ReelProducer(
        slides_pdf=args.slides,
        video_path=args.video,
    )

    produced = producer.produce_from_file(
        pipeline_json=args.input,
        output_dir=args.output,
        max_reels=args.max,
        reel_indices=args.reels,
        character_override=args.characters,
    )

    print(f"\nProduced {len(produced)} reels:")
    for p in produced:
        print(f"  {p}")


if __name__ == "__main__":
    main()

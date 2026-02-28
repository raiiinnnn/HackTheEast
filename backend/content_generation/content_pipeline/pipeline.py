"""
Content Pipeline orchestrator — the main entry point.

Takes a lecture video and/or slides PDF, runs transcription, topic segmentation,
and reel script generation. Outputs structured reel scripts ready for MiniMax
video/voice production.

Usage:
    pipeline = ContentPipeline(reel_duration=30, max_reels=10)
    result = pipeline.run(video_path="lecture.mp4", slides_path="slides.pdf")

    for script in result.reel_scripts:
        print(script.to_readable())

    result.save("content_generation/output/pipeline_result.json")
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .transcriber import Transcriber, TranscriptSegment
from .aws_transcriber import AWSTranscriber
from .slide_analyzer import SlideAnalyzer, SlideContent
from .topic_segmenter import TopicSegmenter, TopicSegment
from .script_generator import ScriptGenerator, ReelScript, ReelDuration


@dataclass
class PipelineResult:
    """Complete output of the content pipeline."""
    transcript_segments: list[TranscriptSegment] = field(default_factory=list)
    slides: list[SlideContent] = field(default_factory=list)
    topic_segments: list[TopicSegment] = field(default_factory=list)
    reel_scripts: list[ReelScript] = field(default_factory=list)
    processing_time_sec: float = 0.0
    video_path: str = ""
    slides_path: str = ""

    def to_dict(self) -> dict:
        return {
            "metadata": {
                "video_path": self.video_path,
                "slides_path": self.slides_path,
                "processing_time_sec": round(self.processing_time_sec, 2),
                "num_transcript_segments": len(self.transcript_segments),
                "num_slides": len(self.slides),
                "num_topics": len(self.topic_segments),
                "num_reel_scripts": len(self.reel_scripts),
            },
            "transcript_segments": [s.to_dict() for s in self.transcript_segments],
            "slides": [s.to_dict() for s in self.slides],
            "topic_segments": [t.to_dict() for t in self.topic_segments],
            "reel_scripts": [r.to_dict() for r in self.reel_scripts],
        }

    def save(self, path: str | Path) -> None:
        """Save the full pipeline result to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n✓ Pipeline result saved to {path}")

    def print_scripts(self) -> None:
        """Print all reel scripts in human-readable format."""
        print(f"\n{'='*60}")
        print(f"  GENERATED {len(self.reel_scripts)} REEL SCRIPTS")
        print(f"{'='*60}")
        for i, script in enumerate(self.reel_scripts):
            print(f"\n[{i+1}/{len(self.reel_scripts)}]")
            print(script.to_readable())

    def print_summary(self) -> None:
        """Print a quick summary of the pipeline run."""
        print(f"\n{'─'*50}")
        print(f"  Pipeline Summary")
        print(f"{'─'*50}")
        print(f"  Video: {self.video_path or 'N/A'}")
        print(f"  Slides: {self.slides_path or 'N/A'}")
        print(f"  Transcript segments: {len(self.transcript_segments)}")
        print(f"  Slides analyzed: {len(self.slides)}")
        print(f"  Topics identified: {len(self.topic_segments)}")
        for t in self.topic_segments:
            print(f"    • {t.topic_name} ({t.time_range_formatted})")
        print(f"  Reel scripts generated: {len(self.reel_scripts)}")
        for r in self.reel_scripts:
            print(f"    • {r.topic} ({r.target_duration_sec}s)")
        print(f"  Processing time: {self.processing_time_sec:.1f}s")
        print(f"{'─'*50}")


class ContentPipeline:
    """
    Main pipeline: video + slides → reel scripts.

    Orchestrates transcription, slide analysis, topic segmentation,
    and script generation. Designed to be easily integrable with the
    existing ReelGenerator for actual MiniMax video/voice production.
    """

    def __init__(
        self,
        reel_duration: ReelDuration = 30,
        max_reels: int = 10,
        whisper_model: str = "base",
        language: str | None = "en",
        transcriber_backend: str = "whisper",
    ):
        self.reel_duration = reel_duration
        self.max_reels = max_reels

        if transcriber_backend == "aws":
            self.transcriber = AWSTranscriber(language=language)
        else:
            self.transcriber = Transcriber(model_size=whisper_model, language=language)

        self.slide_analyzer = SlideAnalyzer()
        self.topic_segmenter = TopicSegmenter()
        self.script_generator = ScriptGenerator(
            reel_duration=reel_duration, max_reels=max_reels
        )

    def run(
        self,
        video_path: str | Path | None = None,
        slides_path: str | Path | None = None,
        output_path: str | Path | None = None,
        max_topics: int | None = None,
    ) -> PipelineResult:
        """
        Run the full pipeline.

        At least one of video_path or slides_path must be provided.
        If both are provided, the transcript is cross-referenced with slide content.

        Args:
            video_path: Path to lecture video (.mp4, .mkv, .avi, etc.)
            slides_path: Path to slides PDF
            output_path: If set, saves result JSON to this path

        Returns:
            PipelineResult with transcript, topics, and reel scripts.
        """
        if not video_path and not slides_path:
            raise ValueError("At least one of video_path or slides_path must be provided.")

        start_time = time.time()
        result = PipelineResult(
            video_path=str(video_path or ""),
            slides_path=str(slides_path or ""),
        )

        print(f"\n{'='*60}")
        print(f"  DoomLearn Content Pipeline")
        print(f"{'='*60}")

        # Step 1: Transcribe video
        if video_path:
            print(f"\n[1/4] TRANSCRIBING VIDEO: {video_path}")
            result.transcript_segments = self.transcriber.transcribe_file(video_path)
        else:
            print(f"\n[1/4] TRANSCRIPTION: skipped (no video)")

        # Step 2: Analyze slides
        if slides_path:
            print(f"\n[2/4] ANALYZING SLIDES: {slides_path}")
            result.slides = self.slide_analyzer.analyze(slides_path)
        else:
            print(f"\n[2/4] SLIDE ANALYSIS: skipped (no slides)")

        # Step 3: Segment into topics
        print(f"\n[3/4] SEGMENTING TOPICS")
        if result.transcript_segments:
            result.topic_segments = self.topic_segmenter.segment(
                result.transcript_segments,
                result.slides if result.slides else None,
            )
        elif result.slides:
            result.topic_segments = self._topics_from_slides_only(result.slides)
        else:
            raise RuntimeError("No content to segment.")

        if max_topics is not None:
            result.topic_segments = result.topic_segments[:max_topics]
            print(f"  (Limited to {max_topics} topic(s) for testing)")

        # Step 4: Generate reel scripts
        print(f"\n[4/4] GENERATING REEL SCRIPTS")
        result.reel_scripts = self.script_generator.generate_scripts(
            result.topic_segments,
            result.slides if result.slides else None,
        )

        result.processing_time_sec = time.time() - start_time

        if output_path:
            result.save(output_path)

        return result

    def _topics_from_slides_only(self, slides: list[SlideContent]) -> list[TopicSegment]:
        """
        When only slides are provided (no video), create topic segments from slide content.
        Groups consecutive slides that seem related.
        """
        from .topic_segmenter import TopicSegment

        print("  → Creating topic segments from slides only...")
        topics = []
        for i, slide in enumerate(slides):
            if not slide.raw_text.strip():
                continue
            topics.append(TopicSegment(
                topic_name=slide.title or f"Slide {slide.page_num}",
                start_sec=float(i * 60),
                end_sec=float((i + 1) * 60),
                transcript_text=slide.raw_text,
                key_points=slide.bullet_points[:5],
                related_slide_nums=[slide.page_num],
                slide_content_summary=slide.raw_text[:200],
                visual_elements=(
                    [f"diagram on slide {slide.page_num}: {slide.diagram_hint}"]
                    if slide.has_diagram else []
                ),
            ))
        print(f"  ✓ Created {len(topics)} topic segments from slides.")
        return topics

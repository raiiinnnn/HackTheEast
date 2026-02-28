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
    notes_path: str = ""

    def to_dict(self) -> dict:
        return {
            "metadata": {
                "video_path": self.video_path,
                "slides_path": self.slides_path,
                "notes_path": self.notes_path,
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
        print(f"  Notes: {self.notes_path or 'N/A'}")
        print(f"  Transcript segments: {len(self.transcript_segments)}")
        print(f"  Slides analyzed: {len(self.slides)}")
        print(f"  Topics identified: {len(self.topic_segments)}")
        for t in self.topic_segments:
            concept_count = len(t.concepts)
            tag = f"{concept_count} concept(s)" if concept_count else "no concepts"
            print(f"    • {t.topic_name} ({t.time_range_formatted}) [{tag}]")
            for c in t.concepts:
                print(f"        – {c['name']}")
        print(f"  Reel scripts generated: {len(self.reel_scripts)}")
        for r in self.reel_scripts:
            extras = f"[{r.format}]" if r.format else ""
            if r.length:
                extras += f" {r.length}"
            if r.voice:
                extras += f" voice={r.voice}"
            print(f"    • {r.topic} ({r.target_duration_sec}s) {extras}")
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
        formats: list[str] | None = None,
        characters: list[str] | None = None,
        length: str = "mix",
    ):
        self.reel_duration = reel_duration
        self.max_reels = max_reels
        self.formats = formats
        self.characters = characters

        if transcriber_backend == "aws":
            self.transcriber = AWSTranscriber(language=language)
        else:
            self.transcriber = Transcriber(model_size=whisper_model, language=language)

        self.slide_analyzer = SlideAnalyzer()
        self.topic_segmenter = TopicSegmenter()
        self.script_generator = ScriptGenerator(
            reel_duration=reel_duration, max_reels=max_reels, length=length,
        )

    def run(
        self,
        video_path: str | Path | None = None,
        slides_path: str | Path | None = None,
        notes_path: str | Path | None = None,
        output_path: str | Path | None = None,
        max_topics: int | None = None,
    ) -> PipelineResult:
        """
        Run the full pipeline.

        At least one of video_path, slides_path, or notes_path must be provided.

        Args:
            video_path: Path to lecture video (.mp4, .mkv, .avi, etc.)
            slides_path: Path to slides PDF (landscape)
            notes_path: Path to notes file (.docx, .txt, or portrait PDF)
            output_path: If set, saves result JSON to this path

        Returns:
            PipelineResult with transcript, topics, and reel scripts.
        """
        if not video_path and not slides_path and not notes_path:
            raise ValueError(
                "At least one of video_path, slides_path, or notes_path must be provided."
            )

        start_time = time.time()
        result = PipelineResult(
            video_path=self._to_relative(video_path) if video_path else "",
            slides_path=self._to_relative(slides_path) if slides_path else "",
            notes_path=self._to_relative(notes_path) if notes_path else "",
        )

        print(f"\n{'='*60}")
        print(f"  FocusFeed Content Pipeline")
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

        # Step 2b: Read notes (if provided)
        notes_text = ""
        if notes_path:
            from .notes_reader import read_notes
            print(f"\n  READING NOTES: {notes_path}")
            notes_text = read_notes(notes_path)
            print(f"  ✓ Read {len(notes_text)} chars from notes")

        # Step 3: Segment into topics
        print(f"\n[3/4] SEGMENTING TOPICS")
        if result.transcript_segments:
            result.topic_segments = self.topic_segmenter.segment(
                result.transcript_segments,
                result.slides if result.slides else None,
            )
        elif result.slides:
            result.topic_segments = self._topics_from_slides_only(result.slides)
        elif notes_text:
            result.topic_segments = self._topics_from_notes(notes_text)
        else:
            raise RuntimeError("No content to segment.")

        if max_topics is not None:
            result.topic_segments = result.topic_segments[:max_topics]
            print(f"  (Limited to {max_topics} topic(s) for testing)")

        # Step 4: Generate reel scripts (format decided here, not during production)
        print(f"\n[4/4] GENERATING REEL SCRIPTS")
        result.reel_scripts = self.script_generator.generate_scripts(
            result.topic_segments,
            slides=result.slides if result.slides else None,
            formats=self.formats,
            has_video=bool(video_path),
            has_slides=bool(result.slides),
            characters=self.characters,
        )

        result.processing_time_sec = time.time() - start_time

        if output_path:
            result.save(output_path)

        return result

    @staticmethod
    def _to_relative(p: str | Path) -> str:
        """Store paths relative to content_generation/ so the JSON is portable."""
        p = Path(p).resolve()
        # Walk up looking for the content_generation directory
        cg_marker = Path(__file__).resolve().parent.parent  # .../content_generation/
        try:
            return str(p.relative_to(cg_marker.parent)).replace("\\", "/")
        except ValueError:
            # Outside the project tree — keep the filename as a fallback
            return str(p).replace("\\", "/")

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

    def _topics_from_notes(self, notes_text: str) -> list[TopicSegment]:
        """Create topic segments from notes text via LLM-based segmentation.

        Splits the text into synthetic transcript segments (one per paragraph)
        and feeds them through the normal topic segmenter.
        """
        print("  → Segmenting topics from notes text...")

        paragraphs = [p.strip() for p in notes_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [s.strip() for s in notes_text.split("\n") if s.strip()]

        if not paragraphs:
            raise RuntimeError("Notes file appears to be empty.")

        synthetic_segments: list[TranscriptSegment] = []
        cursor_sec = 0.0
        for para in paragraphs:
            duration = max(5.0, len(para) / 15.0)
            synthetic_segments.append(TranscriptSegment(
                start_sec=cursor_sec,
                end_sec=cursor_sec + duration,
                text=para,
            ))
            cursor_sec += duration

        return self.topic_segmenter.segment(synthetic_segments, slides=None)

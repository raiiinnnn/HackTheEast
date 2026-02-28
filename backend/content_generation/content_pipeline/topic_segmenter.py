"""
Topic segmentation — uses MiniMax LLM to break a timestamped transcript + slide content
into distinct topic segments, each with time ranges and related slides.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .transcriber import TranscriptSegment
    from .slide_analyzer import SlideContent


@dataclass
class TopicSegment:
    """A segment of the lecture covering one distinct topic/subtopic."""
    topic_name: str
    start_sec: float
    end_sec: float
    transcript_text: str
    key_points: list[str] = field(default_factory=list)
    related_slide_nums: list[int] = field(default_factory=list)
    slide_content_summary: str = ""
    visual_elements: list[str] = field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec

    @property
    def time_range_formatted(self) -> str:
        return f"{_fmt(self.start_sec)} - {_fmt(self.end_sec)}"

    def to_dict(self) -> dict:
        return {
            "topic_name": self.topic_name,
            "start_sec": round(self.start_sec, 2),
            "end_sec": round(self.end_sec, 2),
            "time_range": self.time_range_formatted,
            "duration_sec": round(self.duration_sec, 2),
            "transcript_text": self.transcript_text,
            "key_points": self.key_points,
            "related_slide_nums": self.related_slide_nums,
            "slide_content_summary": self.slide_content_summary,
            "visual_elements": self.visual_elements,
        }


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"


class TopicSegmenter:
    """
    Segments a lecture transcript into distinct topics using MiniMax LLM.

    Cross-references with slide content to identify which slides correspond
    to which parts of the lecture.
    """

    def segment(
        self,
        transcript_segments: list[TranscriptSegment],
        slides: list[SlideContent] | None = None,
    ) -> list[TopicSegment]:
        """
        Analyze transcript + slides and break into topic segments.

        Uses MiniMax LLM to understand the content and identify natural topic boundaries.
        """
        from .llm_client import llm_chat

        timestamped_transcript = self._build_timestamped_text(transcript_segments)
        slide_context = self._build_slide_context(slides) if slides else ""

        prompt = self._build_segmentation_prompt(timestamped_transcript, slide_context)

        print("  → Calling LLM for topic segmentation...")
        result = llm_chat(
            system_prompt=(
                "You are an expert at analyzing lecture content. Your job is to identify "
                "distinct topics/subtopics in a lecture transcript and map them to timestamps "
                "and slide content. Output ONLY valid JSON, no markdown."
            ),
            user_prompt=prompt,
        )

        topics = self._parse_segmentation_result(result, transcript_segments, slides)
        print(f"  ✓ Identified {len(topics)} topic segments.")
        return topics

    def _build_timestamped_text(
        self,
        segments: list[TranscriptSegment],
        max_chars: int = 24_000,
    ) -> str:
        """
        Build a timestamped transcript string, sampling evenly if it would be too long.
        Keeps one segment per ~30s of lecture to cover the full duration.
        """
        lines = []
        for seg in segments:
            lines.append(f"[{_fmt(seg.start_sec)}-{_fmt(seg.end_sec)}] {seg.text}")
        full = "\n".join(lines)

        if len(full) <= max_chars:
            return full

        # Too long — sample evenly across segments to cover the whole lecture
        target_n = max(20, max_chars // 200)  # ~200 chars per line on average
        step = max(1, len(segments) // target_n)
        sampled = segments[::step]
        lines = [f"[{_fmt(s.start_sec)}-{_fmt(s.end_sec)}] {s.text}" for s in sampled]
        result = "\n".join(lines)
        total_dur = _fmt(segments[-1].end_sec) if segments else "?"
        print(f"\n    [segmenter] transcript sampled: {len(sampled)}/{len(segments)} segments "
              f"({len(result)//1000}k chars, covers {total_dur})", flush=True)
        return result

    def _build_slide_context(self, slides: list[SlideContent]) -> str:
        parts = []
        for s in slides:
            if not s.raw_text.strip():
                continue
            desc = f"Slide {s.page_num}"
            if s.title:
                desc += f' — "{s.title}"'
            if s.has_diagram:
                desc += f" [DIAGRAM: {s.diagram_hint or 'visual content'}]"
            if s.has_formula:
                desc += " [FORMULA/EQUATION]"
            if s.bullet_points:
                desc += "\n  Points: " + "; ".join(s.bullet_points[:5])
            if s.key_terms:
                desc += "\n  Key terms: " + ", ".join(s.key_terms[:8])
            parts.append(desc)
        return "\n".join(parts)

    def _build_segmentation_prompt(self, transcript: str, slide_context: str) -> str:
        slide_section = ""
        if slide_context:
            slide_section = f"""

SLIDE CONTENT (for cross-referencing):
{slide_context}
"""

        return f"""Analyze this lecture transcript and identify distinct topics/subtopics.
For each topic, provide the timestamp range, key points, and which slides are related.

TIMESTAMPED TRANSCRIPT:
{transcript}
{slide_section}
Produce a JSON object with this EXACT structure:
{{
  "topics": [
    {{
      "topic_name": "Short descriptive name for this topic",
      "start_time": "M:SS format",
      "end_time": "M:SS format",
      "key_points": ["point 1", "point 2", ...],
      "related_slides": [1, 3],
      "visual_elements": ["diagram of X on slide 3", "formula Y on slide 5", ...]
    }}
  ]
}}

Rules:
- Break the lecture into 3-8 distinct topics (aim for segments of 1-5 minutes each)
- Each topic should cover a coherent concept or idea
- Include ALL content from start to end (no gaps)
- related_slides should reference slide numbers that match the topic content
- visual_elements should describe diagrams, charts, formulas, or key visuals relevant to this topic
- Output ONLY the JSON, no other text"""

    def _parse_segmentation_result(
        self,
        result: dict,
        transcript_segments: list[TranscriptSegment],
        slides: list[SlideContent] | None,
    ) -> list[TopicSegment]:
        """Parse the LLM output into TopicSegment objects."""
        raw_topics = result.get("topics", [])

        if not raw_topics:
            concepts = result.get("concepts", [])
            scripts = result.get("scripts", [])
            raw_topics = self._fallback_from_concepts(
                concepts, scripts, transcript_segments
            )

        if not raw_topics:
            return [self._single_topic_fallback(transcript_segments)]

        topic_segments = []
        for t in raw_topics:
            start = self._parse_time(t.get("start_time", "0:00"))
            end = self._parse_time(t.get("end_time", "0:00"))
            if end <= start:
                end = start + 60

            seg_texts = [
                s.text for s in transcript_segments
                if s.start_sec >= start - 2 and s.end_sec <= end + 2
            ]
            transcript_text = " ".join(seg_texts) if seg_texts else t.get("topic_name", "")

            slide_summary = ""
            related_nums = t.get("related_slides", [])
            if slides and related_nums:
                matched = [s for s in slides if s.page_num in related_nums]
                slide_summary = "; ".join(
                    f"Slide {s.page_num}: {s.title or s.raw_text[:60]}"
                    for s in matched
                )

            topic_segments.append(TopicSegment(
                topic_name=t.get("topic_name", "Untitled Topic"),
                start_sec=start,
                end_sec=end,
                transcript_text=transcript_text,
                key_points=t.get("key_points", []),
                related_slide_nums=related_nums,
                slide_content_summary=slide_summary,
                visual_elements=t.get("visual_elements", []),
            ))

        return topic_segments

    def _fallback_from_concepts(
        self,
        concepts: list[dict],
        scripts: list[dict],
        transcript_segments: list[TranscriptSegment],
    ) -> list[dict]:
        """If LLM returned concepts/scripts format instead of topics, adapt it."""
        if not concepts and not scripts:
            return []

        total_duration = transcript_segments[-1].end_sec if transcript_segments else 60
        items = concepts or scripts
        chunk_dur = total_duration / max(len(items), 1)

        topics = []
        for i, item in enumerate(items):
            start = i * chunk_dur
            end = (i + 1) * chunk_dur
            name = item.get("title") or item.get("topic") or f"Topic {i+1}"
            topics.append({
                "topic_name": name,
                "start_time": _fmt(start),
                "end_time": _fmt(end),
                "key_points": [item.get("definition", ""), item.get("example", "")],
                "related_slides": [],
                "visual_elements": [],
            })
        return topics

    def _single_topic_fallback(
        self, transcript_segments: list[TranscriptSegment]
    ) -> TopicSegment:
        """If everything fails, return the entire lecture as one topic."""
        full_text = " ".join(s.text for s in transcript_segments)
        return TopicSegment(
            topic_name="Full Lecture",
            start_sec=transcript_segments[0].start_sec if transcript_segments else 0,
            end_sec=transcript_segments[-1].end_sec if transcript_segments else 0,
            transcript_text=full_text,
        )

    def _parse_time(self, time_str: str) -> float:
        """Parse 'M:SS' or 'H:MM:SS' to seconds."""
        if isinstance(time_str, (int, float)):
            return float(time_str)
        parts = str(time_str).split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            return float(time_str)
        except (ValueError, TypeError):
            return 0.0

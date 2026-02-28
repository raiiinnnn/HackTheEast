"""
Reel script generator — takes topic segments and produces detailed reel scripts
with visual directions (what to show), narration text, and timing.

Each script is a complete blueprint for producing a TikTok/Reels-style educational video.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .topic_segmenter import TopicSegment
    from .slide_analyzer import SlideContent


ReelDuration = Literal[15, 30, 60]


@dataclass
class VisualDirection:
    """A single visual beat in a reel — what to show at a given moment."""
    timestamp_sec: float
    duration_sec: float
    visual_type: str  # "slide", "video_clip", "text_overlay", "diagram", "animation_prompt"
    description: str
    source_reference: str = ""  # e.g. "slide 3", "video 1:23-1:30"

    def to_dict(self) -> dict:
        return {
            "timestamp_sec": round(self.timestamp_sec, 1),
            "duration_sec": round(self.duration_sec, 1),
            "visual_type": self.visual_type,
            "description": self.description,
            "source_reference": self.source_reference,
        }


@dataclass
class ReelScript:
    """Complete script/blueprint for one educational reel."""
    topic: str
    hook: str
    narration_text: str
    visual_directions: list[VisualDirection] = field(default_factory=list)
    target_duration_sec: int = 30
    source_time_range: str = ""
    key_takeaway: str = ""
    quiz_question: str = ""
    quiz_choices: list[str] = field(default_factory=list)
    quiz_answer_index: int = 0
    suggested_caption: str = ""
    music_mood: str = "calm, educational"

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "hook": self.hook,
            "narration_text": self.narration_text,
            "visual_directions": [v.to_dict() for v in self.visual_directions],
            "target_duration_sec": self.target_duration_sec,
            "source_time_range": self.source_time_range,
            "key_takeaway": self.key_takeaway,
            "quiz_question": self.quiz_question,
            "quiz_choices": self.quiz_choices,
            "quiz_answer_index": self.quiz_answer_index,
            "suggested_caption": self.suggested_caption,
            "music_mood": self.music_mood,
        }

    def to_readable(self) -> str:
        """Human-readable version of the script for review."""
        lines = [
            f"═══ REEL: {self.topic} ({self.target_duration_sec}s) ═══",
            f"Source: {self.source_time_range}",
            "",
            f"🎣 HOOK: {self.hook}",
            "",
            "📝 NARRATION:",
            self.narration_text,
            "",
            "🎬 VISUAL DIRECTIONS:",
        ]
        for v in self.visual_directions:
            lines.append(
                f"  [{v.timestamp_sec:.0f}s, {v.duration_sec:.0f}s] "
                f"({v.visual_type}) {v.description}"
                + (f" — from {v.source_reference}" if v.source_reference else "")
            )
        lines.extend([
            "",
            f"💡 KEY TAKEAWAY: {self.key_takeaway}",
            f"📱 CAPTION: {self.suggested_caption}",
        ])
        if self.quiz_question:
            lines.extend([
                "",
                f"❓ QUIZ: {self.quiz_question}",
                *[f"   {'✓' if i == self.quiz_answer_index else ' '} {c}"
                  for i, c in enumerate(self.quiz_choices)],
            ])
        lines.append("═" * 50)
        return "\n".join(lines)


class ScriptGenerator:
    """
    Generates detailed reel scripts from topic segments using MiniMax LLM.

    Each script includes narration, visual directions, quiz, and production notes.
    """

    def __init__(self, reel_duration: ReelDuration = 30, max_reels: int = 10):
        self.reel_duration = reel_duration
        self.max_reels = max_reels
        self._target_words = self._duration_to_words(reel_duration)

    def generate_scripts(
        self,
        topic_segments: list[TopicSegment],
        slides: list[SlideContent] | None = None,
    ) -> list[ReelScript]:
        """
        Generate reel scripts from topic segments.

        May split long topics into multiple reels, or merge short ones.
        """
        from .llm_client import llm_chat

        scripts: list[ReelScript] = []

        for seg in topic_segments:
            if len(scripts) >= self.max_reels:
                break

            remaining = self.max_reels - len(scripts)
            reels_for_topic = self._decide_reel_count(seg, remaining)

            slide_context = ""
            if slides and seg.related_slide_nums:
                matched = [s for s in slides if s.page_num in seg.related_slide_nums]
                slide_context = self._format_slide_context(matched)

            prompt = self._build_script_prompt(seg, slide_context, reels_for_topic)

            print(f"  → Generating script for '{seg.topic_name}' ({reels_for_topic} reel(s))...")
            result = llm_chat(
                system_prompt=(
                    "You are a viral educational content creator who makes TikTok/Reels-style "
                    f"videos. Write engaging {self.reel_duration}-second reel scripts with "
                    "specific visual directions. Output ONLY valid JSON."
                ),
                user_prompt=prompt,
            )

            parsed = self._parse_script_result(result, seg)
            scripts.extend(parsed)
            print(f"  ✓ Generated {len(parsed)} script(s) for '{seg.topic_name}'.")

        return scripts[:self.max_reels]

    def _decide_reel_count(self, seg: TopicSegment, max_remaining: int) -> int:
        """Decide how many reels a topic segment warrants."""
        topic_duration = seg.duration_sec
        if topic_duration <= 0:
            return 1
        ideal = max(1, int(topic_duration / (self.reel_duration * 2)))
        return min(ideal, max_remaining, 3)

    def _format_slide_context(self, slides: list[SlideContent]) -> str:
        parts = []
        for s in slides:
            desc = f"Slide {s.page_num}"
            if s.title:
                desc += f': "{s.title}"'
            if s.has_diagram:
                desc += f" [DIAGRAM: {s.diagram_hint or 'visual'}]"
            if s.has_formula:
                desc += " [HAS FORMULA]"
            if s.bullet_points:
                desc += "\n    • " + "\n    • ".join(s.bullet_points[:5])
            else:
                text_preview = s.raw_text.strip()[:200]
                if text_preview:
                    desc += f"\n    Content: {text_preview}"
            parts.append(desc)
        return "\n".join(parts)

    def _build_script_prompt(
        self, seg: TopicSegment, slide_context: str, reel_count: int
    ) -> str:
        visual_elements_section = ""
        if seg.visual_elements:
            visual_elements_section = (
                "\nVISUAL ELEMENTS AVAILABLE:\n"
                + "\n".join(f"- {v}" for v in seg.visual_elements)
            )

        slide_section = ""
        if slide_context:
            slide_section = f"\nSLIDE CONTENT:\n{slide_context}"

        return f"""Create {reel_count} reel script(s) for this lecture topic.

TOPIC: {seg.topic_name}
TIME RANGE: {seg.time_range_formatted}
KEY POINTS: {json.dumps(seg.key_points)}

PROFESSOR'S WORDS (transcript):
{seg.transcript_text[:3000]}
{slide_section}
{visual_elements_section}

Each reel should be ~{self.reel_duration} seconds (~{self._target_words} words narration).

Produce JSON with this EXACT structure:
{{
  "reels": [
    {{
      "topic": "specific subtopic name",
      "hook": "attention-grabbing opening line (first 3 seconds)",
      "narration": "full narration script for the reel, written to be spoken aloud, engaging and clear",
      "visual_directions": [
        {{
          "time_offset_sec": 0,
          "duration_sec": 5,
          "type": "slide|video_clip|text_overlay|diagram|animation_prompt",
          "description": "what to show on screen",
          "source": "slide 3 or video 1:23-1:30 or generate"
        }}
      ],
      "key_takeaway": "one sentence summary",
      "quiz_question": "a quick review question",
      "quiz_choices": ["A", "B", "C", "D"],
      "quiz_answer_index": 0,
      "caption": "short social-media style caption with hashtags",
      "music_mood": "calm/energetic/dramatic/inspiring"
    }}
  ]
}}

Rules:
- The hook must grab attention in 3 seconds (question, surprising fact, or bold claim)
- Narration should feel like a real TikTok creator explaining the concept — conversational, not textbook
- Visual directions should reference specific slides/diagrams when available
- For slides, describe what part of the slide to zoom into or highlight
- For concepts without slides, suggest text overlays or animation prompts for MiniMax video generation
- Include the professor's key examples or analogies if they used any
- The quiz should test understanding of the core concept
- Output ONLY the JSON"""

    def _parse_script_result(
        self, result: dict, seg: TopicSegment
    ) -> list[ReelScript]:
        """Parse LLM output into ReelScript objects."""
        raw_reels = result.get("reels", [])

        if not raw_reels:
            raw_reels = self._adapt_from_scripts_format(result)

        if not raw_reels:
            return [self._fallback_script(seg)]

        scripts = []
        for r in raw_reels:
            visuals = []
            for v in r.get("visual_directions", []):
                visuals.append(VisualDirection(
                    timestamp_sec=float(v.get("time_offset_sec", 0)),
                    duration_sec=float(v.get("duration_sec", 5)),
                    visual_type=v.get("type", "text_overlay"),
                    description=v.get("description", ""),
                    source_reference=v.get("source", ""),
                ))

            if not visuals:
                visuals = [VisualDirection(
                    timestamp_sec=0,
                    duration_sec=float(self.reel_duration),
                    visual_type="text_overlay",
                    description=f"Key concept: {r.get('topic', seg.topic_name)}",
                )]

            scripts.append(ReelScript(
                topic=r.get("topic", seg.topic_name),
                hook=r.get("hook", ""),
                narration_text=r.get("narration", r.get("script_text", "")),
                visual_directions=visuals,
                target_duration_sec=self.reel_duration,
                source_time_range=seg.time_range_formatted,
                key_takeaway=r.get("key_takeaway", ""),
                quiz_question=r.get("quiz_question", ""),
                quiz_choices=r.get("quiz_choices", []),
                quiz_answer_index=r.get("quiz_answer_index", 0),
                suggested_caption=r.get("caption", ""),
                music_mood=r.get("music_mood", "calm, educational"),
            ))

        return scripts

    def _adapt_from_scripts_format(self, result: dict) -> list[dict]:
        """Handle case where LLM returns the old concepts/scripts format."""
        scripts = result.get("scripts", [])
        if not scripts:
            return []

        adapted = []
        for s in scripts:
            adapted.append({
                "topic": s.get("topic", "Topic"),
                "hook": "",
                "narration": s.get("script_text", ""),
                "visual_directions": [],
                "key_takeaway": "",
                "quiz_question": "",
                "quiz_choices": [],
                "quiz_answer_index": 0,
                "caption": "",
                "music_mood": "calm, educational",
            })
        return adapted

    def _fallback_script(self, seg: TopicSegment) -> ReelScript:
        """Generate a minimal script when LLM parsing fails."""
        narration = seg.transcript_text[:500] if seg.transcript_text else seg.topic_name
        return ReelScript(
            topic=seg.topic_name,
            hook=f"Let's talk about {seg.topic_name}!",
            narration_text=narration,
            visual_directions=[VisualDirection(
                timestamp_sec=0,
                duration_sec=float(self.reel_duration),
                visual_type="text_overlay",
                description=f"Explaining: {seg.topic_name}",
            )],
            target_duration_sec=self.reel_duration,
            source_time_range=seg.time_range_formatted,
            key_takeaway=seg.key_points[0] if seg.key_points else "",
        )

    def _duration_to_words(self, sec: int) -> int:
        return max(40, int(sec * 2.5))

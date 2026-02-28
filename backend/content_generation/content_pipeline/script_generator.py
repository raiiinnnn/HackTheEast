"""
Reel script generator — takes topic segments and produces detailed reel scripts
with visual directions (what to show), narration text, and timing.

Each script is a complete blueprint for producing a TikTok/Reels-style educational video.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .topic_segmenter import TopicSegment
    from .slide_analyzer import SlideContent


ReelDuration = Literal[15, 30, 60]  # kept for backward compat

ReelLength = Literal["short", "medium", "long"]

_LENGTH_TIERS: dict[str, dict] = {
    "short":  {"max_sec": 45,  "target_sec": 30,  "target_words": 110},
    "medium": {"max_sec": 75,  "target_sec": 60,  "target_words": 190},
    "long":   {"max_sec": 120, "target_sec": 90,  "target_words": 300},
}

_VOICE_POOL = [
    "English_expressive_narrator",
    "English_CaptivatingStoryteller",
    "English_Trustworth_Man",
    "English_ConfidentWoman",
    "English_WiseScholar",
    "English_magnetic_voiced_man",
    "English_Graceful_Lady",
    "English_FriendlyPerson",
]


@dataclass
class VisualDirection:
    """A single visual beat in a reel — what to show at a given moment."""
    timestamp_sec: float
    duration_sec: float
    visual_type: str  # "slide", "video_clip", "text_overlay", "diagram", "animation_prompt"
    description: str
    source_reference: str = ""  # e.g. "slide 3", "video 1:23-1:30"
    slide_number: int | None = None  # explicit slide page to display during this beat

    def to_dict(self) -> dict:
        d = {
            "timestamp_sec": round(self.timestamp_sec, 1),
            "duration_sec": round(self.duration_sec, 1),
            "visual_type": self.visual_type,
            "description": self.description,
            "source_reference": self.source_reference,
        }
        if self.slide_number is not None:
            d["slide_number"] = self.slide_number
        return d


@dataclass
class ReelScript:
    """Complete script/blueprint for one educational reel.

    ``format`` decides how the reel is produced:
      video       – professor's voice from the lecture recording
      slides-only – AI-generated TTS narration over slides
      character   – AI character (top) + slides (bottom) + TTS
      asmr        – ASMR clip (top) + slides (bottom) + TTS
    """
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
    format: str = "slides-only"
    character: str = ""
    length: str = "short"
    voice: str = ""

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
            "format": self.format,
            "character": self.character,
            "length": self.length,
            "voice": self.voice,
        }

    def to_readable(self) -> str:
        """Human-readable version of the script for review."""
        fmt_tag = f" [{self.format}]" if self.format else ""
        char_tag = f" ({self.character})" if self.character else ""
        len_tag = f" {self.length}" if self.length else ""
        voice_tag = f" voice={self.voice}" if self.voice else ""
        lines = [
            f"═══ REEL: {self.topic} ({self.target_duration_sec}s){fmt_tag}{char_tag}{len_tag}{voice_tag} ═══",
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

    def __init__(
        self,
        reel_duration: ReelDuration = 30,
        max_reels: int = 10,
        length: str = "mix",
    ):
        self.reel_duration = reel_duration
        self.max_reels = max_reels
        self._target_words = self._duration_to_words(reel_duration)
        self.length = length if length in ("short", "medium", "long", "mix") else "mix"

    _MAX_CONCURRENT_LLM = 4

    def generate_scripts(
        self,
        topic_segments: list[TopicSegment],
        slides: list[SlideContent] | None = None,
        formats: list[str] | None = None,
        has_video: bool = False,
        has_slides: bool = True,
        characters: list[str] | None = None,
    ) -> list[ReelScript]:
        """
        Generate reel scripts — exactly ONE reel per concept within each topic.

        Format is decided here so that:
          - "video" concepts use the professor's own audio (no LLM call)
          - AI-voiced concepts (slides-only / character / asmr) get a TTS script

        When ``has_slides`` is False (notes-only input), slides-dependent formats
        are excluded and only "character" (full-screen) is available for AI reels.

        LLM calls run in parallel (up to 4 concurrent) for speed.
        """
        import random as _rand
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from .llm_client import llm_chat

        ai_formats = [f for f in (formats or ["slides-only"]) if f != "video"]

        if not has_slides:
            _NEEDS_SLIDES = {"slides-only", "asmr"}
            ai_formats = [f for f in ai_formats if f not in _NEEDS_SLIDES]
            if not ai_formats:
                ai_formats = ["character"]

        allow_video = has_video and (not formats or "video" in (formats or []))

        # ----- Phase 1: collect all (topic, concept) pairs, interleaved -----
        topic_queues: list[list[tuple]] = []
        topic_slide_contexts: dict[str, str] = {}

        all_slide_context = ""
        if slides:
            all_slide_context = self._format_slide_context(slides)

        for seg in topic_segments:
            if self._is_non_content_topic(seg):
                print(f"  → Skipping non-content topic: '{seg.topic_name}'")
                continue

            raw_concepts = seg.concepts or self._concepts_from_key_points(seg)
            concepts = self._dedup_concepts(raw_concepts)
            if not concepts:
                continue

            if slides and seg.related_slide_nums:
                matched = [s for s in slides if s.page_num in seg.related_slide_nums]
                topic_slide_contexts[seg.topic_name] = self._format_slide_context(matched)
            else:
                topic_slide_contexts[seg.topic_name] = ""

            print(f"  → Topic '{seg.topic_name}': {len(concepts)} concept(s)")
            topic_queues.append([(seg, c) for c in concepts])

        # Round-robin interleave
        interleaved: list[tuple] = []
        qi = [0] * len(topic_queues)
        while len(interleaved) < self.max_reels:
            added = False
            for t_idx, queue in enumerate(topic_queues):
                if qi[t_idx] < len(queue):
                    interleaved.append(queue[qi[t_idx]])
                    qi[t_idx] += 1
                    added = True
                    if len(interleaved) >= self.max_reels:
                        break
            if not added:
                break

        if not interleaved:
            return []

        # ----- Phase 1b: assign format + character + length + voice per concept -----
        n = len(interleaved)
        fmt_schedule = self._assign_formats(
            n, allow_video, ai_formats, interleaved,
        )
        char_schedule = self._assign_characters(fmt_schedule, characters)
        length_schedule = self._assign_lengths(interleaved, fmt_schedule)
        voice_schedule = self._assign_voices(fmt_schedule)

        all_concept_labels = [
            f"{seg.topic_name} > {c['name']}" for seg, c in interleaved
        ]

        # ----- Phase 2: build scripts -----
        # Video concepts: no LLM needed — use professor's transcript directly
        # AI concepts: parallel LLM calls

        def _system_prompt_for(tier: str) -> str:
            t = _LENGTH_TIERS[tier]
            return (
                "You are a viral educational content creator who makes TikTok/Reels-style "
                f"videos. You write ~{t['target_sec']}-second reel scripts that explain "
                "ONE specific concept in plain, spoken English — like you're teaching a friend. "
                "Your narration will be read aloud by a text-to-speech engine, so it must "
                "sound completely natural when spoken. "
                "Each reel is a standalone video — it must begin with a hook and end with a "
                "satisfying conclusion or takeaway. Never end mid-thought or with a setup "
                "for content that never comes. Output ONLY valid JSON."
            )

        def _generate_ai_script(position: int) -> tuple[int, ReelScript | None]:
            seg, concept = interleaved[position]
            concept_label = f"{seg.topic_name} > {concept['name']}"
            sibling_concepts = [c for c in all_concept_labels if c != concept_label]

            tier = length_schedule[position]
            tier_info = _LENGTH_TIERS[tier]

            prompt = self._build_script_prompt(
                seg, topic_slide_contexts.get(seg.topic_name, ""),
                concept=concept,
                all_slides_context=all_slide_context,
                available_slide_nums=[s.page_num for s in slides] if slides else [],
                covered_concepts=sibling_concepts,
                target_sec=tier_info["target_sec"],
                target_words=tier_info["target_words"],
                has_slides=has_slides,
            )

            print(f"    → [{position+1}/{n}] {concept_label} [{fmt_schedule[position]}, {tier}]")
            try:
                result = llm_chat(
                    system_prompt=_system_prompt_for(tier),
                    user_prompt=prompt,
                )
            except Exception as e:
                print(f"      ✗ FAILED: {e}")
                return (position, None)

            parsed = self._parse_script_result(result, seg, tier)
            if parsed:
                parsed[0].topic = concept_label
                parsed[0].format = fmt_schedule[position]
                parsed[0].character = char_schedule[position]
                parsed[0].length = tier
                parsed[0].voice = voice_schedule[position]
                parsed[0].target_duration_sec = tier_info["target_sec"]
                print(f"      ✓ done")
                return (position, parsed[0])
            return (position, None)

        def _build_video_script(position: int) -> tuple[int, ReelScript | None]:
            """Pick the best excerpt window for the concept + generate quiz."""
            seg, concept = interleaved[position]
            concept_label = f"{seg.topic_name} > {concept['name']}"
            sibling_concepts = [c for c in all_concept_labels if c != concept_label]

            tier = length_schedule[position]
            tier_info = _LENGTH_TIERS[tier]

            vid_prompt = self._build_video_excerpt_prompt(
                seg, concept, sibling_concepts,
                target_sec=tier_info["target_sec"],
            )
            print(f"    → [{position+1}/{n}] {concept_label} [video — professor, {tier}]")
            try:
                result = llm_chat(
                    system_prompt=(
                        "You are an expert at selecting the most relevant excerpt from a lecture "
                        "transcript for a short-form video. Output ONLY valid JSON."
                    ),
                    user_prompt=vid_prompt,
                )
            except Exception as e:
                print(f"      ✗ FAILED: {e}")
                return (position, None)

            start_str = result.get("start_time", seg.time_range_formatted.split(" - ")[0])
            end_str = result.get("end_time", seg.time_range_formatted.split(" - ")[-1])

            script = ReelScript(
                topic=concept_label,
                hook="",
                narration_text="",
                target_duration_sec=tier_info["target_sec"],
                source_time_range=f"{start_str} - {end_str}",
                key_takeaway=result.get("key_takeaway", concept.get("description", "")),
                quiz_question=result.get("quiz_question", ""),
                quiz_choices=result.get("quiz_choices", []),
                quiz_answer_index=result.get("quiz_answer_index", 0),
                format="video",
                length=tier,
            )
            print(f"      ✓ {start_str}–{end_str}")
            return (position, script)

        # All scripts go through LLM (video ones are lightweight)
        ai_indices = [i for i in range(n) if fmt_schedule[i] != "video"]
        video_indices = [i for i in range(n) if fmt_schedule[i] == "video"]

        results: dict[int, ReelScript | None] = {}

        # All in parallel (video + AI mixed, max 4 concurrent)
        all_indices = list(range(n))
        if all_indices:
            label = f"{len(ai_indices)} AI + {len(video_indices)} video"
            print(f"\n  Generating {label} scripts ({self._MAX_CONCURRENT_LLM} concurrent)...")
            with ThreadPoolExecutor(max_workers=self._MAX_CONCURRENT_LLM) as pool:
                futures = {}
                for i in all_indices:
                    if fmt_schedule[i] == "video":
                        futures[pool.submit(_build_video_script, i)] = i
                    else:
                        futures[pool.submit(_generate_ai_script, i)] = i
                for future in as_completed(futures):
                    pos, script = future.result()
                    results[pos] = script

        # Reassemble in the original interleaved order
        scripts = [results[i] for i in range(n) if results.get(i) is not None]

        v_count = sum(1 for s in scripts if s.format == "video")
        a_count = len(scripts) - v_count
        print(f"\n  ✓ {len(scripts)} scripts: {v_count} video (professor), {a_count} AI-voiced")

        return scripts

    def _assign_formats(
        self, n: int, allow_video: bool,
        ai_formats: list[str], interleaved: list[tuple],
    ) -> list[str]:
        """Assign a format to each concept slot.

        If video is available, concepts with good transcript coverage get "video".
        Others get an AI format distributed evenly and shuffled.
        """
        import random as _rand

        if not allow_video:
            # All AI — distribute evenly
            fmts = ai_formats or ["slides-only"]
            schedule = (fmts * ((n // len(fmts)) + 1))[:n]
            _rand.shuffle(schedule)
            return schedule

        all_formats = ["video"] + (ai_formats if ai_formats else ["slides-only"])
        schedule = (all_formats * ((n // len(all_formats)) + 1))[:n]
        _rand.shuffle(schedule)
        return schedule

    @staticmethod
    def _assign_characters(fmt_schedule: list[str], characters: list[str] | None) -> list[str]:
        """For character-format slots, pick a character from the available list."""
        import random as _rand
        if not characters:
            return [""] * len(fmt_schedule)
        result = []
        for fmt in fmt_schedule:
            if fmt == "character":
                result.append(_rand.choice(characters))
            else:
                result.append("")
        return result

    def _assign_lengths(
        self,
        interleaved: list[tuple],
        fmt_schedule: list[str],
    ) -> list[str]:
        """Assign a length tier to each concept.

        - Fixed mode (short/medium/long): every concept gets that tier.
        - Mix mode: heuristic based on concept description length and
          transcript richness. Roughly: 40% short, 35% medium, 25% long.
        """
        import random as _rand

        if self.length != "mix":
            return [self.length] * len(interleaved)

        tiers = list(_LENGTH_TIERS.keys())
        weights = [0.40, 0.35, 0.25]

        schedule: list[str] = []
        for i, (seg, concept) in enumerate(interleaved):
            desc_len = len(concept.get("description", ""))
            transcript_len = len(seg.transcript_text or "")

            if transcript_len > 3000 or desc_len > 100:
                bias = [0.15, 0.40, 0.45]
            elif transcript_len > 1500 or desc_len > 50:
                bias = [0.30, 0.45, 0.25]
            else:
                bias = weights

            schedule.append(_rand.choices(tiers, weights=bias, k=1)[0])

        return schedule

    @staticmethod
    def _assign_voices(fmt_schedule: list[str]) -> list[str]:
        """Round-robin voices from _VOICE_POOL for AI-voiced reels."""
        pool_idx = 0
        result: list[str] = []
        for fmt in fmt_schedule:
            if fmt == "video":
                result.append("")
            else:
                result.append(_VOICE_POOL[pool_idx % len(_VOICE_POOL)])
                pool_idx += 1
        return result

    @staticmethod
    def _concepts_from_key_points(seg) -> list[dict]:
        """Fallback: derive concepts from key_points, or use the topic itself."""
        if seg.key_points:
            return [{"name": kp, "description": ""} for kp in seg.key_points[:5]]
        return [{"name": seg.topic_name, "description": ""}]

    @staticmethod
    def _dedup_concepts(concepts: list[dict]) -> list[dict]:
        """Merge concepts whose names are near-identical after removing fluff words.

        Catches near-duplicates like "What is X" vs "Importance of X" vs "Why X matters"
        which all teach the same idea, while preserving genuinely distinct concepts
        like "Operational Requirements" vs "Security Requirements".
        """
        if len(concepts) <= 1:
            return concepts

        # Only strip question/filler words, NOT domain nouns
        _FILLER = {
            "what", "why", "how", "is", "are", "the", "a", "an", "of",
            "and", "in", "to", "for", "it", "its", "that", "this",
            "understanding", "importance", "role", "introduction",
            "overview", "basics", "defining", "definition",
        }

        def _key_words(name: str) -> set[str]:
            words = {w.lower().strip(",.;:") for w in name.split()} - _FILLER
            return words if words else {name.lower().strip()}

        kept: list[dict] = []
        kept_keys: list[set[str]] = []

        for concept in concepts:
            words = _key_words(concept["name"])

            is_dup = False
            for existing in kept_keys:
                # Both directions: new must be mostly contained in existing AND vice versa
                if not words or not existing:
                    continue
                fwd = len(words & existing) / len(words)      # how much of new is in existing
                bwd = len(words & existing) / len(existing)    # how much of existing is in new
                # Only merge when BOTH sets are ≥75% overlapping (near-identical)
                if fwd >= 0.75 and bwd >= 0.75:
                    is_dup = True
                    break

            if not is_dup:
                kept.append(concept)
                kept_keys.append(words)

        if len(kept) < len(concepts):
            removed = len(concepts) - len(kept)
            print(f"      (merged {removed} near-duplicate concept(s))")

        return kept

    def _build_video_excerpt_prompt(
        self, seg, concept: dict, sibling_concepts: list[str],
        target_sec: int = 30,
    ) -> str:
        """Prompt that asks the LLM to pick the best excerpt for a concept."""
        sibling_section = ""
        if sibling_concepts:
            sibling_section = (
                "\nOTHER CONCEPTS (covered by separate reels — pick a DIFFERENT excerpt):\n"
                + "\n".join(f"- {c}" for c in sibling_concepts)
            )

        return f"""Find the best ~{target_sec}-second excerpt from this transcript that explains the concept below. The excerpt will be clipped directly from the lecture video.

CONCEPT: {concept['name']}
{f"Description: {concept['description']}" if concept.get('description') else ""}

PARENT TOPIC: {seg.topic_name}
FULL TOPIC TIME RANGE: {seg.time_range_formatted}

TRANSCRIPT:
{seg.transcript_text[:4000]}
{sibling_section}

Return JSON:
{{
  "start_time": "M:SS — where to start the clip (must be within the topic range)",
  "end_time": "M:SS — where to end (aim for ~{target_sec}s, must end at a natural sentence boundary — NEVER mid-sentence)",
  "key_takeaway": "one sentence summary of what the professor explains in this window",
  "quiz_question": "a review question testing the concept the professor covers",
  "quiz_choices": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "quiz_answer_index": 0
}}

Rules:
- Pick a window where the professor is actively explaining THIS concept (not general intro or agenda)
- The clip must start and end at natural sentence boundaries — no mid-sentence cuts
- Avoid sections with long pauses, filler words, or "um/uh" heavy passages
- The window must NOT overlap with excerpts for the other concepts listed above
- The quiz should test understanding of what the professor says in THIS excerpt
- Output ONLY JSON"""

    _NON_CONTENT_KEYWORDS = {
        "agenda", "today's agenda", "today's plan",
        "course outline", "course overview", "course logistics", "logistics",
        "announcements", "announcement", "admin", "administration",
        "housekeeping", "administrative", "class schedule", "schedule",
        "assignment deadlines", "grading policy", "grading",
        "exam schedule", "quiz schedule",
        "previous lecture", "last lecture", "recap of last", "review of last",
        "introduction to the course", "course introduction",
        "learning outcomes", "learning objectives",
        "today we will cover", "what we will cover",
        "syllabus",
    }

    def _is_non_content_topic(self, seg) -> bool:
        """Return True if this topic is admin/logistics fluff, not actual learning content."""
        name_lower = seg.topic_name.strip().lower()
        # Exact or partial keyword match against the topic name
        for kw in self._NON_CONTENT_KEYWORDS:
            if kw in name_lower:
                return True
        # Transcript check: if the segment is very short AND the text reads like logistics
        if seg.duration_sec < 90:
            logistics_phrases = [
                "today we will", "today's agenda", "today's plan",
                "let's start with", "first, let me", "house keeping",
                "office hours", "tutorial", "assignment due",
            ]
            text_lower = seg.transcript_text.lower()
            matches = sum(1 for p in logistics_phrases if p in text_lower)
            if matches >= 2:
                return True
        return False

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
        self,
        seg,
        slide_context: str,
        concept: dict,
        all_slides_context: str = "",
        available_slide_nums: list[int] | None = None,
        covered_concepts: list[str] | None = None,
        target_sec: int | None = None,
        target_words: int | None = None,
        has_slides: bool = True,
    ) -> str:
        visual_elements_section = ""
        if seg.visual_elements:
            visual_elements_section = (
                "\nVISUAL ELEMENTS AVAILABLE:\n"
                + "\n".join(f"- {v}" for v in seg.visual_elements)
            )

        slide_section = ""
        if slide_context:
            slide_section = f"\nTOPIC-RELATED SLIDES:\n{slide_context}"

        all_slides_section = ""
        if all_slides_context:
            all_slides_section = f"\nALL AVAILABLE SLIDES:\n{all_slides_context}"

        slide_nums_hint = ""
        if available_slide_nums:
            slide_nums_hint = f"\nAvailable slide numbers: {available_slide_nums}"

        already_covered_section = ""
        if covered_concepts:
            already_covered_section = (
                "\nOTHER CONCEPTS (covered by separate reels — do NOT overlap these):\n"
                + "\n".join(f"- {c}" for c in covered_concepts)
            )

        concept_desc = concept.get("description", "")
        concept_focus = (
            f"\nCONCEPT TO COVER: {concept['name']}"
            + (f"\n  What it covers: {concept_desc}" if concept_desc else "")
        )

        return f"""Create exactly ONE reel script focused on a single concept from this lecture topic.
{concept_focus}

PARENT TOPIC: {seg.topic_name}
TIME RANGE: {seg.time_range_formatted}
KEY POINTS (for context): {json.dumps(seg.key_points)}

PROFESSOR'S WORDS (transcript excerpt):
{seg.transcript_text[:3000]}
{slide_section}
{all_slides_section}
{visual_elements_section}
{slide_nums_hint}
{already_covered_section}

The reel should be ~{target_sec or self.reel_duration} seconds (~{target_words or self._target_words} words narration).

Produce JSON with this EXACT structure:
{{
  "reels": [
    {{
      "topic": "{concept['name']}",
      "hook": "attention-grabbing opening line (first 3 seconds)",
      "narration": "full narration in plain spoken English — NO code, NO syntax, NO variable names. Explain the concept like you're talking to a friend. This will be read by text-to-speech.",
      "visual_directions": [
        {{
          "time_offset_sec": 0,
          "duration_sec": 5,
          "type": "{'slide' if has_slides else 'text_overlay'}",
          "description": "what to show on screen"{',' if has_slides else ''}
          {'"source": "slide 3",' if has_slides else ''}
          {'"slide_number": 3' if has_slides else ''}
        }}
      ],
      "key_takeaway": "one sentence summary of this specific concept",
      "quiz_question": "a quick review question testing this concept",
      "quiz_choices": ["A", "B", "C", "D"],
      "quiz_answer_index": 0,
      "caption": "short social-media style caption with hashtags",
      "music_mood": "calm/energetic/dramatic/inspiring"
    }}
  ]
}}

Rules:
- This reel covers ONLY the concept "{concept['name']}" — stay tightly focused on it
- Do NOT repeat anything from the "OTHER CONCEPTS" list above — each of those has its own reel
- The hook must grab attention in 3 seconds (question, surprising fact, or bold claim)
- Narration should feel like a real TikTok creator explaining ONE idea to a friend — casual, conversational, zero textbook language
- NEVER copy code, syntax, variable names, or formulas into the narration. Explain what the code does in plain English
- NEVER use question-then-immediate-answer patterns like "Why is X wrong? Answer: because...". Build up to the explanation naturally
- Keep it short-form friendly — every sentence must earn its place. No filler, no "let's dive in", no "in this video we'll cover"
- Write the narration as one flowing paragraph of natural speech. No bullet points, no numbered lists, no colons, no semicolons
- CRITICAL: End with a satisfying conclusion — the punchline, takeaway, or "aha moment". Do NOT end on a setup or cliff-hanger
- NEVER end with phrases like "let's break down", "let's find out", "here's why", "now let's explore" — the video ends there
{'''- CRITICAL: Every visual_directions entry MUST include "slide_number" — the integer page number of the slide to display
- Map narration segments to the most relevant slide. Change slide_number as the narration moves through different ideas
- You can reference ANY slide from the available slides list
- Prefer actual slides over text_overlays''' if has_slides else '''- There are NO slides available — use "type": "text_overlay" for all visual_directions
- Do NOT include slide_number or source fields
- Describe what text or key phrase to display on screen as an overlay'''}
- Output ONLY the JSON"""

    @staticmethod
    def _extract_slide_number(v: dict) -> int | None:
        """Extract slide page number from a visual direction dict."""
        sn = v.get("slide_number")
        if sn is not None:
            try:
                return int(sn)
            except (ValueError, TypeError):
                pass
        source = v.get("source", "")
        m = re.match(r'slide\s+(\d+)', source, re.IGNORECASE)
        if m:
            return int(m.group(1))
        return None

    def _parse_script_result(
        self, result: dict, seg: TopicSegment, tier: str = "short",
    ) -> list[ReelScript]:
        """Parse LLM output into ReelScript objects."""
        raw_reels = result.get("reels", [])
        tier_info = _LENGTH_TIERS.get(tier, _LENGTH_TIERS["short"])

        if not raw_reels:
            raw_reels = self._adapt_from_scripts_format(result)

        if not raw_reels:
            return [self._fallback_script(seg, tier)]

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
                    slide_number=self._extract_slide_number(v),
                ))

            if not visuals:
                visuals = [VisualDirection(
                    timestamp_sec=0,
                    duration_sec=float(tier_info["target_sec"]),
                    visual_type="text_overlay",
                    description=f"Key concept: {r.get('topic', seg.topic_name)}",
                )]

            scripts.append(ReelScript(
                topic=r.get("topic", seg.topic_name),
                hook=r.get("hook", ""),
                narration_text=r.get("narration", r.get("script_text", "")),
                visual_directions=visuals,
                target_duration_sec=tier_info["target_sec"],
                source_time_range=seg.time_range_formatted,
                key_takeaway=r.get("key_takeaway", ""),
                quiz_question=r.get("quiz_question", ""),
                quiz_choices=r.get("quiz_choices", []),
                quiz_answer_index=r.get("quiz_answer_index", 0),
                suggested_caption=r.get("caption", ""),
                music_mood=r.get("music_mood", "calm, educational"),
                length=tier,
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

    def _fallback_script(self, seg: TopicSegment, tier: str = "short") -> ReelScript:
        """Generate a minimal script when LLM parsing fails."""
        tier_info = _LENGTH_TIERS.get(tier, _LENGTH_TIERS["short"])
        narration = seg.transcript_text[:500] if seg.transcript_text else seg.topic_name
        fallback_slide = seg.related_slide_nums[0] if seg.related_slide_nums else None
        return ReelScript(
            topic=seg.topic_name,
            hook=f"Let's talk about {seg.topic_name}!",
            narration_text=narration,
            visual_directions=[VisualDirection(
                timestamp_sec=0,
                duration_sec=float(tier_info["target_sec"]),
                visual_type="slide" if fallback_slide else "text_overlay",
                description=f"Explaining: {seg.topic_name}",
                slide_number=fallback_slide,
            )],
            target_duration_sec=tier_info["target_sec"],
            source_time_range=seg.time_range_formatted,
            key_takeaway=seg.key_points[0] if seg.key_points else "",
            length=tier,
        )

    def _duration_to_words(self, sec: int) -> int:
        return max(40, int(sec * 2.5))

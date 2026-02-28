"""MiniMax AI integration service.
All LLM calls go through this module. Prompt templates are centralized
at the top for easy tweaking."""

import os
import json
import logging
from typing import Dict, List, Optional, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MINIMAX_CHAT_URL = "https://api.minimaxi.chat/v1/text/chatcompletion_v2"
MINIMAX_TTS_URL = "https://api.minimaxi.chat/v1/t2a_v2"

# ---------------------------------------------------------------------------
# Prompt templates — edit these to change generation behavior
# ---------------------------------------------------------------------------

CONCEPT_CARD_PROMPT = """You are an expert educational content creator.
Given the following course material, extract the {count} most important concepts.

For each concept, produce a JSON object with:
- "title": short concept name
- "content": clear 2-3 sentence explanation suitable for a flashcard
- "card_type": one of "definition", "formula", "key_idea"

Course: {course_title}
{subtopic_line}

Material:
\"\"\"
{text}
\"\"\"

Return ONLY a JSON array of objects. No markdown, no explanation."""

REEL_SCRIPT_PROMPT = """You are a TikTok-style educational script writer.
Create {count} short, engaging video scripts from the material below.
Each script should be for a {duration}-second vertical video.

For each reel, produce a JSON object with:
- "title": catchy reel title (max 60 chars)
- "script": the narration script (spoken word, conversational, engaging)
- "captions": subtitle text matching the script
- "visual_notes": brief description of what visuals/diagrams should accompany each part

Course: {course_title}
{subtopic_line}

Material:
\"\"\"
{text}
\"\"\"

Return ONLY a JSON array. No markdown fences, no extra text."""

QUIZ_PROMPT = """You are an educational quiz creator.
Generate {count} quiz questions from the material below.
Difficulty: {difficulty}

For each question, produce a JSON object with:
- "question": the question text
- "question_type": "mcq"
- "options": array of 4 option strings (for MCQ)
- "correct_answer": the correct option text (must exactly match one option)
- "explanation": brief explanation of the correct answer
- "difficulty": "{difficulty}"

Course: {course_title}
{subtopic_line}

Material:
\"\"\"
{text}
\"\"\"

Return ONLY a JSON array. No markdown fences, no extra text."""


def _get_headers() -> Dict[str, str]:
    api_key = settings.MINIMAX_API_KEY
    if not api_key:
        api_key = os.getenv("MINIMAX_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _truncate(text: str, max_chars: int = 12000) -> str:
    """Keep text within token-budget-friendly limits."""
    return text[:max_chars] if len(text) > max_chars else text


async def _call_minimax_chat(prompt: str) -> str:
    """Send a chat completion request to MiniMax and return the text response."""
    headers = _get_headers()
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": "You are a helpful educational AI assistant. Always respond with valid JSON when asked."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(MINIMAX_CHAT_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    choice = data.get("choices", [{}])[0]
    return choice.get("message", {}).get("content", "")


def _parse_json_response(text: str) -> List[Dict[str, Any]]:
    """Robustly parse JSON from LLM output, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
        return [result]
    except json.JSONDecodeError:
        logger.error(f"Failed to parse MiniMax JSON response: {cleaned[:200]}")
        return []


async def generate_concept_cards(
    text: str,
    topic_metadata: Dict[str, Any],
    count: int = 5,
) -> List[Dict[str, Any]]:
    subtopic_line = (
        f"Subtopic: {topic_metadata.get('subtopic_title', '')}"
        if topic_metadata.get("subtopic_title")
        else ""
    )
    prompt = CONCEPT_CARD_PROMPT.format(
        count=count,
        course_title=topic_metadata.get("course_title", ""),
        subtopic_line=subtopic_line,
        text=_truncate(text),
    )

    try:
        raw = await _call_minimax_chat(prompt)
        cards = _parse_json_response(raw)
        if cards:
            return cards
    except Exception as e:
        logger.warning(f"MiniMax concept cards call failed, using fallback: {e}")

    return _fallback_concept_cards(text, count)


async def generate_reel_scripts(
    text: str,
    duration_seconds: int,
    topic_metadata: Dict[str, Any],
    count: int = 3,
) -> List[Dict[str, Any]]:
    subtopic_line = (
        f"Subtopic: {topic_metadata.get('subtopic_title', '')}"
        if topic_metadata.get("subtopic_title")
        else ""
    )
    prompt = REEL_SCRIPT_PROMPT.format(
        count=count,
        duration=duration_seconds,
        course_title=topic_metadata.get("course_title", ""),
        subtopic_line=subtopic_line,
        text=_truncate(text),
    )

    try:
        raw = await _call_minimax_chat(prompt)
        reels = _parse_json_response(raw)
        if reels:
            return reels
    except Exception as e:
        logger.warning(f"MiniMax reel scripts call failed, using fallback: {e}")

    return _fallback_reel_scripts(text, duration_seconds, count)


async def generate_quiz_items(
    text: str,
    difficulty: str,
    count: int,
    topic_metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    subtopic_line = (
        f"Subtopic: {topic_metadata.get('subtopic_title', '')}"
        if topic_metadata.get("subtopic_title")
        else ""
    )
    prompt = QUIZ_PROMPT.format(
        count=count,
        difficulty=difficulty,
        course_title=topic_metadata.get("course_title", ""),
        subtopic_line=subtopic_line,
        text=_truncate(text),
    )

    try:
        raw = await _call_minimax_chat(prompt)
        quizzes = _parse_json_response(raw)
        if quizzes:
            return quizzes
    except Exception as e:
        logger.warning(f"MiniMax quiz call failed, using fallback: {e}")

    return _fallback_quiz_items(count, difficulty)


async def generate_voice_narration(
    text: str,
    voice_style: str = "male-qn-qingse",
) -> Optional[str]:
    """Generate TTS audio via MiniMax T2A API.
    Returns the audio URL/data or None on failure.

    For a complete video pipeline:
    1. This function generates the narration audio
    2. A video compositor would combine audio + extracted images/diagrams
    3. The result is a vertical-format reel with captions overlaid
    """
    headers = _get_headers()
    payload = {
        "model": "speech-01-turbo",
        "text": text,
        "voice_setting": {
            "voice_id": voice_style,
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(MINIMAX_TTS_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        audio_url = data.get("data", {}).get("audio", {}).get("audio_url")
        return audio_url
    except Exception as e:
        logger.warning(f"MiniMax TTS call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Fallback generators (used when MiniMax API is unavailable)
# ---------------------------------------------------------------------------

def _fallback_concept_cards(text: str, count: int) -> List[Dict[str, Any]]:
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20][:count]
    return [
        {
            "title": f"Key Concept {i + 1}",
            "content": s + ".",
            "card_type": "key_idea",
        }
        for i, s in enumerate(sentences)
    ]


def _fallback_reel_scripts(text: str, duration: int, count: int) -> List[Dict[str, Any]]:
    chars_per_script = duration * 15  # ~15 chars/sec for speech
    chunks = []
    for i in range(0, min(len(text), chars_per_script * count), chars_per_script):
        chunks.append(text[i : i + chars_per_script])
    if not chunks:
        chunks = [text[:chars_per_script]]

    return [
        {
            "title": f"Quick Lesson {i + 1}",
            "script": chunk.strip(),
            "captions": chunk.strip(),
            "media_urls": [],
            "audio_url": None,
        }
        for i, chunk in enumerate(chunks[:count])
    ]


def _fallback_quiz_items(count: int, difficulty: str) -> List[Dict[str, Any]]:
    return [
        {
            "question": f"Sample question {i + 1}: What is the key concept discussed in this section?",
            "question_type": "mcq",
            "options": [
                "The main definition presented",
                "A supporting example",
                "A historical reference",
                "An unrelated topic",
            ],
            "correct_answer": "The main definition presented",
            "explanation": "This is a placeholder question. Real questions will be generated from your course materials.",
            "difficulty": difficulty,
        }
        for i in range(count)
    ]

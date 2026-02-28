"""
Lightweight LLM client for the content pipeline.

Supports multiple backends via LLM_BACKEND env var:
  - "featherless"  OpenAI-compatible API at featherless.ai (default)
  - "minimax"      MiniMax proprietary API
  - "openai"       Any OpenAI-compatible endpoint (Groq, OpenAI, etc.)

Key env vars:
  LLM_BACKEND          featherless | minimax | openai  (default: featherless)
  FEATHERLESS_API_KEY  required for featherless backend
  FEATHERLESS_MODEL    model ID (default: Qwen/Qwen3-32B)
  MINIMAX_API_KEY      required for minimax backend
  MINIMAX_LLM_MODEL    model ID (default: MiniMax-M2)
  OPENAI_API_KEY       required for openai backend
  OPENAI_BASE_URL      base URL (default: https://api.openai.com)
  OPENAI_MODEL         model ID (default: gpt-4o-mini)
  MINIMAX_MOCK         set to true for offline dev with mock responses
"""

from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _pkg_dir = Path(__file__).resolve().parent.parent
    load_dotenv(_pkg_dir / ".env")
    load_dotenv(_pkg_dir.parent / ".env")
    load_dotenv()
except ImportError:
    pass


def _backend() -> str:
    return os.getenv("LLM_BACKEND", "featherless").lower()


def _is_mock() -> bool:
    return os.getenv("MINIMAX_MOCK", "false").lower() in ("1", "true", "yes")


def llm_chat(system_prompt: str, user_prompt: str) -> dict:
    """
    Send a prompt to the configured LLM and get back parsed JSON.

    Backend is chosen via LLM_BACKEND env var (featherless/minimax/openai).
    Falls back to mock mode when MINIMAX_MOCK=true or no API key is set.

    Returns: parsed JSON dict from the LLM response.
    """
    if _is_mock():
        return _mock_response(user_prompt)

    backend = _backend()

    if backend == "minimax":
        key = os.getenv("MINIMAX_API_KEY", "")
        if not key:
            print("  WARNING: No MINIMAX_API_KEY set — using mock mode.")
            return _mock_response(user_prompt)
        return _minimax_call(system_prompt, user_prompt, key)

    elif backend == "featherless":
        key = os.getenv("FEATHERLESS_API_KEY", "")
        if not key:
            print("  WARNING: No FEATHERLESS_API_KEY set — using mock mode.")
            return _mock_response(user_prompt)
        return _openai_compatible_call(
            system_prompt, user_prompt, key,
            base_url="https://api.featherless.ai/v1",
            model=os.getenv("FEATHERLESS_MODEL", "Qwen/Qwen3-32B"),
        )

    else:  # "openai" or any custom openai-compatible
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            print("  WARNING: No OPENAI_API_KEY set — using mock mode.")
            return _mock_response(user_prompt)
        return _openai_compatible_call(
            system_prompt, user_prompt, key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------

def _openai_compatible_call(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    base_url: str,
    model: str,
) -> dict:
    """Call any OpenAI-compatible chat completions endpoint."""
    import httpx

    base_url = base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4096,
        "temperature": 0.7,
    }

    prompt_chars = len(system_prompt) + len(user_prompt)
    print(f"  [LLM] {model} (~{prompt_chars//1000}k chars) ...", end="", flush=True)
    with httpx.Client(timeout=120) as client:
        r = client.post(f"{base_url}/chat/completions", headers=headers, json=body)
        if not r.is_success:
            print(f" FAILED ({r.status_code}): {r.text[:300]}", flush=True)
            r.raise_for_status()
        data = r.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"LLM returned no choices. Response: {data}")

    text = choices[0].get("message", {}).get("content") or ""
    if not text.strip():
        raise RuntimeError("LLM returned empty content")

    print(f" done", flush=True)
    return _parse_json_response(text)


def _minimax_call(system_prompt: str, user_prompt: str, api_key: str) -> dict:
    """Call MiniMax proprietary API (different response format)."""
    import httpx

    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io")
    model = os.getenv("MINIMAX_LLM_MODEL", "MiniMax-M2")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4096,
        "temperature": 0.7,
    }

    print(f"  [LLM] {model} via MiniMax ...", end="", flush=True)
    with httpx.Client(timeout=120) as client:
        r = client.post(
            f"{base_url}/v1/text/chatcompletion_v2",
            headers=headers,
            json=body,
        )
        r.raise_for_status()
        data = r.json()

    if data.get("base_resp", {}).get("status_code", 0) != 0:
        msg = data.get("base_resp", {}).get("status_msg", "unknown error")
        raise RuntimeError(f"MiniMax LLM error: {msg}")

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("MiniMax returned no choices")

    text = choices[0].get("message", {}).get("content") or ""
    if not text.strip():
        raise RuntimeError("MiniMax returned empty content")

    print(f" done", flush=True)
    return _parse_json_response(text)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict:
    """Extract and parse JSON from LLM response, handling markdown fences."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = text.strip()

    if not text.startswith("{") and not text.startswith("["):
        start = text.find("{")
        if start >= 0:
            end = text.rfind("}") + 1
            if end > start:
                text = text[start:end]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text, "_parse_error": True}


def _mock_response(user_prompt: str) -> dict:
    """Return a plausible mock response for offline testing."""
    prompt_lower = user_prompt.lower()

    if "segment" in prompt_lower or "topic" in prompt_lower or "identify" in prompt_lower:
        return {
            "topics": [
                {
                    "topic_name": "Introduction & Overview",
                    "start_time": "0:00",
                    "end_time": "3:00",
                    "key_points": [
                        "Course overview and objectives",
                        "Why this topic matters",
                    ],
                    "related_slides": [1, 2],
                    "visual_elements": ["title slide", "overview diagram on slide 2"],
                },
                {
                    "topic_name": "Core Concept Explanation",
                    "start_time": "3:00",
                    "end_time": "8:00",
                    "key_points": [
                        "Main definition and terminology",
                        "Step-by-step breakdown",
                        "Key formula or process",
                    ],
                    "related_slides": [3, 4, 5],
                    "visual_elements": ["diagram on slide 3", "formula on slide 5"],
                },
                {
                    "topic_name": "Examples & Applications",
                    "start_time": "8:00",
                    "end_time": "12:00",
                    "key_points": [
                        "Worked example",
                        "Real-world application",
                    ],
                    "related_slides": [6, 7],
                    "visual_elements": ["example walkthrough on slide 6"],
                },
            ]
        }

    return {
        "reels": [
            {
                "topic": "Mock Topic — Core Concept",
                "hook": "Did you know most students get this wrong?",
                "narration": (
                    "Here's something your textbook won't tell you. "
                    "The key concept here is actually simpler than you think. "
                    "Let me break it down in 30 seconds."
                ),
                "visual_directions": [
                    {
                        "time_offset_sec": 0,
                        "duration_sec": 3,
                        "type": "text_overlay",
                        "description": "Bold hook text on screen",
                        "source": "generate",
                    },
                    {
                        "time_offset_sec": 3,
                        "duration_sec": 12,
                        "type": "slide",
                        "description": "Show main diagram, zoom into key area",
                        "source": "slide 3",
                    },
                    {
                        "time_offset_sec": 15,
                        "duration_sec": 10,
                        "type": "video_clip",
                        "description": "Professor explaining with whiteboard",
                        "source": "video 3:20-3:30",
                    },
                    {
                        "time_offset_sec": 25,
                        "duration_sec": 5,
                        "type": "text_overlay",
                        "description": "Key takeaway bullet points",
                        "source": "generate",
                    },
                ],
                "key_takeaway": "The core concept is simpler than it seems when broken down.",
                "quiz_question": "What is the main idea behind this concept?",
                "quiz_choices": [
                    "Option A (correct)",
                    "Option B",
                    "Option C",
                    "Option D",
                ],
                "quiz_answer_index": 0,
                "caption": "This changed how I study forever #learnontiktok #studytok",
                "music_mood": "calm",
            }
        ]
    }

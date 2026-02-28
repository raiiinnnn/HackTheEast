"""Amazon Bedrock syllabus parsing service.
Accepts raw PDF bytes, extracts text, calls Bedrock Converse API
(Amazon Nova Pro) to return structured programming topics JSON."""

import io
import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError
from PyPDF2 import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)

SYLLABUS_PROMPT = """CRITICAL: Return ONLY valid JSON. NO OTHER TEXT.

From this syllabus PDF, extract ONLY the PROGRAMMING TOPICS that will be taught.

TASK: Find section titled "Topics" or "Topics Covered" and extract THOSE programming topics ONLY.

IGNORE: logistics, instructors, grading, schedule, labs, policies.

EXAMPLE OUTPUT (for COMP 1023 Python course):
{{
  "course_name": "COMP 1023 Introduction to Python Programming",
  "topics": [
    {{
      "topic": "Introduction to Computers and Programming",
      "subtopics": [],
      "weight": 0.08
    }},
    {{
      "topic": "Python Programming Fundamentals",
      "subtopics": [],
      "weight": 0.10
    }},
    {{
      "topic": "Branching Statements",
      "subtopics": [],
      "weight": 0.08
    }},
    {{
      "topic": "Looping Statements",
      "subtopics": [],
      "weight": 0.08
    }},
    {{
      "topic": "Collections – Container Data Types",
      "subtopics": [],
      "weight": 0.12
    }},
    {{
      "topic": "Modularization – Functions and Recursions",
      "subtopics": [],
      "weight": 0.10
    }},
    {{
      "topic": "Modularization – Modules, Packages, and Libraries",
      "subtopics": [],
      "weight": 0.10
    }},
    {{
      "topic": "Object-Oriented Programming",
      "subtopics": [],
      "weight": 0.12
    }},
    {{
      "topic": "NumPy",
      "subtopics": [],
      "weight": 0.08
    }},
    {{
      "topic": "Pandas",
      "subtopics": [],
      "weight": 0.07
    }},
    {{
      "topic": "Matplotlib",
      "subtopics": [],
      "weight": 0.07
    }}
  ]
}}

PDF TEXT: {extracted_text}

Respond with ONLY the JSON above. No explanations."""

MAX_RETRIES = 2


def _get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_DEFAULT_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _parse_json_from_llm(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM output, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def _validate_syllabus_json(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data.get("course_name"), str):
        raise ValueError("Missing or invalid 'course_name'")
    if not isinstance(data.get("topics"), list) or len(data["topics"]) == 0:
        raise ValueError("Missing or empty 'topics' array")
    for t in data["topics"]:
        if not isinstance(t.get("topic"), str):
            raise ValueError(f"Invalid topic entry: {t}")
        if not isinstance(t.get("subtopics"), list):
            t["subtopics"] = []
        if "weight" not in t or not isinstance(t["weight"], (int, float)):
            t["weight"] = 0.0
    return data


async def parse_syllabus_pdf(
    pdf_bytes: bytes,
    course_context: str | None = None,
) -> Dict[str, Any]:
    """PDF bytes -> text extraction -> Bedrock LLM -> validated JSON."""
    extracted_text = extract_text_from_pdf(pdf_bytes)
    if not extracted_text.strip():
        raise ValueError("Could not extract any text from the PDF")

    if len(extracted_text) > 60000:
        extracted_text = extracted_text[:60000]

    prompt_text = SYLLABUS_PROMPT.format(extracted_text=extracted_text)
    if course_context:
        prompt_text += f"\n\nAdditional context: {course_context}"

    client = _get_bedrock_client()
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.converse(
                modelId=settings.BEDROCK_MODEL_ID,
                messages=[
                    {"role": "user", "content": [{"text": prompt_text}]},
                ],
                inferenceConfig={
                    "maxTokens": 4096,
                    "temperature": 0.1,
                },
            )

            raw_text = response["output"]["message"]["content"][0]["text"]
            parsed = _parse_json_from_llm(raw_text)
            return _validate_syllabus_json(parsed)

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                f"Bedrock returned malformed JSON (attempt {attempt + 1}/{MAX_RETRIES + 1}): {e}"
            )
            prompt_text = (
                "Your previous response was NOT valid JSON. "
                "Return ONLY the raw JSON object. No markdown fences, no explanation.\n\n"
                + prompt_text
            )
        except (KeyError, ValueError) as e:
            last_error = e
            logger.warning(f"Bedrock response validation failed (attempt {attempt + 1}): {e}")
            prompt_text = (
                f"Schema error: {e}. Return ONLY valid JSON matching the exact schema.\n\n"
                + prompt_text
            )
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock: {e}")
            raise

    raise ValueError(f"Failed to get valid JSON after {MAX_RETRIES + 1} attempts: {last_error}")

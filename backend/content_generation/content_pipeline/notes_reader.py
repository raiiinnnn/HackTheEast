"""
Notes text extractor — reads .docx, .txt, and portrait-oriented PDF files
and returns the full text content as a single string.
"""

from __future__ import annotations

from pathlib import Path


def read_notes(path: str | Path) -> str:
    """Read text content from a notes file (.docx, .txt, or portrait PDF).

    Returns the full text as a single string with paragraphs separated by
    newlines.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Notes file not found: {path}")

    ext = path.suffix.lower()
    if ext == ".docx":
        return _read_docx(path)
    if ext == ".txt":
        return path.read_text(encoding="utf-8")
    if ext == ".pdf":
        return _read_pdf_text(path)
    if ext == ".doc":
        raise ValueError(
            f"Legacy .doc format is not supported — please save as .docx: {path}"
        )
    raise ValueError(f"Unsupported notes file type: {ext}")


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required for .docx files: pip install python-docx")

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _read_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for PDF files: pip install pypdf")

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)

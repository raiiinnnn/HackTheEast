"""
Slide/PDF content extractor.

Extracts per-page text, identifies structural elements (headings, bullet points,
formulas, diagram references), and provides page-level summaries for cross-referencing
with the video transcript.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SlideContent:
    """Content extracted from a single slide/page."""
    page_num: int
    raw_text: str
    title: str = ""
    bullet_points: list[str] = field(default_factory=list)
    has_diagram: bool = False
    has_formula: bool = False
    diagram_hint: str = ""
    key_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "page_num": self.page_num,
            "title": self.title,
            "raw_text": self.raw_text[:500],
            "bullet_points": self.bullet_points,
            "has_diagram": self.has_diagram,
            "has_formula": self.has_formula,
            "diagram_hint": self.diagram_hint,
            "key_terms": self.key_terms,
        }

    @property
    def summary(self) -> str:
        parts = [f"Slide {self.page_num}"]
        if self.title:
            parts.append(f'"{self.title}"')
        if self.has_diagram:
            hint = f" ({self.diagram_hint})" if self.diagram_hint else ""
            parts.append(f"[contains diagram{hint}]")
        if self.has_formula:
            parts.append("[contains formula/equation]")
        if self.bullet_points:
            parts.append(f"({len(self.bullet_points)} points)")
        return " — ".join(parts)


def detect_pdf_orientation(pdf_path: str | Path) -> str:
    """Check page 1 of a PDF and return ``"landscape"`` or ``"portrait"``.

    Landscape PDFs are treated as slides; portrait PDFs as notes/documents.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required: pip install pypdf")

    reader = PdfReader(str(pdf_path))
    if not reader.pages:
        return "portrait"

    page = reader.pages[0]
    box = page.mediabox
    width = float(box.width)
    height = float(box.height)
    return "landscape" if width > height else "portrait"


class SlideAnalyzer:
    """
    Extracts and analyzes content from PDF slides.

    Identifies per-page: text, titles, bullet points, diagrams, formulas.
    Uses pypdf for text extraction.
    """

    def analyze(self, pdf_path: str | Path) -> list[SlideContent]:
        """
        Analyze a PDF file and return per-page SlideContent.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of SlideContent, one per page.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("pypdf is required: pip install pypdf")

        reader = PdfReader(str(pdf_path))
        slides: list[SlideContent] = []

        print(f"  Analyzing {len(reader.pages)} slides from {pdf_path.name}...")

        for i, page in enumerate(reader.pages):
            raw_text = page.extract_text() or ""
            slide = self._analyze_page(i + 1, raw_text)
            slides.append(slide)

        non_empty = sum(1 for s in slides if s.raw_text.strip())
        print(f"  ✓ Extracted content from {non_empty}/{len(slides)} slides.")
        return slides

    def _analyze_page(self, page_num: int, raw_text: str) -> SlideContent:
        """Analyze a single page's text content."""
        lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]

        title = self._extract_title(lines)
        bullets = self._extract_bullets(lines)
        has_diagram = self._detect_diagram(raw_text, lines)
        has_formula = self._detect_formula(raw_text)
        diagram_hint = self._get_diagram_hint(raw_text, lines) if has_diagram else ""
        key_terms = self._extract_key_terms(raw_text)

        return SlideContent(
            page_num=page_num,
            raw_text=raw_text,
            title=title,
            bullet_points=bullets,
            has_diagram=has_diagram,
            has_formula=has_formula,
            diagram_hint=diagram_hint,
            key_terms=key_terms,
        )

    def _extract_title(self, lines: list[str]) -> str:
        if not lines:
            return ""
        candidate = lines[0]
        if len(candidate) < 100 and not candidate.startswith(("•", "-", "–", "*", "▪")):
            return candidate
        return ""

    def _extract_bullets(self, lines: list[str]) -> list[str]:
        bullets = []
        for ln in lines:
            if re.match(r'^[•\-–\*▪◦▸►]\s*', ln):
                text = re.sub(r'^[•\-–\*▪◦▸►]\s*', '', ln).strip()
                if text:
                    bullets.append(text)
            elif re.match(r'^\d+[\.\)]\s+', ln):
                text = re.sub(r'^\d+[\.\)]\s+', '', ln).strip()
                if text:
                    bullets.append(text)
        return bullets

    def _detect_diagram(self, raw_text: str, lines: list[str]) -> bool:
        diagram_keywords = [
            "figure", "fig.", "diagram", "chart", "graph", "table",
            "illustration", "flowchart", "architecture",
        ]
        text_lower = raw_text.lower()
        if any(kw in text_lower for kw in diagram_keywords):
            return True
        if len(lines) < 3 and len(raw_text) < 50:
            return True
        return False

    def _detect_formula(self, raw_text: str) -> bool:
        formula_patterns = [
            r'[=∑∏∫∂√∞≈≠≤≥]',
            r'\b[a-z]\s*=\s*[a-z0-9]',
            r'\bx\^[0-9]',
            r'\\frac\b',
            r'\\sum\b',
            r'\bf\s*\(\s*x\s*\)',
        ]
        return any(re.search(pat, raw_text) for pat in formula_patterns)

    def _get_diagram_hint(self, raw_text: str, lines: list[str]) -> str:
        text_lower = raw_text.lower()
        for kw in ["flowchart", "architecture", "graph", "chart", "table", "diagram", "figure"]:
            if kw in text_lower:
                for ln in lines:
                    if kw in ln.lower():
                        return ln.strip()[:80]
        if len(lines) < 3:
            return "slide appears to be mostly visual/diagram"
        return ""

    def _extract_key_terms(self, raw_text: str) -> list[str]:
        """Extract words that look like key terms (capitalized, technical-looking)."""
        words = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', raw_text)
        common = {"This", "That", "These", "Those", "What", "When", "Where", "Which",
                   "With", "From", "About", "Into", "They", "Their", "There", "Have",
                   "Will", "Would", "Could", "Should", "Each", "More", "Some", "Also",
                   "Other", "After", "Before", "Between", "Does", "However", "Because"}
        terms = [w for w in words if w not in common]
        seen = set()
        unique = []
        for t in terms:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique[:15]

    def get_all_text(self, slides: list[SlideContent]) -> str:
        """Combine all slide text into a single string with page markers."""
        parts = []
        for s in slides:
            if s.raw_text.strip():
                parts.append(f"--- Slide {s.page_num} ---\n{s.raw_text.strip()}")
        return "\n\n".join(parts)

    def get_slide_summaries(self, slides: list[SlideContent]) -> str:
        """One-line summary per slide for LLM context."""
        return "\n".join(s.summary for s in slides if s.raw_text.strip())

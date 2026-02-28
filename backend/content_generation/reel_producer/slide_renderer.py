"""
Slide renderer — converts PDF pages to vertical (1080x1920) images for reels.

Centers slide content on a gradient dark background with an optional text annotation
panel at the bottom. Can also overlay text descriptions on top of slides.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

REEL_WIDTH = 1080
REEL_HEIGHT = 1920


class SlideRenderer:
    """Render PDF slide pages as vertical images suitable for reels."""

    def __init__(
        self,
        bg_top: tuple[int, int, int] = (18, 18, 35),
        bg_bottom: tuple[int, int, int] = (8, 8, 16),
        slide_margin: int = 40,
    ):
        self.bg_top = bg_top
        self.bg_bottom = bg_bottom
        self.slide_margin = slide_margin
        self._pdf_doc = None
        self._pdf_path: str | None = None
        self._page_count: int = 0

    def load_pdf(self, pdf_path: str | Path) -> int:
        """Load a PDF and return the number of pages."""
        try:
            import fitz
        except ImportError:
            raise ImportError("pymupdf is required: pip install pymupdf")

        self._pdf_path = str(pdf_path)
        self._pdf_doc = fitz.open(self._pdf_path)
        self._page_count = len(self._pdf_doc)
        return self._page_count

    @property
    def page_count(self) -> int:
        return self._page_count

    def render_page(
        self,
        page_num: int,
        output_path: str | Path,
        annotation: str = "",
    ) -> Path:
        """
        Render a PDF page as vertical 1080x1920 image with optional annotation text.

        page_num is 1-indexed. If annotation is provided, it appears in a styled
        panel below the slide.
        """
        from PIL import Image, ImageDraw, ImageFont

        if self._pdf_doc is None:
            raise RuntimeError("No PDF loaded. Call load_pdf() first.")

        idx = page_num - 1
        if idx < 0 or idx >= self._page_count:
            return self._render_placeholder(f"Slide {page_num}", annotation, output_path)

        page = self._pdf_doc[idx]
        scale = 3.0
        import fitz as _fitz
        mat = _fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        slide_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        canvas = self._gradient_canvas()

        if annotation:
            slide_area_h = int(REEL_HEIGHT * 0.50)
            slide_y_start = int(REEL_HEIGHT * 0.08)
        else:
            slide_area_h = int(REEL_HEIGHT * 0.65)
            slide_y_start = int(REEL_HEIGHT * 0.12)

        available_w = REEL_WIDTH - 2 * self.slide_margin
        ratio = min(available_w / slide_img.width, slide_area_h / slide_img.height)
        new_w = int(slide_img.width * ratio)
        new_h = int(slide_img.height * ratio)
        slide_img = slide_img.resize((new_w, new_h), Image.LANCZOS)

        x = (REEL_WIDTH - new_w) // 2
        y = slide_y_start + (slide_area_h - new_h) // 2

        draw = ImageDraw.Draw(canvas)
        shadow_pad = 8
        draw.rounded_rectangle(
            (x - shadow_pad, y - shadow_pad, x + new_w + shadow_pad, y + new_h + shadow_pad),
            radius=12, fill=(5, 5, 12),
        )

        canvas.paste(slide_img, (x, y))

        if annotation:
            self._draw_annotation(canvas, annotation, slide_y_start + slide_area_h + 30)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(str(output_path), "PNG")
        return output_path

    def render_page_cropped(
        self,
        page_num: int,
        output_path: str | Path,
        annotation: str = "",
        focus_region: tuple[float, float, float, float] | None = None,
    ) -> Path:
        """Render a zoomed/cropped region of a slide for close-up visuals."""
        from PIL import Image

        if self._pdf_doc is None:
            raise RuntimeError("No PDF loaded. Call load_pdf() first.")

        idx = page_num - 1
        if idx < 0 or idx >= self._page_count:
            return self._render_placeholder(f"Slide {page_num}", annotation, output_path)

        page = self._pdf_doc[idx]
        scale = 4.0
        import fitz as _fitz
        mat = _fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        slide_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if focus_region:
            xf, yf, wf, hf = focus_region
            cx = int(xf * slide_img.width)
            cy = int(yf * slide_img.height)
            cw = int(wf * slide_img.width)
            ch = int(hf * slide_img.height)
            slide_img = slide_img.crop((cx, cy, cx + cw, cy + ch))

        canvas = self._gradient_canvas()

        available_w = REEL_WIDTH - 2 * self.slide_margin
        available_h = int(REEL_HEIGHT * 0.60)

        ratio = min(available_w / slide_img.width, available_h / slide_img.height)
        new_w = int(slide_img.width * ratio)
        new_h = int(slide_img.height * ratio)
        slide_img = slide_img.resize((new_w, new_h), Image.LANCZOS)

        x = (REEL_WIDTH - new_w) // 2
        y = int(REEL_HEIGHT * 0.15)

        canvas.paste(slide_img, (x, y))

        if annotation:
            self._draw_annotation(canvas, annotation, y + new_h + 40)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(str(output_path), "PNG")
        return output_path

    def get_slide_image(self, page_num: int) -> "Image.Image | None":
        """Get a raw PIL Image of a slide page (for compositing elsewhere)."""
        from PIL import Image

        if self._pdf_doc is None:
            return None
        idx = page_num - 1
        if idx < 0 or idx >= self._page_count:
            return None
        page = self._pdf_doc[idx]
        import fitz as _fitz
        mat = _fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    def render_page_raw(self, page_num: int, output_path: str | Path) -> Path:
        """Render a PDF page as a flat image at its natural aspect ratio (no vertical canvas)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = self.get_slide_image(page_num)
        if img is None:
            return self._render_placeholder(f"Slide {page_num}", "", output_path)
        img.save(str(output_path), "PNG")
        return output_path

    def _gradient_canvas(self) -> "Image.Image":
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (REEL_WIDTH, REEL_HEIGHT))
        draw = ImageDraw.Draw(img)
        for y in range(REEL_HEIGHT):
            t = y / REEL_HEIGHT
            r = int(self.bg_top[0] * (1 - t) + self.bg_bottom[0] * t)
            g = int(self.bg_top[1] * (1 - t) + self.bg_bottom[1] * t)
            b = int(self.bg_top[2] * (1 - t) + self.bg_bottom[2] * t)
            draw.line([(0, y), (REEL_WIDTH, y)], fill=(r, g, b))
        return img

    def _draw_annotation(self, canvas: "Image.Image", text: str, y_start: int):
        from PIL import Image, ImageDraw, ImageFont

        overlay = Image.new("RGBA", (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        margin = 40
        panel_h = min(450, REEL_HEIGHT - y_start - 60)

        ov_draw.rounded_rectangle(
            (margin, y_start, REEL_WIDTH - margin, y_start + panel_h),
            radius=20, fill=(12, 12, 28, 200),
        )

        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba = Image.alpha_composite(canvas_rgba, overlay)
        final = canvas_rgba.convert("RGB")
        canvas.paste(final)

        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except OSError:
            font = ImageFont.load_default()

        wrapped = textwrap.fill(text, width=34)
        draw.multiline_text(
            (margin + 24, y_start + 24), wrapped,
            fill=(220, 220, 230), font=font, spacing=10,
        )

    def _render_placeholder(
        self, label: str, annotation: str, output_path: str | Path
    ) -> "Path":
        from PIL import ImageDraw, ImageFont

        canvas = self._gradient_canvas()
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("arial.ttf", 52)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((REEL_WIDTH - tw) // 2, REEL_HEIGHT // 3),
            label, fill=(120, 120, 140), font=font,
        )
        if annotation:
            self._draw_annotation(canvas, annotation, REEL_HEIGHT // 2)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(str(output_path), "PNG")
        return output_path

    def close(self):
        if self._pdf_doc:
            self._pdf_doc.close()
            self._pdf_doc = None

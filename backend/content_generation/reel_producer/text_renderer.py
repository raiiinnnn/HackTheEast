"""
Text overlay renderer — creates modern, TikTok-style vertical images for reels.

Uses gradient backgrounds, accent panels, large bold typography, and clean design
optimized for mobile vertical viewing (1080x1920).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

REEL_WIDTH = 1080
REEL_HEIGHT = 1920

# Color palette
BG_DARK = (12, 12, 20)
BG_PANEL = (25, 25, 45)
ACCENT_BLUE = (80, 160, 255)
ACCENT_GREEN = (80, 220, 160)
ACCENT_PURPLE = (160, 100, 255)
ACCENT_ORANGE = (255, 160, 60)
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 210)
DIM_GRAY = (100, 100, 120)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        ["arialbd.ttf", "Arial Bold.ttf", "Impact.ttf"] if bold
        else ["arial.ttf", "Arial.ttf", "calibri.ttf", "DejaVuSans.ttf"]
    )
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient_bg(
    w: int = REEL_WIDTH,
    h: int = REEL_HEIGHT,
    top: tuple[int, int, int] = (15, 15, 35),
    bottom: tuple[int, int, int] = (8, 8, 18),
) -> Image.Image:
    """Create a vertical gradient background."""
    img = Image.new("RGB", (w, h))
    for y in range(h):
        t = y / h
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        ImageDraw.Draw(img).line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _rounded_rect(
    draw: ImageDraw.Draw,
    xy: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    radius: int = 20,
    outline: tuple[int, int, int] | None = None,
):
    """Draw a rounded rectangle."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


class TextRenderer:
    """Modern TikTok-style text overlays for reels."""

    def render_hook(self, text: str, output_path: str | Path) -> Path:
        """Big bold hook text — fills the screen, attention-grabbing."""
        canvas = _gradient_bg(top=(20, 10, 40), bottom=(10, 5, 20))
        draw = ImageDraw.Draw(canvas)

        font_big = _font(80, bold=True)
        wrapped = textwrap.fill(text, width=14)

        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font_big, spacing=20)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (REEL_WIDTH - tw) // 2
        y = (REEL_HEIGHT - th) // 2 - 60

        for dx, dy in [(3, 3), (-1, -1), (2, 0), (0, 2)]:
            draw.multiline_text(
                (x + dx, y + dy), wrapped,
                fill=(0, 0, 0), font=font_big, spacing=20, align="center",
            )

        draw.multiline_text(
            (x, y), wrapped,
            fill=ACCENT_BLUE, font=font_big, spacing=20, align="center",
        )

        tag_font = _font(32)
        tag = "SWIPE TO LEARN"
        tbbox = draw.textbbox((0, 0), tag, font=tag_font)
        tgw = tbbox[2] - tbbox[0]
        draw.text(
            ((REEL_WIDTH - tgw) // 2, y + th + 80),
            tag, fill=DIM_GRAY, font=tag_font,
        )

        return self._save(canvas, output_path)

    def render_text_overlay(self, text: str, output_path: str | Path) -> Path:
        """Text content in a styled panel — for explanations, descriptions."""
        canvas = _gradient_bg()
        draw = ImageDraw.Draw(canvas)
        margin = 60

        _rounded_rect(
            draw,
            (margin, REEL_HEIGHT // 2 - 350, REEL_WIDTH - margin, REEL_HEIGHT // 2 + 350),
            fill=(20, 20, 40),
            radius=30,
            outline=ACCENT_BLUE,
        )

        font = _font(46)
        wrapped = textwrap.fill(text, width=26)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=18)
        th = bbox[3] - bbox[1]
        y = (REEL_HEIGHT - th) // 2

        draw.multiline_text(
            (margin + 40, y), wrapped,
            fill=WHITE, font=font, spacing=18,
        )

        return self._save(canvas, output_path)

    def render_text_on_slide(
        self, slide_img: Image.Image, text: str, output_path: str | Path
    ) -> Path:
        """Render text in a panel at the bottom third, overlaid on a slide."""
        canvas = slide_img.copy().resize((REEL_WIDTH, REEL_HEIGHT), Image.LANCZOS)
        draw = ImageDraw.Draw(canvas)
        margin = 40

        panel_h = 420
        panel_y = REEL_HEIGHT - panel_h - 120

        overlay = Image.new("RGBA", (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        ov_draw.rounded_rectangle(
            (margin, panel_y, REEL_WIDTH - margin, panel_y + panel_h),
            radius=24,
            fill=(10, 10, 25, 210),
        )
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)

        font = _font(38)
        wrapped = textwrap.fill(text, width=32)
        draw.multiline_text(
            (margin + 30, panel_y + 30), wrapped,
            fill=WHITE, font=font, spacing=12,
        )

        return self._save(canvas, output_path)

    def render_key_takeaway(self, text: str, output_path: str | Path) -> Path:
        """Key takeaway with accent header bar and styled body."""
        canvas = _gradient_bg(top=(10, 20, 30), bottom=(5, 10, 18))
        draw = ImageDraw.Draw(canvas)
        margin = 60

        bar_y = REEL_HEIGHT // 2 - 220
        draw.rectangle(
            (0, bar_y, REEL_WIDTH, bar_y + 6), fill=ACCENT_GREEN,
        )

        header_font = _font(38, bold=True)
        draw.text(
            (margin, bar_y + 30), "KEY TAKEAWAY",
            fill=ACCENT_GREEN, font=header_font,
        )

        body_font = _font(50)
        wrapped = textwrap.fill(text, width=22)
        draw.multiline_text(
            (margin, bar_y + 100), wrapped,
            fill=WHITE, font=body_font, spacing=18,
        )

        return self._save(canvas, output_path)

    def render_quiz(
        self,
        question: str,
        choices: list[str],
        answer_index: int,
        output_path: str | Path,
        show_answer: bool = False,
    ) -> Path:
        """Quiz with styled choice boxes."""
        canvas = _gradient_bg(top=(20, 10, 35), bottom=(10, 5, 20))
        draw = ImageDraw.Draw(canvas)
        margin = 60

        header_font = _font(36, bold=True)
        draw.text(
            (margin, REEL_HEIGHT // 2 - 380), "QUIZ TIME",
            fill=ACCENT_PURPLE, font=header_font,
        )

        q_font = _font(42, bold=True)
        q_wrapped = textwrap.fill(question, width=26)
        draw.multiline_text(
            (margin, REEL_HEIGHT // 2 - 320), q_wrapped,
            fill=WHITE, font=q_font, spacing=12,
        )
        qbbox = draw.multiline_textbbox(
            (margin, REEL_HEIGHT // 2 - 320), q_wrapped, font=q_font, spacing=12,
        )
        y = qbbox[3] + 40

        labels = ["A", "B", "C", "D"]
        c_font = _font(36)
        for i, choice in enumerate(choices[:4]):
            box_fill = (20, 20, 40)
            box_outline = (50, 50, 70)
            text_color = WHITE

            if show_answer and i == answer_index:
                box_fill = (20, 60, 30)
                box_outline = ACCENT_GREEN
                text_color = ACCENT_GREEN
            elif show_answer:
                text_color = DIM_GRAY
                box_outline = (40, 40, 50)

            _rounded_rect(
                draw,
                (margin, y, REEL_WIDTH - margin, y + 70),
                fill=box_fill, radius=12, outline=box_outline,
            )

            label_font = _font(34, bold=True)
            draw.text((margin + 20, y + 18), f"{labels[i]}", fill=ACCENT_BLUE, font=label_font)
            draw.text((margin + 60, y + 20), choice[:40], fill=text_color, font=c_font)
            y += 90

        return self._save(canvas, output_path)

    def render_concept_card(
        self, description: str, output_path: str | Path, accent: str = "blue",
    ) -> Path:
        """
        Concept card for the bottom half of a split-screen reel.

        Shows the visual description as a styled card with:
        - Gradient dark background
        - Accent-colored title bar
        - Large, readable text
        - Code-style formatting for code-like content
        """
        canvas = _gradient_bg(
            REEL_WIDTH, REEL_HEIGHT,
            top=(18, 12, 35), bottom=(8, 5, 18),
        )
        draw = ImageDraw.Draw(canvas)

        colors = {
            "blue": ACCENT_BLUE,
            "green": ACCENT_GREEN,
            "purple": ACCENT_PURPLE,
            "orange": ACCENT_ORANGE,
        }
        accent_color = colors.get(accent, ACCENT_BLUE)

        margin = 50

        # Accent bar at top
        draw.rectangle(
            (0, 60, REEL_WIDTH, 68), fill=accent_color,
        )

        # Label
        label_font = _font(30, bold=True)
        draw.text((margin, 85), "CONCEPT BREAKDOWN", fill=accent_color, font=label_font)

        # Check if description contains code-like content
        has_code = any(c in description for c in ["<<", ">>", "==", "()", "[]", ";", "++", "->", "int ", "cout"])

        if has_code:
            self._draw_code_block(draw, description, margin, 150, canvas)
        else:
            self._draw_text_block(draw, description, margin, 150, accent_color)

        return self._save(canvas, output_path)

    def _draw_code_block(
        self, draw: ImageDraw.Draw, text: str, margin: int, y: int, canvas: Image.Image,
    ):
        """Draw code-like content in a styled code block."""
        # Code background panel
        _rounded_rect(
            draw,
            (margin, y, REEL_WIDTH - margin, y + 600),
            fill=(15, 15, 30), radius=16,
            outline=(60, 60, 80),
        )

        # Terminal dots
        for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            draw.ellipse(
                (margin + 20 + i * 28, y + 18, margin + 36 + i * 28, y + 34),
                fill=color,
            )

        code_font = _font(36)
        lines = text.split(";")
        code_y = y + 55
        for line in lines[:12]:
            line = line.strip()
            if not line:
                continue
            if len(line) > 40:
                line = line[:40] + "..."
            draw.text(
                (margin + 24, code_y), line,
                fill=(200, 220, 255), font=code_font,
            )
            code_y += 48

    def _draw_text_block(
        self, draw: ImageDraw.Draw, text: str, margin: int, y: int,
        accent: tuple[int, int, int],
    ):
        """Draw description text in a styled panel."""
        # Main text
        body_font = _font(44)
        wrapped = textwrap.fill(text, width=24)
        lines = wrapped.split("\n")

        for i, line in enumerate(lines[:10]):
            color = accent if i == 0 else WHITE
            draw.text(
                (margin + 10, y + i * 58), line,
                fill=color, font=body_font,
            )

    def _save(self, img: Image.Image, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(str(path), "PNG")
        return path

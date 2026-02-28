"""
Instagram Reels-style karaoke subtitles with vibrant color pop.

The ACTIVE word pops in a cycling bright color (pink -> cyan -> green -> orange)
with bold weight + slight scale bump. Inactive words glow soft white.
Font: rounded sans-serif look via "Arial Rounded MT Bold" with fallback to "Arial Black".

Uses stable-ts for word-level timestamps from each clip's audio.
"""

from __future__ import annotations

from pathlib import Path

REEL_WIDTH = 1080
REEL_HEIGHT = 1920

# ASS colors are &HAABBGGRR (hex, reversed from RGB)
POP_COLORS = [
    "&H008040FF",  # hot pink / magenta  (#FF4080)
    "&H00FFFF00",  # cyan                (#00FFFF)
    "&H0000E87A",  # vivid green         (#7AE800)
    "&H000896FF",  # orange              (#FF9608)
    "&H00FF5555",  # electric blue       (#5555FF)
    "&H00AA44FF",  # purple              (#FF44AA)
]
INACTIVE = "&H00FFFFFF"  # clean white
FONT_NAME = "Arial Black"
FONT_SIZE = 62
MARGIN_V = 400
WORDS_PER_GROUP = 4


def transcribe_clip_words(clip_path: str | Path) -> list[dict]:
    """
    Transcribe a short clip and return word-level timestamps.

    Returns list of {word, start, end}.
    """
    try:
        import stable_whisper
    except ImportError:
        print("      [subs] stable-ts not installed, skipping subs")
        return []

    clip_path = Path(clip_path)
    if not clip_path.exists():
        return []

    print("      [subs] transcribing for word timestamps...", end="", flush=True)
    try:
        model = _get_model()
        result = model.transcribe(str(clip_path), word_timestamps=True, fp16=False)

        words = []
        for seg in result.segments:
            for w in seg.words:
                text = w.word.strip()
                if text:
                    words.append({"word": text, "start": w.start, "end": w.end})

        print(f" {len(words)} words", flush=True)
        return words
    except Exception as e:
        print(f" failed: {e}", flush=True)
        return []


_cached_model = None

def _get_model():
    global _cached_model
    if _cached_model is None:
        import stable_whisper
        print("      [subs] loading whisper model...", end="", flush=True)
        _cached_model = stable_whisper.load_model("base")
        print(" ready", flush=True)
    return _cached_model


def generate_subtitles_multi(
    clip_word_lists: list[tuple[float, list[dict]]],
    output_path: str | Path,
) -> Path | None:
    """
    Generate IG Reels-style karaoke subtitles from multiple clips' word lists.

    Active word pops in a cycling bright color with bold + scale.
    Inactive words stay clean white. Group of 4 words at a time.
    """
    all_words: list[dict] = []
    for time_offset, words in clip_word_lists:
        for w in words:
            all_words.append({
                "word": w["word"],
                "start": w["start"] + time_offset,
                "end": w["end"] + time_offset,
            })

    if not all_words:
        return None

    groups: list[list[dict]] = []
    for i in range(0, len(all_words), WORDS_PER_GROUP):
        group = all_words[i:i + WORDS_PER_GROUP]
        if group:
            groups.append(group)

    dialogues: list[str] = []
    color_idx = 0

    for group in groups:
        group_start = group[0]["start"]
        group_end = group[-1]["end"]
        if group_end - group_start < 0.1:
            group_end = group_start + 0.5

        pop_color = POP_COLORS[color_idx % len(POP_COLORS)]
        color_idx += 1

        for active_idx, active_word in enumerate(group):
            w_start = active_word["start"]
            if active_idx + 1 < len(group):
                w_end = group[active_idx + 1]["start"]
            else:
                w_end = group_end
            if w_end - w_start < 0.05:
                w_end = w_start + 0.15

            parts: list[str] = []
            for j, w in enumerate(group):
                safe = w["word"].upper().replace("{", "").replace("}", "")
                if j == active_idx:
                    # Active: pop color, bold, slightly scaled up
                    parts.append(
                        f"{{\\c{pop_color}}}{{\\b1}}{{\\fscx110\\fscy110}}"
                        f"{safe}"
                        f"{{\\fscx100\\fscy100}}{{\\b0}}"
                    )
                else:
                    parts.append(f"{{\\c{INACTIVE}}}{safe}")

            text = " ".join(parts)
            dialogues.append(
                f"Dialogue: 0,{_fmt(w_start)},{_fmt(w_end)},Default,,0,0,0,,{text}"
            )

    if not dialogues:
        return None

    output_path = Path(output_path)
    _write_ass(dialogues, output_path)
    return output_path


def _write_ass(dialogues: list[str], output_path: Path):
    content = f"""[Script Info]
Title: DoomLearn Subtitles
ScriptType: v4.00+
PlayResX: {REEL_WIDTH}
PlayResY: {REEL_HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_NAME},{FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,0,0,0,0,100,100,1,0,1,4,3,2,40,40,{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    content += "\n".join(dialogues) + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8-sig")


def _fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

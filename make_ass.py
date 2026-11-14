import json
import subprocess
import sys
from pathlib import Path


def video_size(video: Path) -> tuple[int, int]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def ts(t: float) -> str:
    """seconds -> H:MM:SS.cc (ASS format)"""
    cs = round(t * 100)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def chunk(words, max_words=1, max_gap=0.6):
    """Group words into single word chunks chronologically."""
    # Words ko time ke hisaab se sort karo taaki koi order break na ho
    sorted_words = sorted(words, key=lambda w: w["start"])
    chunks, cur = [], []
    for w in sorted_words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w["word"].strip().endswith((".", "?", "!")):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(words, width, height) -> str:
    # --- FONT & SIZE ---
    font_name = "Arial Black"
    base_size = round(height * 0.055)

    # --- STROKES (OUTLINE & SHADOW) ---
    outline = max(4, round(height * 0.004))  # Thick black stroke around corner
    shadow = max(2, round(height * 0.002))  # Drop shadow

    # --- COLORS (&HAABBGGRR) ---
    primary_color = "&H00FFFFFF"  # Pure full white
    secondary_color = "&H00FFFFFF"  # Pure full white
    outline_color = "&H00000000"  # Pure black border
    back_color = "&H80000000"  # Shadow color

    # --- EXACT LOCKED POSITION (70% HEIGHT) ---
    # Har word ka center point fix coordinate par freeze ho jayega
    pos_x = round(width / 2)
    pos_y = round(height * 0.70)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{base_size},{primary_color},{secondary_color},{outline_color},{back_color},-1,0,0,0,100,100,0,0,1,{outline},{shadow},5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    chunks = chunk(words, max_words=1)
    lines = []
    prev_end = 0.0

    for idx, c in enumerate(chunks):
        # 1. Puraane word ke end hone se pehle naya word start nahi ho sakta
        start = max(c[0]["start"], prev_end)
        end = c[-1]["end"]

        # 2. Agle word ke start time ke aage yeh word extend nahi hoga
        if idx + 1 < len(chunks):
            next_start = chunks[idx + 1][0]["start"]
            if next_start > start:
                end = min(end, next_start)

        # 3. Minimum duration check
        if end <= start:
            end = start + 0.08

        prev_end = end

        # 4. Uppercase ensures exact same height across all words
        parts = []
        for i, wd in enumerate(c):
            nxt = c[i + 1]["start"] if i + 1 < len(c) else end
            k = max(1, round((nxt - wd["start"]) * 100))
            parts.append(f"{{\\k{k}}}{wd['word'].strip().upper()}")

        text = " ".join(parts)

        # 5. \an5\pos(pos_x, pos_y) locks position completely (0 jitter / 0 jumping)
        lines.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{{\\an5\\pos({pos_x},{pos_y})}}{text}"
        )

    return header + "\n".join(lines) + "\n"


if __name__ == "__main__":
    video = Path(sys.argv[1])
    data = json.loads(Path("output", f"{video.stem}.json").read_text(encoding="utf-8"))
    w, h = video_size(video)
    ass = build_ass(data["words"], w, h)
    out = Path("output", f"{video.stem}.ass")
    out.write_text(ass, encoding="utf-8")
    print(f"Wrote {out} ({w}x{h})")

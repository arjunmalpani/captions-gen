import json
import subprocess
import sys
from pathlib import Path


def video_size(video: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(video)],
        capture_output=True, text=True, check=True,
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


def chunk(words, max_words=4, max_gap=0.6):
    """Group words into short phrases. Break on max size, long pauses, or sentence end."""
    chunks, cur = [], []
    for w in words:
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
    base_size = round(height * 0.06)
    margin_lr = round(width * 0.125)          # leaves a 75% wide text area
    outline = max(2, round(height * 0.004))

    alignment = 8                              # top center: first line stays fixed
    caption_y = 0.70                           # 0.50 = center, 1.0 = bottom
    margin_v = round(height * caption_y)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{base_size},&H0000FFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline},0,{alignment},{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    chunks = chunk(words, max_words=1)
    lines = []
    for idx, c in enumerate(chunks):
        start = c[0]["start"]
        end = c[-1]["end"]

        # never overlap the next caption
        if idx + 1 < len(chunks):
            end = min(end, chunks[idx + 1][0]["start"])
        end = max(end, start + 0.05)

        parts = []
        for i, wd in enumerate(c):
            nxt = c[i + 1]["start"] if i + 1 < len(c) else end
            k = max(1, round((nxt - wd["start"]) * 100))
            parts.append(f"{{\\k{k}}}{wd['word'].strip()}")

        text = " ".join(parts)
        lines.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{text}"
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
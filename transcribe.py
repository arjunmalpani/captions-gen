import json
import sys
import subprocess
from pathlib import Path
import os

from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def extract_audio(video: Path | str, out_dir: Path | str = "output") -> Path:
    video_path = Path(video)
    output_dir = Path(out_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)

    audio = output_dir / f"{video_path.stem}.flac"

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn",          # drop video
            "-ac", "1",     # mono audio
            "-ar", "16000", # 16kHz
            "-sample_fmt", "s16",
            "-c:a", "flac",
            str(audio),
        ],
        check=True
    )
    return audio

def transcribe(audio:Path) -> dict:
    with open(audio, "rb") as file:
        result = client.audio.transcriptions.create(
            file=(audio.name, file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"],
            temperature=0,
            language="en"
        )
    return result.model_dump()

if __name__ == "__main__":
    video = Path(sys.argv[1])
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    audio = extract_audio(video, out_dir)
    print(f"Audio: {audio} ({audio.stat().st_size / 1_000_000:.1f} MB)")

    data = transcribe(audio)
    (out_dir / f"{video.stem}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(data["text"][:300])
    print("Segments:", len(data.get("segments", [])))
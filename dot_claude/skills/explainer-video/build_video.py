#!/usr/bin/env python3
"""Build a narrated video from a Marp deck.

Layout expected in the work dir (default: cwd, or pass as argv[1]):
  deck.md            - Marp source; one narration HTML comment per slide
  slides/deck.*.png  - one PNG per slide (marp --images png --image-scale 2)
  venv/bin/edge-tts  - optional; falls back to `edge-tts` on PATH

Produces video_work/ (per-slide mp3+mp4, reused on re-run) and output.mp4.
Env overrides: TTS_VOICE (en-US-AndrewNeural), TTS_RATE (+8%), TAIL_PAD (0.8).
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
DECK = HERE / "deck.md"
SLIDES = HERE / "slides"
WORK = HERE / "video_work"
OUT = HERE / "output.mp4"
VOICE = os.environ.get("TTS_VOICE", "en-US-AndrewNeural")
RATE = os.environ.get("TTS_RATE", "+8%")
TAIL_PAD = float(os.environ.get("TAIL_PAD", "0.8"))

venv_tts = HERE / "venv" / "bin" / "edge-tts"
EDGE_TTS = str(venv_tts) if venv_tts.exists() else shutil.which("edge-tts")
if not EDGE_TTS:
    sys.exit("edge-tts not found: create venv + `pip install edge-tts`, or install on PATH")


def extract_notes(md: str) -> list[str]:
    body = md.split("---\n", 2)[2]  # strip front matter (--- ... ---)
    slides = re.split(r"\n---\n", body)
    notes = []
    for slide in slides:
        comments = re.findall(r"<!--(.*?)-->", slide, re.DOTALL)
        text = " ".join(
            c.strip() for c in comments
            if not re.match(r"^\s*_?\w+\s*:", c.strip())  # skip directives like _class: lead
        )
        notes.append(re.sub(r"\s+", " ", text).strip())
    return notes


def dur(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def main() -> None:
    WORK.mkdir(exist_ok=True)
    notes = extract_notes(DECK.read_text())
    pngs = sorted(SLIDES.glob("deck.*.png"))
    assert len(pngs) == len(notes), f"{len(pngs)} slides vs {len(notes)} note blocks"

    segs = []
    for i, (png, note) in enumerate(zip(pngs, notes), 1):
        assert note, f"slide {i} has no narration comment"
        mp3 = WORK / f"seg{i:03d}.mp3"
        seg = WORK / f"seg{i:03d}.mp4"
        if not mp3.exists():
            subprocess.run(
                [EDGE_TTS, "--text", note, "--voice", VOICE, "--rate", RATE,
                 "--write-media", str(mp3)],
                check=True, capture_output=True,
            )
        if not seg.exists():
            t = dur(mp3) + TAIL_PAD
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-loop", "1", "-i", str(png), "-i", str(mp3),
                 "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p",
                 "-af", f"apad=pad_dur={TAIL_PAD}", "-t", f"{t:.3f}", "-r", "30",
                 "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", "20",
                 "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                 str(seg)],
                check=True,
            )
        segs.append(seg)
        print(f"[{i:02d}/{len(pngs)}] {seg.name} ready", flush=True)

    concat = WORK / "concat.txt"
    concat.write_text("".join(f"file '{s}'\n" for s in segs))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat), "-c", "copy", str(OUT)],
        check=True,
    )
    total = dur(OUT)
    print(f"DONE: {OUT}  ({total/60:.1f} min, {OUT.stat().st_size/1e6:.0f} MB)")


if __name__ == "__main__":
    main()

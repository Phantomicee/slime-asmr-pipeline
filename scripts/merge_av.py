# scripts/merge_av.py
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


VIDEO_INBOX = Path("video_raw")
VIDEO_DONE = Path("video_done")
AUDIO_INBOX = Path("audio_raw")
AUDIO_DONE = Path("audio_done")
FINAL_DIR = Path("final")
PROMPTS_PATH = Path("prompts/prompts_today.json")

LOOPED_AUDIO_DIR = Path("audio_looped")


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n\nOutput:\n{p.stdout}")


def list_files(folder: Path, exts: tuple[str, ...]) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts]
    files.sort(key=lambda p: p.stat().st_mtime)  # oldest first
    return files


def safe_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        i = 1
        while True:
            cand = dst_dir / f"{src.stem}_{i}{src.suffix}"
            if not cand.exists():
                dst = cand
                break
            i += 1
    shutil.move(str(src), str(dst))
    return dst


def loop_audio_to_10s(in_audio: Path, out_audio: Path, seconds: float = 10.0, xfade: float = 0.35) -> None:
    """
    Wraps ffmpeg looping into a 10s WAV (good for ASMR).
    """
    out_audio.parent.mkdir(parents=True, exist_ok=True)

    T = float(seconds)
    F = float(xfade)
    if F <= 0 or F >= T:
        raise ValueError("xfade must be > 0 and < seconds")

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "10",
        "-i", str(in_audio),
        "-filter_complex",
        (
            f"[0:a]atrim=0:{T-F},asetpts=PTS-STARTPTS[mid];"
            f"[0:a]atrim={T-F}:{T},asetpts=PTS-STARTPTS[tail];"
            f"[0:a]atrim=0:{F},asetpts=PTS-STARTPTS[head];"
            f"[tail][head]acrossfade=d={F}:c1=tri:c2=tri[xf];"
            f"[mid][xf]concat=n=2:v=0:a=1[outa]"
        ),
        "-map", "[outa]",
        "-t", f"{T}",
        "-ac", "2",
        "-ar", "48000",
        str(out_audio),
    ]
    run(cmd)


def merge_video_audio(video: Path, audio: Path, out_mp4: Path) -> None:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-i", str(audio),
        "-t", "10",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_mp4),
    ]
    run(cmd)


def load_prompts(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return data["items"]
    except Exception:
        return []
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=3, help="How many videos to process from inbox (default 3)")
    ap.add_argument("--seconds", type=float, default=10.0, help="Target duration (default 10)")
    ap.add_argument("--xfade", type=float, default=0.35, help="Audio crossfade seconds (default 0.35)")
    args = ap.parse_args()

    FINAL_DIR.mkdir(exist_ok=True)
    LOOPED_AUDIO_DIR.mkdir(exist_ok=True)

    prompts = load_prompts(PROMPTS_PATH)  # optional; only used for logging

    videos = list_files(VIDEO_INBOX, (".mp4", ".mov", ".m4v"))
    audios = list_files(AUDIO_INBOX, (".wav", ".mp3", ".m4a"))

    if not videos:
        raise SystemExit("No new videos found in video_raw/")
    if not audios:
        raise SystemExit("No new audios found in audio_raw/")

    n = min(args.count, len(videos), len(audios))
    if n <= 0:
        raise SystemExit("Nothing to process.")

    stamp = datetime.now().strftime("%Y%m%d")

    for i in range(n):
        v = videos[i]
        a = audios[i]

        idx = i + 1
        # Optional: include a short tag if prompts exist
        tag = ""
        if i < len(prompts):
            # try to keep filename safe
            theme = prompts[i].get("theme") or prompts[i].get("style") or ""
            theme = "".join(ch for ch in theme if ch.isalnum() or ch in ("-", "_"))[:20]
            if theme:
                tag = f"_{theme}"

        looped = LOOPED_AUDIO_DIR / f"audio_{stamp}_{idx:02d}_10s.wav"
        out = FINAL_DIR / f"slime_{stamp}_{idx:02d}{tag}.mp4"

        # 1) make 10s audio
        loop_audio_to_10s(a, looped, seconds=args.seconds, xfade=args.xfade)

        # 2) merge
        merge_video_audio(v, looped, out)

        # 3) archive originals (so they NEVER get reused)
        safe_move(v, VIDEO_DONE)
        safe_move(a, AUDIO_DONE)

        print(f"OK: {out}")

    print(f"Done. Created {n} final videos in {FINAL_DIR}/")


if __name__ == "__main__":
    main()
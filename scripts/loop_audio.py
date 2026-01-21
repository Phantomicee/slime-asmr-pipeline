# scripts/loop_audio.py
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n\nOutput:\n{p.stdout}")


def loop_audio_to_duration(
    in_audio: Path,
    out_audio: Path,
    target_seconds: float = 10.0,
    crossfade_seconds: float = 0.35,
) -> None:
    """
    Creates a seamless-ish loop from an arbitrary audio file by:
    - repeating it
    - trimming to target duration
    - applying a short crossfade at the end back into the start (good for ASMR textures)
    Output is WAV (safe for merging).
    """
    out_audio.parent.mkdir(parents=True, exist_ok=True)

    # Strategy:
    # 1) Create a long repeated stream using -stream_loop
    # 2) Trim to target_seconds
    # 3) Crossfade end->start using acrossfade on the same stream by splitting and delaying
    #
    # Simple and reliable approach:
    # - concat the audio with itself a few times
    # - then apply acrossfade between end and beginning by:
    #   * make two copies: A (full), B (full)
    #   * trim last fade window from A and first fade window from B
    #   * acrossfade them
    #
    # Implementation using filter_complex:
    # [0:a]atrim=0:TARGET,asetpts=PTS-STARTPTS[a];
    # [0:a]atrim=0:FADE,asetpts=PTS-STARTPTS[head];
    # [0:a]atrim=TARGET-FADE:TARGET,asetpts=PTS-STARTPTS[tail];
    # [tail][head]acrossfade=d=FADE:c1=tri:c2=tri[xf];
    # [a][xf] ??? -> We need to replace tail with xf.
    #
    # We'll do:
    # - build "mid" = atrim=0:TARGET-FADE
    # - build "xf" = acrossfade(tail, head)
    # - concat(mid, xf)

    T = float(target_seconds)
    F = float(crossfade_seconds)
    if F <= 0 or F >= T:
        raise ValueError("crossfade_seconds must be > 0 and < target_seconds")

    # Use -stream_loop to ensure enough length
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "10",  # repeat input enough times
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input audio file (wav/mp3)")
    ap.add_argument("--out", dest="out", required=True, help="Output WAV path")
    ap.add_argument("--seconds", type=float, default=10.0, help="Target duration in seconds (default 10)")
    ap.add_argument("--xfade", type=float, default=0.35, help="Crossfade seconds (default 0.35)")
    args = ap.parse_args()

    loop_audio_to_duration(Path(args.inp), Path(args.out), args.seconds, args.xfade)


if __name__ == "__main__":
    main()
from pathlib import Path

RUNS_DIR = Path("runs")

def latest_run_dir() -> Path:
    """
    Returns the newest run directory inside /runs based on folder name.
    Expected format: YYYY-MM-DD or YYYY-MM-DD_xxx
    """
    if not RUNS_DIR.exists():
        raise FileNotFoundError("runs/ folder not found")

    run_dirs = [p for p in RUNS_DIR.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError("No run folders found inside runs/")

    # Sort by name (YYYY-MM-DD works lexicographically). Newest = last.
    run_dirs.sort(key=lambda p: p.name)
    return run_dirs[-1]

def run_paths(run_dir: Path) -> dict:
    return {
        "run_dir": run_dir,
        "prompts": run_dir / "prompts.json",
        "video_raw": run_dir / "video_raw",
        "audio_raw": run_dir / "audio_raw",
        "final": run_dir / "final",
    }
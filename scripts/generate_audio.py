# scripts/generate_audio.py
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests

PROMPTS_PATH = Path("prompts/prompts_today.json")
OUT_DIR = Path("audio_raw")

# ElevenLabs endpoints verschillen per product. Deze gebruikt de "sound generation / SFX" stijl.
# Als jouw account een andere endpoint vereist, dan faalt hij met 404/400 en dan passen we hem aan.
ELEVEN_SFX_URL = "https://api.elevenlabs.io/v1/sound-generation"

def sanitize_id(n: int) -> str:
    return f"{n:02d}"

def ensure_prompts():
    if not PROMPTS_PATH.exists():
        raise SystemExit(f"Missing {PROMPTS_PATH}. Run generate_prompts_openai_v2.py first.")
    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) == 0:
        raise SystemExit("prompts_today.json is empty or not a list.")
    return data

def main():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("Missing ELEVENLABS_API_KEY in env/secrets.")

    items = ensure_prompts()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/wav",
    }

    for item in items:
        idx = int(item.get("id", 0) or 0)
        if idx <= 0:
            continue

        prompt = item.get("audio_prompt", "").strip()
        if not prompt:
            raise SystemExit(f"Item id={idx} missing audio_prompt")

        # ElevenLabs SFX generatie is doorgaans prompt + duration
        payload = {
            "text": prompt,
            "duration_seconds": 8,
        }

        out_path = OUT_DIR / f"audio_{sanitize_id(idx)}.wav"

        r = requests.post(ELEVEN_SFX_URL, headers=headers, json=payload, timeout=120)
        if r.status_code >= 400:
            raise SystemExit(
                f"ElevenLabs error for id={idx}: {r.status_code}\n{r.text}\n"
                f"Endpoint used: {ELEVEN_SFX_URL}"
            )

        out_path.write_bytes(r.content)
        print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
# scripts/generate_prompts_openai_v2.py
from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from openai import OpenAI

OUT_PATH = Path("prompts/prompts_today.json")
HISTORY_PATH = Path("prompts/history.json")

N_ITEMS = int(os.getenv("N_PROMPTS", "3"))

# =========================================================
# LIBRARIES (SAFE, PROVEN, TABLETOP-ONLY)
# =========================================================

SURFACES_LIB = [
    "horizontal polished black marble tabletop with fine white veining",
    "horizontal honed travertine stone tabletop with soft porous texture",
    "horizontal satin-finished onyx stone tabletop with subtle natural veins",
    "horizontal brushed metal tabletop with soft linear reflections",
    "horizontal smoked glass tabletop with deep glossy reflections",
    "horizontal glazed ceramic tabletop with luxury sheen",
    "horizontal dark basalt stone tabletop with matte premium texture",
    "horizontal mother-of-pearl inlay tabletop with subtle iridescence",
]

BACKGROUNDS_LIB = [
    "luxury penthouse lounge interior with dim nighttime city lights through large windows, softly blurred",
    "boutique hotel bathroom with marble surfaces and warm ambient lamp glow, softly blurred",
    "modern design kitchen with gentle reflections and bokeh highlights, softly blurred",
    "minimalist interior studio with mixed warm and cool practical lights, softly blurred",
    "calm spa interior with warm sconces and subtle steam, softly blurred",
    "high-end product studio with tasteful colored practical lights, softly blurred",
]

PALETTES_LIB = [
    "obsidian black with subtle iridescent highlights",
    "emerald green, sapphire blue, and bronze glints",
    "deep sapphire blue with warm amber gold and subtle violet",
    "jade green with pearl white and champagne gold",
    "ultramarine blue with rose gold and soft plum haze",
    "arctic teal with silver and midnight blue",
    "honey amber with espresso brown and warm copper",
]

SLIME_TYPES = [
    {
        "type": "thick glossy slime",
        "visual": (
            "very thick cohesive slime with high viscosity and heavy mass, "
            "slow stretching before settling, thick rounded folds, delayed recovery, "
            "never watery, never splashy"
        ),
        "audio": (
            "Very slow-paced slime audio. Deep, heavy, cohesive gel movement with long pauses, "
            "low event density, smooth wet glide, soft folds, long decay. "
            "No sharp transients. Duration: exactly 10 seconds."
        ),
    },
    {
        "type": "creamy slime",
        "visual": (
            "dense creamy slime with yogurt-like thickness, smooth drape, "
            "rounded soft folds, cohesive body, calm slow glide"
        ),
        "audio": (
            "Slow and gentle creamy slime audio. Smooth dense flow, "
            "moderate spacing between events, soft wet texture, gradual settling. "
            "Duration: exactly 10 seconds."
        ),
    },
    {
        "type": "pearlescent slime",
        "visual": (
            "thick pearlescent cohesive slime with subtle realistic shimmer (not glitter), "
            "smooth glossy surface, slow rounded deformation"
        ),
        "audio": (
            "Slow elegant slime audio with soft wet texture and gentle motion, "
            "low-to-moderate tempo, no harsh peaks. Duration: exactly 10 seconds."
        ),
    },
]

SCENE_PATTERNS = [
    "slowly settling onto the surface, gently spreading, then gliding in rounded folds",
    "resting fully on the surface while gradually compressing and gliding with visible weight",
    "forming thick rounded folds that slowly deform and glide across the surface",
]

# =========================================================
# HARD GLOBAL LOCKS (ANTI-FAILURE)
# =========================================================

BASE_RULES = """
GLOBAL VIDEO RULES (MANDATORY):
- 10-second concept for Pika (720p).
- Extreme macro close-up.
- Camera completely static (no zoom, no shake).
- Surface MUST be horizontal tabletop orientation (0–15° max). Never vertical, never wall.
- Slime rests fully on the surface and moves autonomously due to gravity only.
- Slime must be thick, cohesive, and slow-moving (never watery, never splashy).
- No human presence of any kind: no hands, fingers, arms, people.
- No tools, spatulas, containers, pouring devices, or interaction.
- No new objects may enter the frame at any time.
- No scene changes from start to end.
- Avoid rotation, spinning, warping, jitter, or mechanical motion.
- Background must be a REAL interior space, softly blurred (bokeh).
- Stable cinematic lighting (no flicker).
"""

AUDIO_RULES = """
GLOBAL AUDIO RULES:
- Slime-only texture. No voice, no music, no ambience.
- Tempo must be slow and match slime thickness.
- Explicitly forbid: knocking, banging, thumping, sawing, grinding, scraping, metallic sounds, clicks, switches.
- Studio-clean, high fidelity.
"""

JSON_SCHEMA = """
Return VALID JSON ONLY in this exact schema:
[
  {
    "id": 1,
    "surface": "string",
    "background": "string",
    "palette": "string",
    "slime_type": "string",
    "video_prompt": "string",
    "audio_prompt": "string"
  }
]
"""

# =========================================================
# HELPERS
# =========================================================

def sanitize_surface(text: str) -> str:
    t = text.lower()
    t = re.sub(r"\b(vertical|wall|panel|upright)\b", "horizontal", t)
    if "horizontal" not in t:
        t = "horizontal " + t
    if "tabletop" not in t:
        t += " tabletop orientation"
    return t

def load_history(max_items: int = 10) -> list[dict[str, Any]]:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))[-max_items:]
        except Exception:
            return []
    return []

def save_history(entries: list[dict[str, Any]]) -> None:
    hist = load_history(200)
    hist.extend(entries)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

# =========================================================
# BUILD BRIEFS
# =========================================================

@dataclass
class Brief:
    surface: str
    background: str
    palette: str
    slime_type: dict
    scene: str

def build_briefs(n: int) -> list[Brief]:
    return [
        Brief(
            surface=random.choice(SURFACES_LIB),
            background=random.choice(BACKGROUNDS_LIB),
            palette=random.choice(PALETTES_LIB),
            slime_type=random.choice(SLIME_TYPES),
            scene=random.choice(SCENE_PATTERNS),
        )
        for _ in range(n)
    ]

# =========================================================
# MAIN
# =========================================================

def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.55"))

    briefs = build_briefs(N_ITEMS)
    history = load_history()
    run_id = sha256(datetime.now().isoformat().encode()).hexdigest()[:8]

    system_prompt = f"""
You generate premium macro ASMR video and audio prompts.

{BASE_RULES}
{AUDIO_RULES}

CRITICAL:
- Never introduce hands, people, tools, or interaction.
- Never introduce late changes or new objects.
- Always keep the surface horizontal tabletop orientation.

RECENT GENERATIONS TO AVOID REPEATING:
{json.dumps(history, ensure_ascii=False, indent=2)}

{JSON_SCHEMA}
"""

    user_prompt = f"""
Generate exactly {N_ITEMS} items using the briefs below.
Follow them strictly and keep all motion autonomous.

{json.dumps([b.__dict__ for b in briefs], ensure_ascii=False, indent=2)}

Return JSON only.
"""

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )

    data = json.loads(resp.output_text.strip())

    for i, item in enumerate(data, start=1):
        item["id"] = i
        item["surface"] = sanitize_surface(item["surface"])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    save_history([
        {
            "run": run_id,
            "surface": d["surface"],
            "background": d["background"],
            "palette": d["palette"],
            "slime_type": d["slime_type"],
        }
        for d in data
    ])

    print(f"Wrote {OUT_PATH} | run {run_id}")

if __name__ == "__main__":
    main()
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
from typing import Any, List

from openai import OpenAI

# =========================================================
# PATHS & SETTINGS
# =========================================================

OUT_PATH = Path("prompts/prompts_today.json")
HISTORY_PATH = Path("prompts/history.json")

N_ITEMS = int(os.getenv("N_PROMPTS", "3"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.65"))

# =========================================================
# SURFACES (ALWAYS HORIZONTAL / PREMIUM)
# =========================================================

SURFACES_LIB = [
    "horizontal polished black marble tabletop with fine white veining",
    "horizontal satin-finished onyx stone tabletop with translucent layers",
    "horizontal brushed metal tabletop with soft cinematic reflections",
    "horizontal smoked glass tabletop with deep glossy reflections",
    "horizontal dark basalt stone tabletop with matte premium texture",
    "horizontal mother-of-pearl inlay tabletop with subtle iridescence",
    "horizontal glazed ceramic tabletop with luxury sheen",
]

# =========================================================
# BACKGROUNDS — INDOOR + OUTDOOR (VISUALLY INTERESTING)
# =========================================================

BACKGROUNDS_LIB = [
    # Indoor (cinematic)
    "luxury penthouse lounge with glowing city skyline at night, softly blurred",
    "high-end spa interior with warm stone walls and atmospheric steam, softly blurred",
    "modern art gallery with dramatic spotlights and deep shadows, softly blurred",
    "upscale cocktail bar with neon accent lights and glass reflections, softly blurred",
    "minimalist studio with colored practical lights and moody ambience, softly blurred",

    # Outdoor (safe, calm, cinematic)
    "rooftop terrace overlooking a glowing city at dusk, softly blurred",
    "desert stone plateau during golden sunset with warm sky gradients, softly blurred",
    "cliffside terrace overlooking the ocean at golden hour, softly blurred",
    "forest clearing with shafts of warm light filtering through trees, softly blurred",
    "rocky coastal overlook with sea haze and dramatic evening light, softly blurred",
]

# =========================================================
# COLOR PALETTES — ALWAYS COLORFUL & HOOKY
# =========================================================

PALETTES_LIB = [
    "deep emerald green blending into sapphire blue with glowing gold highlights",
    "neon magenta flowing into electric cyan with subtle violet glow",
    "lava orange and molten amber with deep crimson shadows and inner glow",
    "ultramarine blue fading into teal with silver light veins",
    "jade green, turquoise, and pearl highlights with soft internal illumination",
    "royal purple melting into hot pink with luminous accents",
    "midnight blue with bioluminescent cyan streaks and soft glow",
    "sunset gradient slime: coral, peach, and warm gold with glowing edges",
]

# =========================================================
# SLIME TYPES — VISUAL MAGIE VOOR AI
# =========================================================

SLIME_TYPES = [
    {
        "type": "thick glossy slime",
        "visual": (
            "very thick cohesive slime with rich saturated colors, smooth gradients, "
            "subtle internal glow and light traveling through the material, "
            "heavy rounded folds, glossy surface with luminous highlights"
        ),
    },
    {
        "type": "creamy slime",
        "visual": (
            "dense creamy slime with vibrant blended colors, "
            "soft internal illumination, silky rounded folds, slow deformation"
        ),
    },
    {
        "type": "pearlescent slime",
        "visual": (
            "thick pearlescent slime with colorful iridescence (never white), "
            "rainbow-like light shifts, subtle internal glow, rich saturated tones"
        ),
    },
]

SCENE_PATTERNS = [
    "resting fully on the surface while slowly folding and merging into itself",
    "gradually spreading and compressing under its own weight in rounded folds",
    "slowly deforming with continuous motion and visible internal depth",
]

# =========================================================
# HARD RULES (VIDEO + AUDIO)
# =========================================================

BASE_RULES = """
GLOBAL VIDEO RULES (MANDATORY):
- 10-second concept for Pika (720p).
- Extreme macro close-up.
- Camera completely static (no zoom, no shake).
- Surface MUST be horizontal or gently sloped tabletop (0–15° max).
- Slime is already present and in motion at frame 1.
- Slime moves autonomously due to gravity only.
- Slime must be visually striking and colorful, never neutral or plain.
- Use rich saturated colors, gradients, internal illumination, and visible depth.
- No human presence: no hands, fingers, people.
- No tools, containers, pouring devices, or interaction.
- No new objects may enter the frame.
- Background must be a REAL environment (indoor or outdoor), softly blurred.
- Stable cinematic lighting, no flicker.
"""

AUDIO_RULES = """
GLOBAL AUDIO RULES (MANDATORY):
- Continuous ASMR slime sound: heavy, cohesive, organic, and calming.
- Narrative, tactile description style with onomatopoeia.
- Avoid ALL water-like language: water, wet, liquid, flow, flowing, pour, poured,
  drip, dripping, splash, splashing, bubbles, gurgle, stream, honey, syrup.
- Avoid mechanical/hard sounds: knock, bang, click, scrape, grind, metallic.
- No voice, no music, no ambience.
- Studio-clean, close-mic, high fidelity.
"""

AUDIO_STYLE_ANCHOR = """
AUDIO STYLE EXAMPLE (FOLLOW THIS VIBE):
A slow, muted plop as thick slime makes contact with the surface — dense and rounded.
As it moves, a low, sticky schlrrrp forms, like something heavy stretching and yielding.
When it folds over itself, a soft, tacky thummm is heard, followed by a smooth glossy gluuuh
as the material compresses. The sound is continuous, calm, rounded, and unhurried.
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
    t = re.sub(r"\b(vertical|wall|upright|panel)\b", "horizontal", text, flags=re.IGNORECASE)
    if "horizontal" not in t.lower():
        t = "horizontal " + t
    if "tabletop" not in t.lower():
        t += " tabletop"
    return t

def load_history(limit: int = 12) -> List[dict[str, Any]]:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))[-limit:]
        except Exception:
            return []
    return []

def save_history(entries: List[dict[str, Any]]) -> None:
    hist = load_history(200)
    hist.extend(entries)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

# =========================================================
# BUILD UNIQUE BRIEFS
# =========================================================

@dataclass
class Brief:
    surface: str
    background: str
    palette: str
    slime: dict
    scene: str

def build_briefs(n: int) -> List[Brief]:
    surfaces = random.sample(SURFACES_LIB, n)
    backgrounds = random.sample(BACKGROUNDS_LIB, n)
    palettes = random.sample(PALETTES_LIB, n)
    slimes = random.sample(SLIME_TYPES, n)
    scenes = random.sample(SCENE_PATTERNS, n)

    return [
        Brief(
            surface=surfaces[i],
            background=backgrounds[i],
            palette=palettes[i],
            slime=slimes[i],
            scene=scenes[i],
        )
        for i in range(n)
    ]

# =========================================================
# MAIN
# =========================================================

def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)
    briefs = build_briefs(N_ITEMS)
    history = load_history()
    run_id = sha256(datetime.now().isoformat().encode()).hexdigest()[:8]

    system_prompt = f"""
You generate premium macro ASMR video and audio prompts.

{BASE_RULES}
{AUDIO_RULES}

IMPORTANT VISUAL PRIORITY:
- Slime must always be colorful, luminous, and visually striking.
- If background is dark or neutral, slime must be vibrant and glowing.
- Never generate plain white, gray, or colorless slime.

IMPORTANT AUDIO PRIORITY:
- Follow the AUDIO STYLE EXAMPLE closely.

RECENT PROMPTS (AVOID SIMILARITY):
{json.dumps(history, ensure_ascii=False, indent=2)}

{AUDIO_STYLE_ANCHOR}

{JSON_SCHEMA}
"""

    user_prompt = f"""
Generate exactly {N_ITEMS} matched items using the briefs below.
Use each brief once. Do not repeat environments within this batch.

{json.dumps([b.__dict__ for b in briefs], ensure_ascii=False, indent=2)}

Return JSON only.
"""

    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=TEMPERATURE,
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
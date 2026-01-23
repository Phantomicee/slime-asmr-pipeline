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

# =========================================================
# SURFACES — ALWAYS HORIZONTAL / SLIGHTLY SLOPED
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
    "horizontal champagne-toned brushed metal tabletop",
    "horizontal glazed porcelain tabletop with micro crackle texture",
]

# =========================================================
# BACKGROUNDS — INDOOR + OUTDOOR (REALISTIC & PREMIUM)
# =========================================================

BACKGROUNDS_LIB = [
    # Indoor
    "luxury penthouse lounge with panoramic city skyline at dusk, softly blurred",
    "high-end spa interior with warm stone walls and subtle steam, softly blurred",
    "modern design kitchen with reflective surfaces and warm ambient lighting, softly blurred",
    "minimalist product studio with subtle colored practical lights, softly blurred",
    "boutique hotel bathroom with marble textures and warm lamp glow, softly blurred",
    "upscale cocktail bar with neon accents and glass reflections, softly blurred",
    "modern art gallery interior with soft spotlights and clean walls, softly blurred",

    # Outdoor
    "luxury rooftop terrace overlooking city lights at dusk, softly blurred",
    "quiet mountain viewpoint with distant peaks under soft evening light, softly blurred",
    "desert stone plateau during calm sunset with warm sky tones, softly blurred",
    "rocky coastal overlook with gentle sea haze and warm dusk light, softly blurred",
    "forest clearing with soft morning light filtering through trees, softly blurred",
    "cliffside terrace overlooking the ocean at golden hour, softly blurred",
]

# =========================================================
# COLOR PALETTES
# =========================================================

PALETTES_LIB = [
    "obsidian black with subtle iridescent highlights",
    "emerald green, sapphire blue, and bronze glints",
    "deep sapphire blue with warm amber gold and subtle violet",
    "jade green with pearl white and champagne gold",
    "ultramarine blue with rose gold and soft plum haze",
    "arctic teal with silver and midnight blue",
    "honey amber with espresso brown and warm copper",
    "soft pastel opal tones (peach, mint, lilac) rendered realistically",
]

# =========================================================
# SLIME TYPES — VISUAL + CONTINUOUS PRESSURE-DRIVEN AUDIO
# =========================================================

SLIME_TYPES = [
    {
        "type": "thick glossy slime",
        "visual": (
            "very thick cohesive slime with high viscosity and heavy mass, "
            "slow stretching before settling, thick rounded folds, delayed recovery, "
            "never watery, never splashy"
        ),
        "audio": (
            "Continuous thick slime SFX, close-mic. Slow pressure-driven mass movement with dense, "
            "cohesive gelatinous texture. Heavy body, muted highs, low-frequency weight. "
            "Constant slow deformation and folding over itself under pressure. "
            "No liquid flow, no dripping, no pouring, no splashing, no bubbles. "
            "Studio-clean. Duration: exactly 10 seconds."
        ),
    },
    {
        "type": "creamy slime",
        "visual": (
            "dense creamy slime with yogurt-like thickness, smooth drape, "
            "rounded soft folds, cohesive body, calm slow deformation"
        ),
        "audio": (
            "Continuous creamy slime SFX, close-mic. Smooth pressure-driven deformation with "
            "soft dense body and gentle folding over itself. "
            "Even uninterrupted texture, muted highs, warm mid-low frequencies. "
            "No water-like behavior, no drips or splashes. "
            "Studio-clean. Duration: exactly 10 seconds."
        ),
    },
    {
        "type": "pearlescent slime",
        "visual": (
            "thick pearlescent cohesive slime with subtle realistic shimmer (not glitter), "
            "smooth glossy surface, slow rounded deformation"
        ),
        "audio": (
            "Continuous premium slime SFX, close-mic. Dense gelatinous mass slowly deforming, "
            "silky cohesive texture with constant pressure movement. "
            "Soft, damped, low-frequency body throughout. "
            "No liquid sounds, no dripping, no pouring, no bubbles. "
            "Studio-clean. Duration: exactly 10 seconds."
        ),
    },
]

SCENE_PATTERNS = [
    "resting fully on the surface while slowly deforming and folding over itself",
    "gradually compressing under its own weight and spreading in rounded folds",
    "forming thick rounded folds that continuously deform under gravity",
]

# =========================================================
# HARD GLOBAL LOCKS (ANTI-FAILURE)
# =========================================================

BASE_RULES = """
GLOBAL VIDEO RULES (MANDATORY):
- 10-second concept for Pika (720p).
- Extreme macro close-up.
- Camera completely static (no zoom, no shake).
- Surface MUST be horizontal or gently sloped tabletop orientation (0–15° max). Never vertical, never wall.
- Slime rests fully on the surface and moves autonomously due to gravity only.
- Slime must be thick, cohesive, and slow-moving (never watery, never splashy).
- No human presence of any kind: no hands, fingers, arms, people.
- No tools, spatulas, containers, pouring devices, or interaction.
- No new objects may enter the frame at any time.
- No scene changes from start to end.
- Avoid rotation, spinning, warping, jitter, or mechanical motion.
- Background must be a REAL environment (indoor or outdoor), softly blurred (bokeh).
- Stable cinematic lighting (no flicker).
"""

AUDIO_RULES = """
GLOBAL AUDIO RULES (MANDATORY):
- Continuous pressure-driven slime sound (mass deformation), not liquid flow.
- Thick, cohesive, gelatinous texture with low-frequency body and muted highs.
- Explicitly forbid: water, watery, liquid, flow, pour, pouring, drip, dripping, splash, splashing, bubbles, gurgle, stream.
- Explicitly forbid: knocking, banging, clicking, scraping, grinding, metallic or mechanical sounds.
- No voice, no music, no ambience.
- Studio-clean, close-mic, high fidelity.
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
    t = re.sub(r"\b(vertical|wall|panel|upright)\b", "horizontal", text, flags=re.IGNORECASE)
    if "horizontal" not in t.lower():
        t = "horizontal " + t
    if "tabletop" not in t.lower():
        t += " tabletop orientation"
    return t

def load_history(max_items: int = 12) -> List[dict[str, Any]]:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))[-max_items:]
        except Exception:
            return []
    return []

def save_history(entries: List[dict[str, Any]]) -> None:
    hist = load_history(200)
    hist.extend(entries)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

# =========================================================
# BUILD UNIQUE BRIEFS (NO DUPLICATES PER RUN)
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
# scripts/generate_prompts_openai_v2.py
from __future__ import annotations

import json
import os
import random
from datetime import datetime
from pathlib import Path

from openai import OpenAI

OUT_PATH = Path("prompts/prompts_today.json")

# ---------------------------
# Visual variation libraries
# ---------------------------

SURFACES = [
    "polished marble with liquid gold veins",
    "warm onyx stone with translucent layers",
    "handcrafted satin ceramic glaze",
    "brushed metal plate with soft reflections",
    "smoked glass slab with inner light depth",
    "polished obsidian stone with subtle warm practical lights",
    "granite with subtle mica sparkle under studio lighting",
    "glazed porcelain with micro crackle texture (kintsugi-inspired)",
    "honed travertine stone with soft porous texture",
    "dark basalt stone with matte premium texture",
    "mother-of-pearl inlay surface with subtle iridescence",
    "champagne-toned brushed metal surface",
]

BACKGROUNDS = [
    "luxury spa interior with warm sconces and subtle steam, softly blurred",
    "boutique hotel bathroom with marble and warm lamp glow, softly blurred",
    "modern design kitchen with gentle reflections and bokeh highlights, softly blurred",
    "minimalist studio with mixed warm and cool practical lights, softly blurred",
    "nighttime city lights through a window, interior softly blurred",
    "calm stone room with warm ambient lighting, softly blurred",
    "high-end product studio with tasteful colored practical lights, softly blurred",
    "greenhouse corner with soft sunlight and plants, very blurred",
]

PALETTES = [
    "deep sapphire blue with warm amber gold and subtle violet hints",
    "electric cyan with deep magenta and molten gold accents",
    "jade green with pearl white and soft champagne gold",
    "emerald green with sapphire blue and bronze glints",
    "coral red with lavender haze and champagne gold",
    "arctic teal with silver and midnight blue",
    "honey amber with espresso brown and warm copper",
    "pastel opal gradient (peach, mint, lilac) but still realistic",
    "obsidian-dark tones with subtle iridescent highlights",
    "ultramarine blue with rose gold accents",
]

SLIME_TYPES = [
    {
        "type": "thick glossy slime",
        "behavior": (
            "very cohesive, high-viscosity slime that stretches before settling, "
            "forms thick ribbons and rounded folds, slow deformation and delayed recovery, "
            "never watery, never splashy"
        ),
    },
    {
        "type": "creamy slime",
        "behavior": (
            "dense creamy slime with yogurt-like thickness, smooth slow drape, "
            "rounded soft folds, cohesive body, not liquid"
        ),
    },
    {
        "type": "pearlescent slime",
        "behavior": (
            "thick pearlescent slime with subtle realistic shimmer, heavy and cohesive, "
            "smooth glossy surface, slow rounded folds, no glitter"
        ),
    },
    {
        "type": "semi-translucent slime gel",
        "behavior": (
            "semi-translucent but still thick cohesive slime, visible depth, "
            "slow internal movement, stretches and compresses as one mass"
        ),
    },
]

SCENE_PATTERNS = [
    "slow ribbon pour that stretches, lands, compresses, and glides in soft folds",
    "thick slime mass gently falling and spreading before slowly gliding",
    "cohesive slime flowing and folding over itself in calm, hypnotic motion",
    "dense slime settling and moving slowly across the surface with visible weight",
]

# ---------------------------
# Global rules (CRITICAL)
# ---------------------------

BASE_RULES = """
GLOBAL STYLE RULES:
- Create ~10 second concepts for Pika (720p).
- Extreme macro close-up.
- Camera completely static (no zoom, no shake).
- Background must be a REAL interior space, softly blurred (bokeh), not a void or flat gradient.
- Hero surface must look premium and realistic.
- Slime must always behave as thick, cohesive slime (never watery, never splashy).
- Motion is slow, heavy, satisfying, gravity-driven.
- Stable cinematic lighting (no flicker).
- No hands, no tools, no text, no logos, no brands.
- Avoid rotation, spinning, warping, jitter, mechanical motion.
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

# ---------------------------
# Build unique briefs
# ---------------------------

def build_briefs(n: int = 3) -> list[dict]:
    surfaces = random.sample(SURFACES, n)
    backgrounds = random.sample(BACKGROUNDS, n)
    palettes = random.sample(PALETTES, n)
    slime_types = random.sample(SLIME_TYPES, n)
    scenes = random.sample(SCENE_PATTERNS, n)

    briefs = []
    for i in range(n):
        briefs.append(
            {
                "surface": surfaces[i],
                "background": backgrounds[i],
                "palette": palettes[i],
                "slime_type": slime_types[i]["type"],
                "slime_behavior": slime_types[i]["behavior"],
                "scene_pattern": scenes[i],
            }
        )
    return briefs


# ---------------------------
# Main
# ---------------------------

def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.6"))

    client = OpenAI(api_key=api_key)

    n = 3
    briefs = build_briefs(n)
    today = datetime.now().strftime("%Y-%m-%d")

    system_instructions = f"""
You generate premium macro ASMR video + audio prompt pairs.

{BASE_RULES}

IMPORTANT AUDIO RULES:
- Audio must ONLY be slime/gel texture.
- Smooth wet movement, slow folds, dense cohesive glide.
- EXPLICITLY FORBID: knocking, banging, thumping, sawing, grinding, scraping, metallic sounds, clicks, switches, tools.
- No voice, no music, no ambience.
- Studio-clean, high fidelity.
- Duration: exactly 10 seconds.

Use the briefs exactly as given.
Each item must be clearly different.

{JSON_SCHEMA}
"""

    user_input = f"""
Date: {today}

Here are the {n} briefs you MUST follow exactly:
{json.dumps(briefs, ensure_ascii=False, indent=2)}

For each item:
- Build a concise, vivid video_prompt using the surface, background, palette, slime behavior, and scene pattern.
- Build a matching audio_prompt that stays soft, organic, and slime-only.
Return JSON only.
"""

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_input},
        ],
        temperature=temperature,
    )

    text = resp.output_text.strip()
    data = json.loads(text)

    if not isinstance(data, list) or len(data) != n:
        raise ValueError("Invalid JSON output from model.")

    for i, item in enumerate(data, start=1):
        item["id"] = i

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} with {n} prompt pairs.")


if __name__ == "__main__":
    main()
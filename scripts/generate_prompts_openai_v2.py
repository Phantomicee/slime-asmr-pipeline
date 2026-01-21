# scripts/generate_prompts_openai_v2.py
from __future__ import annotations

import json
import os
import random
from datetime import datetime
from pathlib import Path

from openai import OpenAI

OUT_PATH = Path("prompts/prompts_today.json")

# Hero-surface themes (je kunt deze lijst uitbreiden; dit is stijl/setting, geen kleuren)
THEMES = [
    "polished marble with liquid gold veins",
    "warm onyx stone with translucent layers",
    "handcrafted satin ceramic glaze",
    "brushed metal plate with soft reflections",
    "smoked glass slab with inner light depth",
    "polished obsidian stone with subtle warm room practical lights",
    "granite with subtle mica sparkle under studio lighting",
    "glazed porcelain with micro crackle texture (kintsugi-inspired)",
]

# Slime material modes (verwoord in model-brief zodat het niet “rubbery” wordt)
SLIME_MATERIALS = [
    {"material": "creamy", "behavior": "smooth, silky, moderately viscous, rounded folds, calm stretch-and-settle, no rubbery snap"},
    {"material": "fluffy", "behavior": "airy, pillowy, soft compression, gentle deformation, semi-matte to soft gloss, no stiffness"},
    {"material": "glossy", "behavior": "wet-looking, glassy sheen, cohesive ribbons, slow deformation, rich specular highlights, no stiff recoil"},
]

# Palette moods (regels i.p.v. vaste combinaties)
MOODS = ["high-contrast", "harmonious", "luxury glow", "pastel"]


def hue_name_hint(deg: int) -> str:
    # Only a hint to help the model choose nice words; not a strict label.
    if deg < 20 or deg >= 340:
        return "red"
    if deg < 45:
        return "orange"
    if deg < 70:
        return "yellow"
    if deg < 160:
        return "green"
    if deg < 200:
        return "cyan"
    if deg < 255:
        return "blue"
    if deg < 290:
        return "violet"
    if deg < 340:
        return "magenta"
    return "colorful"


def make_palette(mood: str) -> dict:
    """
    Infinite palettes with constraints to stay aesthetically pleasing.
    We generate a base hue and derive related hues based on mood.
    Return a human-readable color brief the model can follow.
    """
    base_deg = random.randint(0, 359)
    base_name = hue_name_hint(base_deg)

    def wrap(d: int) -> int:
        return d % 360

    if mood == "high-contrast":
        comp = wrap(base_deg + 180)
        accent = wrap(base_deg + random.choice([150, 210, 120, 240]))
        slime = (
            f"high-contrast slime palette: vivid {base_name} + vivid {hue_name_hint(comp)} "
            f"with subtle {hue_name_hint(accent)} accents; smooth gradients and tasteful saturation"
        )
        bg = (
            "real interior room background with soft bokeh; keep background less saturated than slime "
            "to maximize contrast and hook"
        )
        surface_rule = "choose a surface that supports contrast (neutral/stone/metal/glass) and does not steal focus"

    elif mood == "harmonious":
        a1 = wrap(base_deg + 18)
        a2 = wrap(base_deg - 18)
        slime = (
            f"harmonious slime palette: analogous tones around {base_name} "
            f"({hue_name_hint(a2)}, {base_name}, {hue_name_hint(a1)}), gentle tonal gradients"
        )
        bg = (
            "real interior room background with soft bokeh; keep background in the same family but slightly darker "
            "or less saturated than slime"
        )
        surface_rule = "choose a surface that complements the palette (stone/ceramic/onyx) with subtle contrast"

    elif mood == "luxury glow":
        glow = wrap(base_deg + random.choice([160, 200, 220]))
        slime = (
            f"luxury glow slime palette: deep saturated {base_name} base with subtle internal glow and "
            f"{hue_name_hint(glow)} rim-light glow; premium jewel-toned look"
        )
        bg = (
            "real interior room background with soft bokeh; dim, cinematic depth with tasteful practical lights "
            "(not pitch black), premium vibe"
        )
        surface_rule = "choose a premium surface (onyx/obsidian/smoked glass/metal) that enhances glow and reflections"

    else:  # pastel
        t1 = wrap(base_deg + 120)
        t2 = wrap(base_deg + 240)
        slime = (
            f"pastel slime palette: pastel {base_name} with pastel {hue_name_hint(t1)} and pastel {hue_name_hint(t2)}; "
            "creamy gradients, low contrast, soft pleasing tones"
        )
        bg = (
            "real interior room background with soft bokeh; airy, warm-neutral ambience, gentle light gradients, calm vibe"
        )
        surface_rule = "choose a soft tactile surface (satin ceramic/porcelain/matte stone) that matches pastel softness"

    return {
        "mood": mood,
        "base_hue_deg": base_deg,
        "slime_color_brief": slime,
        "background_color_brief": bg,
        "surface_rule": surface_rule,
        "contrast_tip": "If background is colorful, keep slime palette cohesive; if background is neutral, slime can be more vibrant.",
    }


BASE_RULES = """
GLOBAL STYLE RULES (must stay consistent each run):
- Create 10-second concepts for Pika (720p).
- Extreme macro close-up.
- Background must be a REAL interior / room, softly blurred (bokeh), not a plain gradient-only background, not pitch black.
- Hero surface must look beautiful and premium even without slime.
- Slime must look realistic and deeply satisfying for the chosen material type.
- Stable cinematic lighting (no flicker), camera completely static (no zoom, no motion).
- Avoid words/behavior that produce stiff/rubbery slime: "rubbery", "stiff", "snappy recoil", "springy", "hard gel".
- We want premium ASMR visuals: smooth, tactile, hypnotic, realistic highlights and deformation.
"""

JSON_SCHEMA = """
Return VALID JSON ONLY in this exact schema:
[
  {
    "id": 1,
    "theme": "short label",
    "material": "creamy|fluffy|glossy",
    "palette_mood": "high-contrast|harmonious|luxury glow|pastel",
    "video_prompt": "string",
    "audio_prompt": "string"
  }
]
"""


def build_briefs(n: int = 3) -> list[dict]:
    used = set()
    briefs: list[dict] = []
    while len(briefs) < n:
        theme = random.choice(THEMES)
        mat = random.choice(SLIME_MATERIALS)
        mood = random.choice(MOODS)
        pal = make_palette(mood)

        key = (theme, mat["material"], pal["mood"], pal["base_hue_deg"])
        if key in used:
            continue
        used.add(key)

        briefs.append(
            {
                "theme": theme,
                "material": mat["material"],
                "material_behavior": mat["behavior"],
                "palette": pal,
            }
        )
    return briefs


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY (set as env var or GitHub Actions secret).")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.9"))

    client = OpenAI(api_key=api_key)

    briefs = build_briefs(n=3)
    today = datetime.now().strftime("%Y-%m-%d")

    system_instructions = f"""
You are generating prompt pairs for an automated ASMR pipeline.

{BASE_RULES}

You must produce 3 items. Each item must be clearly different (theme + material + palette intent).
Use the provided briefs exactly (theme/material behavior/palette briefs). Keep prompts concise but vivid.

Video prompt requirements:
- Extreme macro close-up.
- A beautiful hero surface (from brief).
- A real interior room background, softly blurred.
- Cinematic lighting.
- Satisfying, realistic slime motion.
- Keep the concept stable for looping (avoid strong narrative start/end).

Audio prompt requirements:
- 8 seconds SFX for ElevenLabs style generation.
- No voice, no music, no ambience.
- Must match the chosen material behavior:
  * creamy: smooth, soft folds, gentle wet movement (not rubber)
  * fluffy: airy, soft compressions, subtle texture
  * glossy: slick, wet, smooth stretch, rich tactile detail
- Clean, studio-quality.

{JSON_SCHEMA}
"""

    user_input = f"""
Date: {today}

Here are the 3 briefs you MUST follow (do not alter fields; incorporate them):
{json.dumps(briefs, ensure_ascii=False, indent=2)}

Generate the JSON now.
"""

    # Responses API call
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_input},
        ],
        temperature=temperature,
    )

    text = resp.output_text.strip()

    # Validate JSON
    data = json.loads(text)
    if not isinstance(data, list) or len(data) != 3:
        raise ValueError("Model did not return a JSON list with exactly 3 items.")

    # Minimal schema check
    for i, item in enumerate(data, start=1):
        for k in ("id", "theme", "material", "palette_mood", "video_prompt", "audio_prompt"):
            if k not in item:
                raise ValueError(f"Missing key '{k}' in item {i}.")
        if item["id"] != i:
            # normalize ids if model got it wrong
            item["id"] = i

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} with 3 matched prompt pairs.")


if __name__ == "__main__":
    main()
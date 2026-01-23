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

N_ITEMS = int(os.getenv("N_PROMPTS", "3"))  # optional override

# ---------------------------
# Libraries (keep your proven combos)
# ---------------------------

SURFACES_LIB = [
    "horizontal polished black marble tabletop with fine white veining",
    "horizontal honed travertine stone tabletop with soft porous texture",
    "horizontal brushed metal tabletop with soft linear reflections",
    "horizontal smoked glass tabletop with deep glossy reflections",
    "horizontal glazed ceramic tabletop with luxury sheen",
    "horizontal dark basalt stone tabletop with matte premium texture",
    "horizontal mother-of-pearl inlay tabletop with subtle iridescence",
    "horizontal champagne-toned brushed metal tabletop",
    "horizontal polished marble with liquid gold veins (tabletop)",
    "horizontal warm onyx stone with translucent layers (tabletop)",
    "horizontal glazed porcelain with micro crackle texture (kintsugi-inspired tabletop)",
]

BACKGROUNDS_LIB = [
    "luxury spa interior with warm sconces and subtle steam, softly blurred bokeh",
    "boutique hotel bathroom with marble and warm ambient lamp glow, softly blurred",
    "modern design kitchen with gentle reflections and bokeh highlights, softly blurred",
    "minimalist interior studio with mixed warm and cool practical lights, softly blurred",
    "nighttime city lights through a window, interior softly blurred",
    "calm stone interior room with warm ambient lighting, softly blurred",
    "high-end product studio with tasteful colored practical lights, softly blurred",
    "library corner with warm lamp glow, softly blurred",
]

PALETTES_LIB = [
    "deep sapphire blue + warm amber gold + subtle violet hints",
    "electric cyan + deep magenta + molten gold accents",
    "jade green + pearl white + champagne gold",
    "emerald green + sapphire blue + bronze glints",
    "coral red + lavender haze + champagne gold",
    "arctic teal + silver + midnight blue",
    "honey amber + espresso brown + warm copper",
    "pastel opal gradient (peach + mint + lilac) but still realistic and premium",
    "obsidian black + subtle iridescent highlights + deep color depth",
    "ultramarine blue + rose gold + soft plum haze",
]

SLIME_TYPES = [
    {
        "type": "thick glossy slime",
        "visual": (
            "very thick cohesive slime with high viscosity, heavy mass, slow stretching before settling, "
            "thick rounded folds, delayed recovery, never watery or splashy"
        ),
        "audio_style": (
            "Very slow-paced, heavy, cohesive slime texture. Low event density, long pauses, smooth wet glide, "
            "soft folds and gradual settling. No sharp transients."
        ),
    },
    {
        "type": "creamy slime",
        "visual": (
            "dense creamy slime with yogurt-like thickness, smooth drape, rounded soft folds, cohesive body, calm slow glide"
        ),
        "audio_style": (
            "Slow and gentle creamy slime texture. Moderate event spacing, smooth folding, soft wet movement, "
            "gradual settling, never busy."
        ),
    },
    {
        "type": "pearlescent slime",
        "visual": (
            "thick pearlescent cohesive slime with subtle realistic shimmer (not glitter), smooth glossy surface, slow rounded deformation"
        ),
        "audio_style": (
            "Slow elegant slime texture with soft wet detail. Low-to-moderate tempo, smooth continuous movement, no harsh peaks."
        ),
    },
]

SCENE_PATTERNS = [
    "a thick cohesive slime ribbon slowly falling from above, stretching, landing, gently compressing, then gliding in soft folds",
    "a dense slime mass settling onto the surface, spreading slowly, then gliding with visible weight and rounded edges",
    "slime flowing and folding over itself in calm, hypnotic motion across the surface",
    "a slow pour that forms elegant ribbons, then transitions into a smooth glide with rounded folds and gentle deformation",
]

# ---------------------------
# Global locks
# ---------------------------

BASE_RULES = """
GLOBAL VIDEO RULES:
- 10-second concept for Pika (720p).
- Extreme macro close-up.
- Camera completely static (no zoom, no shake).
- Surface MUST be horizontal or gently sloped tabletop orientation (<=15 degrees). Never vertical, never wall.
- Slime must be thick and cohesive (slime-like), never watery, never splashy, no thin drips.
- Motion: gravity-driven stretch -> gentle compress -> slow glide -> rounded folds.
- Background is a REAL interior/room, softly blurred (bokeh). Not a void, not a flat gradient-only background.
- Stable cinematic lighting (no flicker). Premium realistic reflections.
- No hands, no tools, no text, no logos, no brands.
- Avoid: rotation/spinning, warping, jitter, mechanical motion, hard impacts.
"""

AUDIO_LOCKS = """
GLOBAL AUDIO RULES:
- 10 seconds SFX.
- Slime-only texture. No voice, no music, no ambience.
- Explicitly forbid: knocking, banging, thumping, sawing, grinding, scraping, metallic sounds, clicks, switches, tools.
- Tempo MUST be slow; never busy/fast.
"""

JSON_SCHEMA = """
Return VALID JSON ONLY in this exact schema:
[
  {
    "id": 1,
    "mode": "library|invent",
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
# History helpers (cross-run diversity)
# ---------------------------

def load_history(max_items: int = 12) -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        hist = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(hist, list):
            return hist[-max_items:]
    except Exception:
        return []
    return []

def save_history(entry: dict[str, Any]) -> None:
    hist = load_history(max_items=200)
    hist.append(entry)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

def history_brief(hist: list[dict[str, Any]]) -> str:
    if not hist:
        return "No prior generations stored."
    # Keep it concise
    lines = []
    for h in hist[-8:]:
        lines.append(
            f"- palette: {h.get('palette')} | surface: {h.get('surface')} | background: {h.get('background')} | slime: {h.get('slime_type')}"
        )
    return "\n".join(lines)

def sanitize_orientation(text: str) -> str:
    # Force "horizontal tabletop" language if model invents ambiguous surfaces
    t = text.strip()
    if "horizontal" not in t.lower():
        t = "horizontal " + t
    if "tabletop" not in t.lower():
        t = t + " (tabletop orientation)"
    # Block obvious vertical terms if they appear
    t = re.sub(r"\b(vertical|wall|panel|upright)\b", "horizontal", t, flags=re.IGNORECASE)
    return t

def validate_fields(surface: str, background: str, palette: str) -> None:
    bad_words = ["vertical", "wall", "upright", "panel"]
    for bw in bad_words:
        if bw in surface.lower() or bw in background.lower():
            raise ValueError(f"Invalid orientation in generated fields: found '{bw}'")

# ---------------------------
# Build briefs with 80/20 invention
# ---------------------------

@dataclass
class Brief:
    mode: str
    surface: str
    background: str
    palette: str
    slime_type: str
    slime_visual: str
    slime_audio_style: str
    scene_pattern: str

def build_briefs(n: int, invent_ratio: float = 0.25) -> list[Brief]:
    # Ensure uniqueness within run
    surfaces = random.sample(SURFACES_LIB, k=min(n, len(SURFACES_LIB)))
    backgrounds = random.sample(BACKGROUNDS_LIB, k=min(n, len(BACKGROUNDS_LIB)))
    palettes = random.sample(PALETTES_LIB, k=min(n, len(PALETTES_LIB)))
    slimes = random.sample(SLIME_TYPES, k=min(n, len(SLIME_TYPES)))
    scenes = random.sample(SCENE_PATTERNS, k=min(n, len(SCENE_PATTERNS)))

    briefs: list[Brief] = []
    for i in range(n):
        mode = "invent" if random.random() < invent_ratio else "library"

        s = surfaces[i % len(surfaces)]
        b = backgrounds[i % len(backgrounds)]
        p = palettes[i % len(palettes)]
        st = slimes[i % len(slimes)]
        sc = scenes[i % len(scenes)]

        briefs.append(
            Brief(
                mode=mode,
                surface=s,
                background=b,
                palette=p,
                slime_type=st["type"],
                slime_visual=st["visual"],
                slime_audio_style=st["audio_style"],
                scene_pattern=sc,
            )
        )
    return briefs

# ---------------------------
# Main
# ---------------------------

def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.55"))

    client = OpenAI(api_key=api_key)

    n = N_ITEMS
    briefs = build_briefs(n=n, invent_ratio=0.25)
    today = datetime.now().strftime("%Y-%m-%d")
    run_signature = sha256((datetime.now().isoformat() + str(random.random())).encode()).hexdigest()[:8]

    hist = load_history(max_items=12)

    system_instructions = f"""
You generate premium macro ASMR video + audio prompt pairs.

{BASE_RULES}

{AUDIO_LOCKS}

CROSS-RUN DIVERSITY (CRITICAL):
- The new generation must feel clearly different from recent generations.
- Avoid repeating similar palette families, backgrounds, and surface families seen recently.
- Change the overall vibe/setting in noticeable ways while staying realistic and premium.

RECENT GENERATIONS TO AVOID (do not reuse closely):
{history_brief(hist)}

INVENTION RULE (IMPORTANT):
Some items have mode="invent". For those, you MUST invent NEW:
- palette (new color combination)
- surface (new premium tabletop surface)
- background (new real interior environment)
They must still follow all rules and remain realistic/premium.
Do not invent brands. Do not invent sci-fi voids.
Always keep surface horizontal tabletop orientation.

OUTPUT: return JSON only.
Run signature: {run_signature}

{JSON_SCHEMA}
"""

    # Provide libraries to guide inventions (so inventions stay within "good taste")
    libraries_hint = {
        "surfaces_library_examples": SURFACES_LIB[:8],
        "backgrounds_library_examples": BACKGROUNDS_LIB[:8],
        "palettes_library_examples": PALETTES_LIB[:8],
        "slime_types": [s["type"] for s in SLIME_TYPES],
    }

    user_input = f"""
Date: {today}
Generate exactly {n} items.

Here are the briefs you MUST follow.
- If mode is "library": use the brief's surface/background/palette exactly.
- If mode is "invent": replace surface/background/palette with newly invented ones that fit the same premium style.
- Always keep surface explicitly horizontal tabletop orientation.

Briefs:
{json.dumps([b.__dict__ for b in briefs], ensure_ascii=False, indent=2)}

Helpful examples (not mandatory, just guidance for good taste):
{json.dumps(libraries_hint, ensure_ascii=False, indent=2)}

Write the JSON now.
"""

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_input},
        ],
        temperature=temperature,
    )

    data = json.loads(resp.output_text.strip())

    if not isinstance(data, list) or len(data) != n:
        raise ValueError(f"Model did not return a JSON list with exactly {n} items.")

    # Normalize + sanitize + validate + save history
    for i, item in enumerate(data, start=1):
        item["id"] = i
        # Ensure orientation lock even for invented items
        item["surface"] = sanitize_orientation(str(item.get("surface", "")))
        validate_fields(item["surface"], str(item.get("background", "")), str(item.get("palette", "")))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save a short history entry (for cross-run diversity)
    for it in data:
        save_history({
            "ts": datetime.now().isoformat(),
            "run": run_signature,
            "palette": it.get("palette"),
            "surface": it.get("surface"),
            "background": it.get("background"),
            "slime_type": it.get("slime_type"),
            "mode": it.get("mode"),
        })

    print(f"Wrote {OUT_PATH} with {n} prompt pairs (run {run_signature}). Saved history for diversity.")


if __name__ == "__main__":
    main()
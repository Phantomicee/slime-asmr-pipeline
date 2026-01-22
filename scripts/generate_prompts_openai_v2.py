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
# KEEP + EXPAND: surfaces
# (behoud je bestaande combinaties + uitbreiden)
# ---------------------------
SURFACES = [
    # (oude THEMES behouden)
    "polished marble with liquid gold veins",
    "warm onyx stone with translucent layers",
    "handcrafted satin ceramic glaze",
    "brushed metal plate with soft reflections",
    "smoked glass slab with inner light depth",
    "polished obsidian stone with subtle warm room practical lights",
    "granite with subtle mica sparkle under studio lighting",
    "glazed porcelain with micro crackle texture (kintsugi-inspired)",

    # extra variatie
    "polished black marble with fine white veining",
    "honed travertine stone with soft porous texture",
    "frosted glass plate with gentle edge highlights",
    "brushed titanium plate with soft linear reflections",
    "glazed ceramic tile with luxury sheen",
    "dark basalt stone with matte premium texture",
    "mother-of-pearl inlay surface with subtle iridescence",
    "champagne-toned brushed metal surface",
    "translucent acrylic block surface with deep edge glow (subtle, realistic)",
    "wet river stone slab with smooth dark reflections",
]


# ---------------------------
# Backgrounds: real places (blurred)
# ---------------------------
BACKGROUNDS = [
    "luxury spa interior with warm sconces and subtle steam, softly blurred bokeh",
    "boutique hotel bathroom with marble and warm lamp glow, softly blurred",
    "modern design kitchen with gentle reflections and bokeh highlights, softly blurred",
    "minimalist studio with mixed warm/cool practical lights and soft bokeh, softly blurred",
    "nighttime city lights through a window (bokeh), interior softly blurred",
    "calm stone room with warm ambient lighting and gentle depth, softly blurred",
    "high-end product studio with tasteful colored practical lights (bokeh), softly blurred",
    "greenhouse corner with soft sunlight and plants, very blurred background",
    "library corner with warm lamp glow and wooden texture, softly blurred",
    "modern lounge at dusk with soft practical lights, softly blurred",
]


# ---------------------------
# Palettes: keep mood system + add explicit combos
# (we keep your "moods" concept but ALSO add explicit high-CTR palettes)
# ---------------------------
PALETTES_EXPLICIT = [
    # keep some of your earlier successful combos
    "deep sapphire blue + warm amber gold + subtle violet hints",
    "electric cyan + deep magenta + molten gold accents",
    "jade green + pearl white + soft champagne gold",
    "emerald green + sapphire blue + bronze glints",
    "coral red + lavender haze + champagne gold",
    "arctic teal + silver + midnight blue",
    "honey amber + espresso brown + warm copper",
    "pastel opal gradient (peach + mint + lilac) but still realistic and premium",
    "obsidian-dark with subtle iridescent highlights and deep color depth",

    # more combos (new)
    "ultramarine blue + rose gold + soft violet haze",
    "deep teal + neon-lime accents + dark purple shadows (premium, not cartoony)",
    "ruby red + smoked plum + warm gold highlights",
    "seafoam teal + pearl + soft coral accents",
    "sunset amber + deep navy + subtle crimson edge tones",
    "emerald + champagne gold + soft indigo undertones",
    "icy cyan + lilac + silver highlights",
]


# Optional mood labels (still useful), but we won’t rely on them alone
MOODS = ["high-contrast", "harmonious", "luxury glow", "pastel"]


def hue_name_hint(deg: int) -> str:
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


def make_palette_brief(mood: str) -> str:
    """
    Keep your infinite palette generator idea, but output a SHORT human-usable brief.
    """
    base_deg = random.randint(0, 359)
    base_name = hue_name_hint(base_deg)

    def wrap(d: int) -> int:
        return d % 360

    if mood == "high-contrast":
        comp = wrap(base_deg + 180)
        accent = wrap(base_deg + random.choice([150, 210, 120, 240]))
        return (
            f"high-contrast palette: vivid {base_name} + vivid {hue_name_hint(comp)} "
            f"with subtle {hue_name_hint(accent)} accents; smooth gradients, premium saturation"
        )
    if mood == "harmonious":
        a1 = wrap(base_deg + 18)
        a2 = wrap(base_deg - 18)
        return (
            f"harmonious palette: analogous tones around {base_name} "
            f"({hue_name_hint(a2)}, {base_name}, {hue_name_hint(a1)}), gentle tonal gradients"
        )
    if mood == "luxury glow":
        glow = wrap(base_deg + random.choice([160, 200, 220]))
        return (
            f"luxury glow palette: deep jewel-toned {base_name} base with subtle internal glow and "
            f"{hue_name_hint(glow)} rim-light accents; premium reflections"
        )
    # pastel
    t1 = wrap(base_deg + 120)
    t2 = wrap(base_deg + 240)
    return (
        f"pastel palette: pastel {base_name} with pastel {hue_name_hint(t1)} and pastel {hue_name_hint(t2)}; "
        "creamy gradients, soft pleasing tones"
    )


# ---------------------------
# Slime types: force "slime-like" thickness (never watery)
# ---------------------------
SLIME_TYPES = [
    {
        "slime_type": "thick glossy slime",
        "behavior": (
            "very cohesive high-viscosity slime, heavy ribbons, rounded folds, slow deformation, "
            "delayed recovery, no thin edges, no splashing, never watery"
        ),
    },
    {
        "slime_type": "creamy slime",
        "behavior": (
            "dense creamy slime, yogurt-like thickness, smooth slow drape, rounded soft folds, "
            "cohesive mass, slow elastic recovery, not liquid"
        ),
    },
    {
        "slime_type": "pearlescent slime",
        "behavior": (
            "thick pearlescent slime with subtle realistic shimmer (not glitter), heavy and cohesive, "
            "smooth glossy surface, slow deformation and rounded folds, never watery"
        ),
    },
    {
        "slime_type": "semi-translucent slime gel",
        "behavior": (
            "semi-translucent but still thick cohesive slime with visible depth, slow internal movement, "
            "stretches and compresses as one mass, never watery"
        ),
    },
    {
        "slime_type": "fluffy glossy slime",
        "behavior": (
            "soft pillowy slime with cohesive body, gentle compression and rounded folds, "
            "semi-matte to soft gloss, no stiffness, not airy foam, never watery"
        ),
    },
]


# ---------------------------
# "Event hooks" (optional): add interest without breaking realism
# ---------------------------
HOOK_EVENTS = [
    {
        "name": "slow ribbon pour",
        "desc": "a thick cohesive ribbon of slime pours slowly from above, stretches, lands, compresses, then glides",
    },
    {
        "name": "heavy droplet impacts",
        "desc": "large gel-like droplets fall at a calm rhythm, each impact compresses the slime and creates slow waves",
    },
    {
        "name": "single strong contact then calm glide",
        "desc": "a controlled initial contact (strong but not splashy) followed by slow satisfying glide and folds",
    },
    {
        "name": "fold-and-settle cycle",
        "desc": "slime folds over itself in slow rounded waves, then settles, repeating in calm hypnotic motion",
    },
]


BASE_RULES = """
GLOBAL STYLE RULES (must stay consistent):
- Create 10-second concepts for Pika (720p).
- Extreme macro close-up.
- Background must be a REAL interior / room, softly blurred (bokeh), not a plain gradient-only background, not pitch black.
- Hero surface must look beautiful and premium even without slime.
- Slime texture must be cohesive and thick (slime-like), never watery, never splashy, no thin edges.
- Stable cinematic lighting (no flicker), camera completely static (no zoom, no motion).
- No hands, no tools, no text, no logos, no brands.
- Avoid AI artifact triggers: rotation/spinning, warping, jitter, melting edges, chaotic splash.
- Motion should be slow, heavy, satisfying, physically believable (gravity-driven stretch → compress → glide → soft folds).
"""

JSON_SCHEMA = """
Return VALID JSON ONLY in this exact schema:
[
  {
    "id": 1,
    "surface": "string",
    "background": "string",
    "palette": "string",
    "palette_mode": "explicit|mood",
    "mood": "high-contrast|harmonious|luxury glow|pastel",
    "slime_type": "string",
    "hook_event": "string",
    "video_prompt": "string",
    "audio_prompt": "string"
  }
]
"""


def build_briefs(n: int = 3) -> list[dict]:
    """
    Force uniqueness across the batch:
    - different surface
    - different background
    - different palette (explicit or mood-based)
    - different slime_type
    - different hook_event
    """
    surfaces = random.sample(SURFACES, k=n) if len(SURFACES) >= n else [random.choice(SURFACES) for _ in range(n)]
    backgrounds = random.sample(BACKGROUNDS, k=n) if len(BACKGROUNDS) >= n else [random.choice(BACKGROUNDS) for _ in range(n)]
    slime_types = random.sample(SLIME_TYPES, k=n) if len(SLIME_TYPES) >= n else [random.choice(SLIME_TYPES) for _ in range(n)]
    events = random.sample(HOOK_EVENTS, k=n) if len(HOOK_EVENTS) >= n else [random.choice(HOOK_EVENTS) for _ in range(n)]

    briefs: list[dict] = []
    used_palettes: set[str] = set()

    for i in range(n):
        # Mix explicit palettes with mood-generated palettes
        use_explicit = (random.random() < 0.75)  # 75% explicit (more consistent CTR), 25% mood (infinite)
        if use_explicit:
            # ensure no repeats
            choices = [p for p in PALETTES_EXPLICIT if p not in used_palettes] or PALETTES_EXPLICIT
            palette = random.choice(choices)
            used_palettes.add(palette)
            palette_mode = "explicit"
            mood = random.choice(MOODS)
        else:
            mood = random.choice(MOODS)
            palette = make_palette_brief(mood)
            palette_mode = "mood"

        briefs.append(
            {
                "surface": surfaces[i],
                "background": backgrounds[i],
                "palette": palette,
                "palette_mode": palette_mode,
                "mood": mood,
                "slime_type": slime_types[i]["slime_type"],
                "slime_behavior": slime_types[i]["behavior"],
                "hook_event": events[i]["name"],
                "hook_desc": events[i]["desc"],
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

    n = 3
    briefs = build_briefs(n=n)
    today = datetime.now().strftime("%Y-%m-%d")

    system_instructions = f"""
You are generating premium macro ASMR prompt pairs for an automated pipeline.

{BASE_RULES}

You must produce exactly {n} items. Each item must be clearly different:
- different surface
- different background
- different palette
- different slime_type
- different hook_event

Use the provided briefs EXACTLY (do not alter the surface/background/palette/slime type/event).
Keep prompts concise but vivid.

Video prompt requirements:
- Must explicitly describe the slime behaving as cohesive thick slime (never watery).
- Must include the given surface and background.
- Must follow the hook event description (cause → satisfying motion).
- No camera motion, no hands/tools, no text/logos.

Audio prompt requirements:
- Duration: exactly 10 seconds.
- No voice, no music, no ambience/noise.
- Must match the hook rhythm: brief gentle impact early (if relevant), then continuous smooth slime glide/fold texture.
- Avoid rubber squeaks, cartoon squish, sharp clicks.
- Studio-clean, high fidelity.

{JSON_SCHEMA}
"""

    user_input = f"""
Date: {today}

Here are the {n} briefs you MUST follow (do not change their fields):
{json.dumps(briefs, ensure_ascii=False, indent=2)}

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

    text = resp.output_text.strip()

    data = json.loads(text)
    if not isinstance(data, list) or len(data) != n:
        raise ValueError(f"Model did not return a JSON list with exactly {n} items.")

    # Minimal schema check + normalize ids
    for i, item in enumerate(data, start=1):
        for k in ("id", "surface", "background", "palette", "palette_mode", "mood", "slime_type", "hook_event", "video_prompt", "audio_prompt"):
            if k not in item:
                raise ValueError(f"Missing key '{k}' in item {i}.")
        item["id"] = i

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} with {n} matched prompt pairs.")


if __name__ == "__main__":
    main()
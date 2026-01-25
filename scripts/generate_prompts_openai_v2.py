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
    "horizontal glazed porcelain tabletop with subtle crackle texture",
]

# =========================================================
# BACKGROUNDS — INDOOR + OUTDOOR (WITH MOUNTAIN VARIANTS)
# =========================================================

BACKGROUNDS_LIB = [
    # ===== INDOOR =====
    "luxury penthouse lounge at night with glowing city lights and deep contrast, softly blurred",
    "high-end spa interior with warm stone walls and drifting steam, softly blurred",
    "modern art gallery with dramatic spotlights and deep shadows, softly blurred",
    "upscale cocktail bar with neon accents and glass reflections, softly blurred",
    "minimalist studio with colored practical lights and moody ambience, softly blurred",
    "boutique hotel suite with warm lamp glow and textured fabrics, softly blurred",

    # ===== OUTDOOR – MOUNTAIN VARIANTS =====
    "snowy mountain plateau at blue hour with cold sky gradients and distant peaks, softly blurred",
    "rocky mountain overlook at warm sunset with orange-pink sky glow, softly blurred",
    "misty mountain ridge at early dawn with soft fog and muted colors, softly blurred",
    "high-altitude mountain terrace at night under a star-filled sky, softly blurred",

    # ===== OUTDOOR – COAST / DESERT / FOREST =====
    "cliffside terrace overlooking the ocean at golden hour, softly blurred",
    "rocky coastal overlook during moody overcast dusk, softly blurred",
    "desert stone plateau during fiery sunset with dramatic sky gradients, softly blurred",
    "quiet forest clearing at sunrise with warm light shafts, softly blurred",
    "forest overlook during autumn twilight with deep amber tones, softly blurred",
]

# =========================================================
# COLOR PALETTES — ALWAYS COLORFUL & HOOKY
# =========================================================

PALETTES_LIB = [
    "deep emerald green blending into sapphire blue with glowing gold highlights",
    "neon magenta blending into electric cyan with subtle violet glow",
    "lava orange and molten amber with deep crimson shadows and inner glow",
    "ultramarine blue fading into teal with silver light veins",
    "jade green, turquoise, and pearl highlights with soft internal illumination",
    "royal purple melting into hot pink with luminous accents",
    "midnight blue with bioluminescent cyan streaks and soft glow",
    "sunset gradient slime: coral, peach, and warm gold with glowing edges",
    "electric blue with neon lime accents and faint internal glow",
]

# =========================================================
# SLIME TYPES — VISUAL MAGIE + CONTINUOUS ARRIVAL FROM ABOVE
# =========================================================

SLIME_TYPES = [
    {
        "type": "thick glossy slime",
        "visual": (
            "very thick cohesive slime with rich saturated colors and smooth gradients, "
            "subtle internal illumination, heavy rounded folds, glossy surface with luminous highlights"
        ),
    },
    {
        "type": "creamy slime",
        "visual": (
            "dense creamy slime with vibrant blended colors, soft internal glow, "
            "silky rounded folds, slow deformation, visually rich and smooth"
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
    "new slime continuously arrives from just above the frame and folds over the existing slime in rounded layers",
    "a steady uninterrupted ribbon of slime enters from above, merging smoothly and folding over itself on the tabletop",
    "incoming slime from above continuously drapes and folds onto the existing mass, maintaining calm hypnotic motion",
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
- Slime is already present on the surface AND new slime is continuously arriving from just above the frame.
- Incoming slime folds over existing slime in slow, rounded layers with no visible start or end.
- Slime moves autonomously due to gravity only.
- Slime must be visually striking and colorful, never neutral or plain.
- Use rich saturated colors, gradients, subtle internal illumination, and visible depth.
- No human presence: no hands, fingers, people.
- No tools, containers, pouring devices, or interaction.
- No new objects may enter the frame.
- Background must be a REAL environment (indoor or outdoor), softly blurred (bokeh).
- Stable cinematic lighting, no flicker.
- Avoid rotation/spinning, jitter, warping, or mechanical motion.
"""

# ✅ Centering rule (short, strong, Pika-friendly)
COMPOSITION_RULE = (
    "Composition: perfectly centered macro framing; slime mound and folds stay in the exact center "
    "with wide empty margins on all sides; no drift to edges or corners; no off-center framing."
)

AUDIO_RULES = """
GLOBAL AUDIO RULES (MANDATORY):
- Keep audio prompts SIMPLE and property-based (material tags), not narrative.
- 2–3 short lines max.
- Thick, cohesive slime texture with soft rounded folds and calm, slow settling.
- Slightly moist texture is allowed (slime can sound a bit moist), but NEVER watery or liquid-like.
- Avoid ALL water-like / liquid-motion words: water, watery, liquid, flow, flowing, pour, pouring, poured,
  drip, dripping, stream, splash, splashing, slosh, gurgle, bubbles, honey, syrup.
- Avoid mechanical/hard sounds: knock, bang, thump, click, scrape, grind, metallic, squeak.
- No voice, no music, no ambience. Studio-quality close-mic recording.
- Duration: 8 seconds.
"""

AUDIO_STYLE_ANCHOR = """
AUDIO TEMPLATE STYLE (FOLLOW THIS FORMAT):
Silky, smooth, thick slime ASMR sounds with soft rounded folds and slow, calm settling.
Slightly moist, cohesive texture with gentle compression and smooth release.
Studio-quality close-mic recording, no voice, no music, no ambience. Duration: 8 seconds.
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

def ensure_composition_line(video_prompt: str) -> str:
    vp = (video_prompt or "").strip()
    # Always append the composition rule once (keep it short and consistent)
    if "composition:" not in vp.lower():
        vp = vp.rstrip(".") + ". " + COMPOSITION_RULE
    return vp

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
    briefs = build_briefs(N_ITEMS)
    history = load_history()
    run_id = sha256(datetime.now().isoformat().encode()).hexdigest()[:8]

    system_prompt = f"""
You generate premium macro ASMR video and audio prompts.

{BASE_RULES}

CENTERING / COMPOSITION (MANDATORY):
- Always keep the main slime mass centered, with wide safe margins from frame edges.
- Never place slime near edges/corners; no off-center framing; no drift.
- Include this exact line in every video_prompt (verbatim):
{COMPOSITION_RULE}

{AUDIO_RULES}

COLOR CONTRAST RULE:
- If the background is cold or dark (snow, night, blue hour), the slime must use warm or neon colors.
- If the background is warm (sunset, desert), the slime must include cool or contrasting tones.
- Never generate plain white, gray, or colorless slime.

AUDIO PRIORITY (VERY IMPORTANT):
- Audio prompts must follow the AUDIO TEMPLATE STYLE.
- Keep audio prompt short, property-based, and cohesive (not narrative).
- Allow "slightly moist" but never watery or liquid-like.

RECENT PROMPTS (AVOID SIMILARITY):
{json.dumps(history, ensure_ascii=False, indent=2)}

{AUDIO_STYLE_ANCHOR}

{JSON_SCHEMA}
"""

    user_prompt = f"""
Generate exactly {N_ITEMS} matched items using the briefs below.
Use each brief once. Do not repeat environments within this batch.
Keep prompts concise but vivid.

CRITICAL VIDEO INSTRUCTIONS:
- The slime must be centered in frame (not near edges/corners) and remain centered.
- No off-center framing and no lateral drift.
- Include the composition line.

CRITICAL AUDIO INSTRUCTIONS:
- Write audio_prompt in the same short style as the template.
- 2–3 short lines max.
- Include: thick/cohesive, soft rounded folds, slow calm settling, slightly moist.
- Include: "Studio-quality close-mic recording, no voice, no music, no ambience. Duration: 8 seconds."
- Do NOT use: water/watery/liquid/flow/pour/drip/splash/stream/bubbles/honey/syrup or any mechanical sound words.

Briefs:
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

    text = resp.output_text.strip()
    data = json.loads(text)

    if not isinstance(data, list) or len(data) != N_ITEMS:
        raise ValueError(f"Model did not return a JSON list with exactly {N_ITEMS} items.")

    for i, item in enumerate(data, start=1):
        item["id"] = i
        item["surface"] = sanitize_surface(item.get("surface", "horizontal tabletop"))

        # Force composition line appended (prevents off-center failures)
        item["video_prompt"] = ensure_composition_line(str(item.get("video_prompt", "")))

        # Basic safety: ensure no forbidden terms in video prompt
        vp = str(item.get("video_prompt", "")).lower()
        forbidden_video = [
    "hand", "hands", "finger", "fingers",
    "tool", "tools", "spatula", "knife", "bowl", "spoon",
    "vertical", "wall", "upright", "panel"
]
        if any(x in vp for x in forbidden_video):
            raise ValueError("Generated video_prompt contains forbidden content (hands/tools/wall/edge/corner/off-center).")

        # Audio safety: reject if it contains forbidden watery words
        ap = str(item.get("audio_prompt", "")).lower()
        forbidden_audio = [
            "water", "watery", "liquid", "flow", "pour", "drip", "splash", "stream", "bubbles", "honey", "syrup",
            "knock", "bang", "thump", "click", "scrape", "grind", "metallic", "squeak"
        ]
        if any(w in ap for w in forbidden_audio):
            raise ValueError("Generated audio_prompt contains forbidden watery/mechanical words.")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    save_history([
        {
            "run": run_id,
            "surface": d.get("surface"),
            "background": d.get("background"),
            "palette": d.get("palette"),
            "slime_type": d.get("slime_type"),
        }
        for d in data
    ])

    print(f"Wrote {OUT_PATH} | run {run_id}")

if __name__ == "__main__":
    main()
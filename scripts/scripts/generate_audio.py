import os, json, sys
import requests

PROMPTS_PATH = "prompts/prompts_today.json"
AUDIO_DIR = "audio_raw"
VIDEO_DIR = "video_raw"

# NOTE: This endpoint may differ for your ElevenLabs account for Sound Effects.
ELEVEN_SFX_URL = "https://api.elevenlabs.io/v1/sound-generation"

def list_mp4s():
    files = [f for f in os.listdir(VIDEO_DIR) if f.lower().endswith(".mp4")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(VIDEO_DIR, f)))
    return files

def main():
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print("Missing ELEVENLABS_API_KEY env var.")
        sys.exit(1)

    os.makedirs(AUDIO_DIR, exist_ok=True)

    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    shorts = data.get("shorts", [])
    if len(shorts) < 1:
        print("No shorts found in prompts_today.json")
        sys.exit(1)

    mp4s = list_mp4s()
    if len(mp4s) < len(shorts):
        print(f"Not enough mp4 files in {VIDEO_DIR}. Found {len(mp4s)} but need {len(shorts)}.")
        sys.exit(1)

    # Map by upload order (oldest->slime_01, newest->slime_02, etc.)
    mapping = []
    for i, item in enumerate(shorts):
        mapping.append((item["id"], mp4s[i], item["audio_prompt"]))

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    for sid, mp4_name, audio_prompt in mapping:
        out_wav = os.path.join(AUDIO_DIR, f"{sid}.wav")

        payload = {
            "text": audio_prompt,
            "duration_seconds": 5
        }

        r = requests.post(ELEVEN_SFX_URL, headers=headers, json=payload, timeout=180)
        print(f"{sid}: status={r.status_code} content-type={r.headers.get('content-type')}")

        if r.status_code != 200:
            print("Error body:", r.text[:500])
            sys.exit(1)

        # Assume raw audio bytes
        with open(out_wav, "wb") as f:
            f.write(r.content)

        print("Saved", out_wav)

if __name__ == "__main__":
    main()

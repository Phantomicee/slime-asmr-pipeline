import os, json, subprocess, sys

PROMPTS_PATH = "prompts/prompts_today.json"
VIDEO_DIR = "video_raw"
AUDIO_DIR = "audio_raw"
FINAL_DIR = "final"

def list_mp4s():
    files = [f for f in os.listdir(VIDEO_DIR) if f.lower().endswith(".mp4")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(VIDEO_DIR, f)))
    return files

def run(cmd):
    print(" ".join(cmd))
    subprocess.check_call(cmd)

def main():
    os.makedirs(FINAL_DIR, exist_ok=True)

    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    shorts = data
    if len(shorts) < 1:
        print("No shorts in prompts file.")
        sys.exit(1)

    mp4s = list_mp4s()
    if len(mp4s) < len(shorts):
        print("Not enough mp4 files in video_raw.")
        sys.exit(1)

    for i, item in enumerate(shorts):
        sid = item["id"]
        video_path = os.path.join(VIDEO_DIR, mp4s[i])
        audio_path = os.path.join(AUDIO_DIR, f"{sid}.wav")
        out_path = os.path.join(FINAL_DIR, f"{sid}_final_10s.mp4")

        if not os.path.exists(audio_path):
            print("Missing audio:", audio_path)
            sys.exit(1)

        run([
            "ffmpeg", "-y",
            "-stream_loop", "1", "-i", video_path,
            "-stream_loop", "1", "-i", audio_path,
            "-t", "10",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            out_path
        ])

        print("Created", out_path)

if __name__ == "__main__":
    main()

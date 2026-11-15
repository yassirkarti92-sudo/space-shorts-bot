import asyncio
import os
import re
import subprocess
import time
from pathlib import Path

import edge_tts
from google import genai

OUT_DIR = Path("downloads")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
VOICE = "en-US-GuyNeural"
RATE = "+10%"
ORIG_VOL = 0.3        # original audio volume under the voice
VOICE_VOL = 1.6
VOICE_DELAY_MS = 300  # voice starts slightly after the hook appears
WORDS_PER_SEC = 2.3
MAX_WORDS = 45

PROMPT = (
    "Watch this football clip. Write an energetic sports-commentator voiceover "
    "of 1-2 short sentences, max {n} words, in English. Describe what actually "
    "happens, start with a punchy hook, build excitement, no spoilers in the first "
    "words. Do NOT guess player or team names unless clearly readable on screen. "
    "No emojis, no hashtags, no quotes. Output only the commentary."
)


def get_duration(video):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(video)],
            capture_output=True, text=True,
        ).stdout.strip()
        return float(out)
    except Exception:
        return 15.0


def has_audio(video):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video)],
            capture_output=True, text=True,
        ).stdout.strip()
        return bool(out)
    except Exception:
        return False


def clean(text):
    text = re.sub(r"[^\x00-\x7F]+", "", text)          # drop emojis / odd chars
    text = re.sub(r"[#*_\"`]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def describe(client, video, dur):
    n = max(8, min(MAX_WORDS, int(dur * WORDS_PER_SEC)))
    f = client.files.upload(file=str(video))
    try:
        for _ in range(60):
            if f.state.name != "PROCESSING":
                break
            time.sleep(2)
            f = client.files.get(name=f.name)
        if f.state.name != "ACTIVE":
            raise RuntimeError(f"Gemini file state: {f.state.name}")
        text = None
        for attempt in range(2):
            try:
                resp = client.models.generate_content(
                    model=MODEL, contents=[f, PROMPT.format(n=n)])
                text = clean(resp.text or "")
                if text:
                    break
            except Exception as e:
                print("Gemini retry:", str(e)[:150])
                time.sleep(5)
        if not text:
            raise RuntimeError("empty commentary")
        words = text.split()
        return " ".join(words[:n])
    finally:
        try:
            client.files.delete(name=f.name)
        except Exception:
            pass


async def tts(text, path):
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))


def mix(video, voice, out, dur):
    if has_audio(video):
        flt = (
            f"[0:a]volume={ORIG_VOL}[a0];"
            f"[1:a]adelay={VOICE_DELAY_MS}|{VOICE_DELAY_MS},volume={VOICE_VOL}[a1];"
            "[a0][a1]amix=inputs=2:duration=longest:normalize=0[aout]"
        )
    else:
        flt = f"[1:a]adelay={VOICE_DELAY_MS}|{VOICE_DELAY_MS},volume={VOICE_VOL}[aout]"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(voice),
        "-filter_complex", flt, "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-t", f"{dur:.2f}", str(out),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def add_voice(client, video):
    dur = get_duration(video)
    voice = Path("voice.mp3")
    tmp = video.with_name(video.stem + "_voice.mp4")
    try:
        text = describe(client, video, dur)
        asyncio.run(tts(text, voice))
        result = mix(video, voice, tmp, dur)
        if result.returncode != 0 or not tmp.exists():
            raise RuntimeError(result.stderr[-300:])
        video.unlink()
        tmp.rename(video.with_suffix(".mp4"))
        print(f"Added voice to {video.name}: {text!r}")
    except Exception as e:
        print(f"Voice skipped for {video.name}, keeping original:", str(e)[:300])
        tmp.unlink(missing_ok=True)
    finally:
        voice.unlink(missing_ok=True)


def main():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("add_voice skipped: no GEMINI_API_KEY")
        return
    client = genai.Client(api_key=key)
    for video in sorted(OUT_DIR.glob("*")):
        if video.suffix.lower() in {".mp4", ".mov", ".webm"}:
            add_voice(client, video)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("add_voice skipped:", e)

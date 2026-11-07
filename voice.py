"""Narration with Piper: free, offline neural text-to-speech."""
import os
import subprocess
import sys
import wave

VOICE = os.environ.get("PIPER_VOICE", "en_US-ryan-high")
VOICE_DIR = os.environ.get("PIPER_DIR", "voices")
SAY = {"km/h": "kilometers per hour", "km": "kilometers", "°C": "degrees Celsius"}


def duration(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def speak(text, out, max_len):
    for k, v in SAY.items():
        text = text.replace(k, v)
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", VOICE, "--data-dir", VOICE_DIR,
         "--length-scale", "0.92", "-f", out],
        input=text.encode(), check=True, timeout=120, capture_output=True)
    d = duration(out)
    if d > max_len:  # too long for the scene: speed up (max 1.4x)
        tmp = out + ".t.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-filter:a",
                        f"atempo={min(1.4, d / max_len):.3f}", tmp], check=True)
        os.replace(tmp, out)
    return out


def make_clips(plan, workdir, max_len):
    """One wav per scene, or None if anything fails (video then has music only)."""
    clips = []
    for i, scene in enumerate(plan):
        try:
            clips.append(speak(scene["caption"], os.path.join(workdir, f"voice{i}.wav"), max_len))
        except Exception as e:
            err = getattr(e, "stderr", b"") or b""
            print("Voice skipped:", str(e)[:120], err.decode(errors="ignore")[-200:])
            return None
    return clips

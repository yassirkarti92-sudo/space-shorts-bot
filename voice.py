# voice.py - Gemini TTS, one request per video, Piper as fallback
import json, os, re, wave
from google import genai
from google.genai import types

MODEL = "gemini-3.8-flash-tts"
VOICE = "Bodi"
RATE = 24000
MAX_WORDS_PER_REQUEST = 220   # above this, split into chunks (max 3)
STATUS_FILE = "voice_status.json"

STYLE = ("flat, monotone, matter-of-fact, fast pace, no pauses between "
         "sentences, no emotion, no emphasis, like a bored engineer "
         "reading a manual")


class VoiceLimitReached(Exception):
    pass


def _chunks(text):
    words = text.split()
    if len(words) <= MAX_WORDS_PER_REQUEST:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    n = min(3, -(-len(words) // MAX_WORDS_PER_REQUEST))
    target = len(words) / n
    out, cur, count = [], [], 0
    for s in sentences:
        cur.append(s)
        count += len(s.split())
        if count >= target and len(out) < n - 1:
            out.append(" ".join(cur)); cur, count = [], 0
    if cur:
        out.append(" ".join(cur))
    return out


def _request(client, text):
    # TEST 1: style passed as a labelled section before the transcript.
    # If you hear the style words spoken aloud, switch to the style field
    # or the config option AI Studio shows for it.
    prompt = f"## Style:\n{STYLE}\n\n## Transcript:\n{text}"
    cfg = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)
            )
        ),
    )
    resp = client.models.generate_content(model=MODEL, contents=prompt, config=cfg)
    for part in resp.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data   # raw 16-bit PCM, 24 kHz mono
    raise RuntimeError("no audio in response")


def synthesize(text, out_path="narration.wav"):
    """Return (wav_path, duration_seconds). Raises on failure so the caller
    can fall back to Piper."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key)
    pcm = b""
    try:
        for chunk in _chunks(text):
            pcm += _request(client, chunk)
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            with open(STATUS_FILE, "w") as f:
                json.dump({"voice": "limit_reached"}, f)
            print("GEMINI TTS LIMIT REACHED - falling back to Piper, no broken video posted")
            raise VoiceLimitReached(msg)
        raise
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(pcm)
    return out_path, len(pcm) / (2 * RATE)

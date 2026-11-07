# voice.py - Gemini 3.8 TTS (Interactions API), Piper as fallback in main.py
import base64, json, os, re, wave
from google import genai

MODEL = "gemini-3.8-flash-tts"
VOICE = "Bodi"
RATE = 24000
MAX_WORDS_PER_REQUEST = 220
STATUS_FILE = "voice_status.json"

# Short on purpose: the docs say long style blocks make the voice drift.
STYLE = "monotone and flat, speaking rapidly, deadpan, no emotion"


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
            out.append(" ".join(cur))
            cur, count = [], 0
    if cur:
        out.append(" ".join(cur))
    return out


def _request(client, text):
    interaction = client.interactions.create(
        model=MODEL,
        input=[{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text,
                "annotations": [{"type": "speech_metadata", "style": STYLE}],
            }],
        }],
        # raw PCM so several chunks can be joined safely
        response_format={"type": "audio", "mime_type": "audio/l16", "sample_rate": RATE},
        generation_config={"speech_config": [{"voice": VOICE}]},
    )
    return base64.b64decode(interaction.output_audio.data)


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
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return out_path, len(pcm) / (2 * RATE)

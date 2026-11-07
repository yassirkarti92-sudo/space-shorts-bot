# voice.py - Gemini 3.8 TTS via plain HTTP (same endpoint AI Studio uses)
import base64, io, json, os, re, urllib.request, urllib.error, wave

MODEL = "gemini-3.8-flash-tts"
VOICE = "Bodi"
RATE = 24000
MAX_WORDS_PER_REQUEST = 220
STATUS_FILE = "voice_status.json"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

STYLE = "calm and warm, steady pace, conversational explainer, gentle cadence, slight pause between story steps"


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


def _request(key, text):
    body = {
        "contents": [{
            "role": "user",
            "parts": [{"text": text, "speech_metadata": {"style": STYLE}}],
        }],
        "generationConfig": {
            "responseModalities": ["audio"],
            "temperature": 1,
            "speech_config": {
                "voice_config": {"prebuilt_voice_config": {"voice_name": VOICE}}
            },
        },
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code}: {detail}")
    for part in data["candidates"][0]["content"]["parts"]:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            mime = inline.get("mimeType") or inline.get("mime_type") or ""
            return base64.b64decode(inline["data"]), mime
    raise RuntimeError("no audio in response: " + json.dumps(data)[:300])


def _to_pcm(raw, mime):
    """Return raw 16-bit mono PCM and its sample rate."""
    if "wav" in mime.lower() or raw[:4] == b"RIFF":
        with wave.open(io.BytesIO(raw)) as w:
            return w.readframes(w.getnframes()), w.getframerate()
    m = re.search(r"rate=(\d+)", mime)
    return raw, int(m.group(1)) if m else RATE


def synthesize(text, out_path="narration.wav"):
    """Return (wav_path, duration_seconds). Raises on failure so the caller
    can fall back to Piper."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    pcm, rate = b"", RATE
    try:
        for chunk in _chunks(text):
            raw, mime = _request(key, chunk)
            part, rate = _to_pcm(raw, mime)
            pcm += part
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
        w.setframerate(rate)
        w.writeframes(pcm)
    return out_path, len(pcm) / (2 * rate)
def make_clips(plan, outdir, max_len):
    """Temporary stub: the old per-scene Piper voice is gone, so videos are
    music-only until the new one-voice-per-video pipeline is wired in."""
    return None

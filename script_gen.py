"""Asks Groq (free tier) to write the script: 4 scenes, one fact each."""
import json, os, random, urllib.error, urllib.request
import render

BASE = "https://api.groq.com/openai/v1"
PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
TYPES = {"planets", "sizes", "zoom", "rocket"}
ANGLES = [
    "extreme scale (huge or tiny)", "time: how long things take or last",
    "speed and motion", "temperature extremes",
    "things that sound fake but are true", "what would happen if you were really there",
    "records and extremes of the solar system", "space compared with everyday life",
]

PROMPT = """You are a viral short-form video scriptwriter AND editor (TikTok, Reels, Shorts) in the space niche.
Write ONE 24-second "Space Facts" video: 4 scenes of about 6 seconds. Every caption is also READ ALOUD by a
narrator, so write for the ear.

STORY STRUCTURE (professional retention editing):
1. HOOK (scene 1): a spike in the first 2 seconds. MAX 9 words. Open on a shocking number, a contradiction,
   or a challenge to what viewers believe. Never start with "Did you know", "Today", "Welcome" or a greeting.
2. BUILD (scene 2): deepen the curiosity with the surprising detail or the scale. Make a comparison the viewer
   can picture using everyday things (a city, a car, a stadium, a lifetime).
3. TWIST (scene 3): a pattern interrupt. The most mind-blowing fact, a change of direction.
4. PAYOFF + LOOP (scene 4): resolve in one punchy line, then end so it flows back into the hook or asks a
   question that makes people comment.

WRITING RULES:
- Each caption: max 12 words (hook max 9). One idea. Concrete numbers, active verbs, short everyday words.
- The 4 captions are ONE connected story, not 4 unrelated facts. Each caption makes the viewer need the next one.
- Make the viewer feel something: awe, fear or disbelief. Cut every filler word. Numbers must be easy to say aloud.
- Strictly true. One fact per caption, verified by NASA or ESA. Say "about" for rounded numbers. Never guess or invent.
- Today's angle: {angle}. Choose a topic that fits it.

SCENES (use each type exactly once; choose the order so what is on screen matches the caption):
- planets = the Sun with Mercury, Venus, Earth and Mars orbiting (solar system, orbits, years, distances)
- sizes = Jupiter growing next to a tiny Earth (sizes and scale)
- zoom = warp-speed zoom toward the Sun (the Sun, stars, light, distances)
- rocket = a rocket launching with Earth below (spaceflight, speed, escaping gravity)

OUTPUT: JSON only, in this order:
{"hook_candidates": [5 different hooks, max 9 words each],
 "topic": "...",
 "hashtags": ["#space", ...max 5],
 "scenes": [4 objects: {"scene": "planets|sizes|zoom|rocket", "caption": "...", "label": "MAX 3 WORDS CAPS"}]}
Scene 1's caption must be the best of your 5 hook candidates.
Do not repeat these recent facts: {recent}"""


def _call(path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"],
                 "Content-Type": "application/json", "User-Agent": "space-shorts-bot/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Groq {path} HTTP {e.code}: {e.read().decode()[:300]}")


_model = None


def pick_model():
    global _model
    if _model is None:
        ids = {m["id"] for m in _call("/models")["data"]}
        print("Groq models available:", sorted(ids))
        _model = next((m for m in PREFERRED if m in ids), None)
        if _model is None:
            raise RuntimeError("none of the preferred models is available")
        print("Using model:", _model)
    return _model


def ask_groq(recent):
    messages = [
        {"role": "system", "content": PROMPT.replace("{recent}", "; ".join(recent[-30:]) or "none").replace("{angle}", random.choice(ANGLES))},
        {"role": "user", "content": "Write one new script now. Output JSON only."},
    ]
    body = {"model": pick_model(), "temperature": 0.7, "messages": messages,
            "response_format": {"type": "json_object"}}
    try:
        res = _call("/chat/completions", body)
    except RuntimeError as e:
        if "HTTP 400" not in str(e):
            raise
        del body["response_format"]  # some models reject JSON mode
        res = _call("/chat/completions", body)
    text = res["choices"][0]["message"]["content"]
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def validate(data):
    scenes = data["scenes"]
    assert len(scenes) == 4 and {s["scene"] for s in scenes} == TYPES, "bad scene set"
    for s in scenes:
        assert 10 <= len(s["caption"]) <= 95, "bad caption length"
        render.fit_caption(s["caption"])  # raises if it cannot fit on screen
        s["label"] = str(s.get("label", ""))[:24]
    tags = [t if t.startswith("#") else "#" + t for t in data.get("hashtags", [])][:5]
    return scenes, tags


def generate(recent):
    """Returns (plan, hashtags, used_ai)."""
    if os.environ.get("GROQ_API_KEY"):
        for _ in range(3):
            try:
                plan, tags = validate(ask_groq(recent))
                return plan, tags, True
            except Exception as e:
                print("script attempt failed:", str(e)[:150])
        raise SystemExit("Groq script failed 3 times - nothing posted.")
    print("No GROQ_API_KEY: using built-in test script (render only).")
    return render.DEFAULT_PLAN, ["#space", "#astronomy", "#facts"], False

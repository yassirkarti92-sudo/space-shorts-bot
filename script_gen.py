"""Asks Groq (free tier) to write the script: 4 scenes, one fact each."""
import json, os, urllib.request
import render

MODEL = "llama-3.3-70b-versatile"
TYPES = {"planets", "sizes", "zoom", "rocket"}
PROMPT = """You write scripts for 24-second vertical "Space Facts" shorts.
Return ONLY JSON: {"hashtags": ["#space", ...max 5], "scenes": [exactly 4 objects]}
Each scene: {"scene": "planets|sizes|zoom|rocket", "caption": "...", "label": "..."}
Rules:
- Use each scene type exactly once, in the order that tells the best story.
- The first caption is a hook: a surprising number or question that makes people keep watching.
- The last caption ends with a punchy line that makes people follow or comment.
- Each caption: max 12 words, plain English, ONE well-known fact verified by NASA/ESA. Never guess or invent numbers.
- label: max 3 words, ALL CAPS, summarising the fact.
- Scene meanings: planets = solar system and orbits, sizes = comparing planet sizes,
  zoom = stars, the Sun, light and distances, rocket = spaceflight and speed.
- Do not repeat these recent facts: {recent}"""


def ask_groq(recent):
    body = {
        "model": MODEL, "temperature": 0.5,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": PROMPT.replace("{recent}", "; ".join(recent[-30:]) or "none")},
            {"role": "user", "content": "Write one new script now."},
        ],
    }
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"],
                 "Content-Type": "application/json", "User-Agent": "space-shorts-bot/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(json.load(r)["choices"][0]["message"]["content"])


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

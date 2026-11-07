"""script_gen2.py - Gemini writes the whole story (narration + captions + scenes). Groq is the fallback.

generate(recent) -> (plan, hashtags, used_ai, subject)
plan = list of {"narration", "caption", "sfx", "spec"}: the format render2.py reads.
Run `python script_gen2.py` to test it alone (one Gemini request, nothing is rendered or posted)."""
import csv
import json
import os
import pathlib
import functools
import re
import urllib.error
import urllib.request

import render2
import vector

# Tried in this order. When one is overloaded (503), slow or out of free quota (429), the next one is used.
GEMINI_MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_TEXT_MODELS", "gemini-3.8-flash,gemini-3.5-flash,gemini-2.5-flash,gemini-flash-latest").split(",")
    if m.strip()]
GEMINI_TIMEOUT = 75
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_MODELS = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]

SUBJECTS = pathlib.Path("subjects.csv")
USED = pathlib.Path("used_subjects.json")
RULES = pathlib.Path("style_rules.txt")

SFX_TYPES = ("whoosh", "rumble", "swell", "boom")
MIN_SCENES, MAX_SCENES = 12, 24
MIN_WORDS, MAX_WORDS = 140, 215
YOU_SHARE = 0.75        # at least this share of scenes must say you / your
MAX_BROKEN = 4          # scenes the checker may reject before the whole script is thrown away


YOU_RE = re.compile(r"\byou(?:r|rs|rself)?\b", re.I)


class LimitReached(Exception):
    """The free Gemini limit was reached (HTTP 429)."""


FORMAT = """
OUTPUT FORMAT
Return ONE JSON object and nothing else:
{
  "topic": "short title",
  "hashtags": ["#science", "...", "max 5"],
  "scenes": [ 16 to 20 scene objects ]
}

Each scene object:
{
  "narration": "the exact words spoken in this scene (about 9 to 11 words)",
  "caption": "max 10 words, one *highlighted* word",
  "sfx": [{"type": "whoosh", "at": 0}],
  "spec": {"background": "navy", "camera": "push", "elements": [ ... ]}
}

Total narration of all scenes: 165 to 185 words. Narration and caption of a scene say the same thing.
The caption is a shortened version of the narration. Wrap exactly one important word of the caption
in stars, like *word*. Never use stars anywhere else.

sfx: 0 to 2 per scene. Allowed types: whoosh, rumble, swell, boom. "at" is seconds from the start of the
scene (0 to 4). Use a boom only for the biggest moments.

SCENE DRAWING (our own code draws it, you only describe it)
background: navy, slate, teal, dusk, void.
camera: push, pull, static.
Each scene has 1 to 16 elements. x is percent of the screen width (0 left, 100 right). y is percent of the
picture area (0 top, 100 bottom of the picture area). Captions have their own space at the bottom, so you
cannot cover them. Sizes s and h are percent of the screen width.
Colour names: navy, slate, gray, cyan, mint, amber, red, white, cream, skin, dark, purple, brown, blue.

Element types and their fields:
- figure: x, y, s (25 to 40 is normal), body (colour), head (colour), eyes (open, closed, wide),
  pose (stand, lie), arm_up (true/false), angle (degrees). The main character is "you".
- pod: x, y, s  (glass cryo-pod)
- window: x, y, s, view (stars, city, planet, ocean)
- skyline: x, y, s, color
- planet: x, y, s, color, ring (true/false)
- disc: x, y, s, color   (circle, use it for the Sun, a ball, an explosion)
- rect: x, y, s, h, color
- badge: x, y, text (UPPERCASE, max 24 characters, ideally 1 to 4 words), color. For dates and labels,
  like "DAY 3", "800 MPH", "35,000 FT".
- text: x, y, text (max 24 characters), color
- clock: x, y, s, spin
- timer: no x and y (it is locked in the top-right corner). at, from. A digital counter that counts up.
  "from" is the number of seconds it shows when it appears. Use it in the scenes where time matters,
  and continue the count from the previous scene.

Optional fields for any element: at (seconds when it appears), until (seconds when it disappears),
move_to [x, y] with move_at and move_time (seconds), shake (0 to 5), bob (0 to 5), pop (false turns
the pop-in off).

Rules for drawing:
- Every scene must be different from the one before it. Change the background, the camera, the objects
  or the layout. Never reuse the same scene twice in a row.
- Keep the main figure between 25 and 40 in size and near the middle (y 35 to 60).
- Use a badge for every number or date mentioned in the narration.
- Only use the types, colours and values listed here. Anything else makes the scene unusable.
- Time values are in seconds and must stay between 0 and 6.
"""


# ---------- subjects ----------
def _read_subjects():
    if not SUBJECTS.exists():
        raise SystemExit("subjects.csv not found")
    out = []
    with SUBJECTS.open(newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row and row[0].strip():
                out.append(row[0].strip())
    if out and out[0].lower() in ("subject", "subjects", "topic", "question"):
        out = out[1:]
    if not out:
        raise SystemExit("subjects.csv has no subjects")
    return out


def pick_subject():
    """First subject of subjects.csv that has not been used yet."""
    subs = _read_subjects()
    used = json.loads(USED.read_text()) if USED.exists() else []
    fresh = [s for s in subs if s not in used]
    if not fresh:
        print("All subjects were used: starting the list again.")
        USED.write_text("[]")
        fresh = subs
    return fresh[0]


def mark_used(subject):
    """Call this after a video was posted."""
    used = json.loads(USED.read_text()) if USED.exists() else []
    if subject not in used:
        used.append(subject)
    USED.write_text(json.dumps(used, indent=2))


# ---------- prompts ----------
def build_prompts(subject, recent):
    rules = RULES.read_text(encoding="utf-8") if RULES.exists() else ""
    system = rules + "\n\n" + FORMAT
    user = (f"SUBJECT: {subject}\n"
            "Write one new video about this subject now. Output the JSON only.\n"
            f"Do not reuse these recent captions: {'; '.join(recent[-30:]) or 'none'}")
    return system, user


def _json_from(text):
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


# ---------- Gemini ----------
def ask_gemini(system, user, model=None):
    model = model or GEMINI_MODELS[0]
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        GEMINI_URL.format(model), data=json.dumps(body).encode(),
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=GEMINI_TIMEOUT) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise LimitReached()
        raise RuntimeError(f"Gemini HTTP {e.code}: {e.read().decode()[:300]}")
    parts = res["candidates"][0]["content"]["parts"]
    return _json_from("".join(p.get("text", "") for p in parts))


# ---------- Groq (fallback) ----------
_groq_model = None


def _groq(path, body=None):
    req = urllib.request.Request(
        GROQ_BASE + path, data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"],
                 "Content-Type": "application/json", "User-Agent": "space-shorts-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Groq {path} HTTP {e.code}: {e.read().decode()[:300]}")


def ask_groq(system, user):
    global _groq_model
    if _groq_model is None:
        ids = {m["id"] for m in _groq("/models")["data"]}
        _groq_model = next((m for m in GROQ_MODELS if m in ids), None)
        if _groq_model is None:
            raise RuntimeError("no preferred Groq model is available")
        print("Using Groq model:", _groq_model)
    body = {"model": _groq_model, "temperature": 0.8,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"}}
    try:
        res = _groq("/chat/completions", body)
    except RuntimeError as e:
        if "HTTP 400" not in str(e):
            raise
        del body["response_format"]
        res = _groq("/chat/completions", body)
    return _json_from(res["choices"][0]["message"]["content"])


# ---------- validation ----------
def validate(data):
    """Check the AI answer. Returns (plan, hashtags) or raises an error (then we try again)."""
    scenes = data["scenes"]
    if not isinstance(scenes, list) or not MIN_SCENES <= len(scenes) <= MAX_SCENES:
        raise ValueError(f"need {MIN_SCENES} to {MAX_SCENES} scenes")
    plan, broken, words, you_scenes = [], 0, 0, 0
    for i, s in enumerate(scenes, 1):
        narration = " ".join(str(s.get("narration", "")).split())
        caption = " ".join(str(s.get("caption", "")).split())
        if not narration or not caption:
            raise ValueError(f"scene {i}: empty narration or caption")
        if len(caption.replace("*", "").split()) > 10:
            raise ValueError(f"scene {i}: caption is longer than 10 words")
        render2.fit_caption(caption)      # raises if it cannot fit on the screen
        words += len(narration.split())
        if YOU_RE.search(narration):
            you_scenes += 1
        elif i <= 2:
            raise ValueError(f"scene {i}: the first two scenes must say you / your")
        sfx = []
        for fx in s.get("sfx") or []:
            if (isinstance(fx, dict) and fx.get("type") in SFX_TYPES
                    and isinstance(fx.get("at"), (int, float)) and not isinstance(fx.get("at"), bool)
                    and 0 <= fx["at"] <= 8):
                sfx.append({"type": fx["type"], "at": float(fx["at"])})
        spec = s.get("spec")
        ok, why = vector.check_scene(spec) if spec else (False, "no spec")
        if not ok:
            print(f"scene {i}: broken ({why}), a safe fallback scene will be used")
            broken += 1
            spec = vector.FALLBACK_SPEC
        plan.append({"narration": narration, "caption": caption, "sfx": sfx, "spec": spec})
    if you_scenes < YOU_SHARE * len(scenes):
        raise ValueError(f"only {you_scenes} of {len(scenes)} scenes say you / your")
    if broken > MAX_BROKEN:
        raise ValueError(f"{broken} broken scenes")
    if not MIN_WORDS <= words <= MAX_WORDS:
        raise ValueError(f"narration has {words} words (need {MIN_WORDS} to {MAX_WORDS})")
    tags = [t if t.startswith("#") else "#" + t for t in data.get("hashtags", []) if isinstance(t, str)][:5]
    return plan, tags


# ---------- main entry ----------
def generate(recent):
    """Returns (plan, hashtags, used_ai, subject)."""
    subject = pick_subject()
    system, user = build_prompts(subject, recent)
    print("Subject:", subject)

    engines = []
    if os.environ.get("GEMINI_API_KEY"):
        for m in GEMINI_MODELS:
            engines.append((m, functools.partial(ask_gemini, model=m), 1))
    if os.environ.get("GROQ_API_KEY"):
        engines.append(("Groq", ask_groq, 2))
    if not engines:
        raise SystemExit("No GEMINI_API_KEY or GROQ_API_KEY set.")

    for name, ask, tries in engines:
        for n in range(1, tries + 1):
            try:
                plan, tags = validate(ask(system, user))
                print(f"{name} script accepted ({len(plan)} scenes).")
                return plan, tags, True, subject
            except LimitReached:
                print(f"*** FREE LIMIT REACHED for {name} (HTTP 429): trying the next engine. ***")
                break
            except Exception as e:
                print(f"{name} attempt {n} failed:", str(e)[:200])
    raise SystemExit("Script generation failed - nothing posted.")


if __name__ == "__main__":
    plan, tags, _, subject = generate([])
    print("\nTags:", " ".join(tags))
    for i, p in enumerate(plan, 1):
        print(f"{i:2}. [{p['spec'].get('background')}/{p['spec'].get('camera')}] {p['caption']}\n"
              f"      {p['narration']}")
    print("\nTotal words:", sum(len(p["narration"].split()) for p in plan))

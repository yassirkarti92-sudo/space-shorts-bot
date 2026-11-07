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
import time
import urllib.error
import urllib.request

import render2
import vector

# Tried in this order. When one is overloaded (503), slow or out of free quota (429), the next one is used.
GEMINI_MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_TEXT_MODELS", "gemini-3.8-flash,gemini-3.5-flash,gemini-flash-latest").split(",")
    if m.strip()]
GEMINI_TIMEOUT = 120
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
background: navy, slate, teal, dusk, void (use a "sky" element on top of it when you want a sky).
camera: push, pull, static, push_fast, pan_left, pan_right, shake.
Each scene has 6 to 14 elements. x and y are the CENTRE of the element. x is percent of the screen width
(0 left, 100 right). y is percent of the picture area (0 top, 100 bottom of the picture area). Captions have
their own space at the bottom, so you cannot cover them. Sizes s and h are percent of the screen width.
ONLY these colour names exist (no gold, no yellow, no orange, no green): navy, slate, gray, cyan, mint,
amber, red, white, cream, dark, purple, brown, blue. Use amber for gold or yellow.

SCENERY (draw these first, in this order: sky, far objects, ground or sea, near objects):
- sky: style (day, dusk, night, storm, red, space). No x, y, s. Always the first element.
- mountain, sun, moon, earth, cloud, tree: x, y, s, optional color. (sun s 15 to 30, earth s 20 to 45)
- city: x, y, s. y is the ground line, s is the height of the tallest building (20 to 50).
- ground: style (grass, desert, rock, snow, lava, dark), x 50, y, s 100. y is the surface line, it fills down.
- sea: style (water, lava, ice), x 50, y, s 100. y is the water line, it fills down.
- crowd: x, y, s (width, 50 to 90), n (3 to 20 people), h (7 to 12, person height), bob (0 to 3).
- skyline, window (view: stars, city, planet, ocean), planet (ring true/false), pod, rect, clock: as before
  (x, y, s, color).

CHARACTER:
- figure: x, y, s (40 to 55: the figure must be BIG), body (colour), head (use gray), eyes (open, closed,
  wide), pose (stand, lie), arm_up (true/false), angle (degrees). The main character is "you".
  act (walk, run, panic, wave, point), flip (true faces left).
  Use act in most scenes: walk or run when you move, panic in danger, point to show things.

SYMBOLS AND TEXT:
- icon: icon (drop, flame, bolt, thermometer, house, heart, warning, hourglass), x, y, s (10 to 20), color.
  Use icons to show what the narration talks about (heat = thermometer or flame, danger = warning, home = house).
- arrow: x, y, s (15 to 35), angle (degrees, 0 = right, -90 = up), color.
- badge: x, y, text (UPPERCASE, max 24 characters, ideally 1 to 4 words), color. For dates and labels,
  like "DAY 3", "800 MPH", "35,000 FT".
- text: x, y, text (max 24 characters), color.
- timer: no x and y (it is locked in the top-right corner). at, from. A digital counter that counts up.
  "from" is the number of seconds it shows when it appears. Use it only when seconds or minutes matter,
  and continue the count from the previous scene.
- particles: kind (rain, snow, embers). No x, y, s. Weather or fire in the air. Add it after the objects.
- disc: x, y, s, color. Only for a ball or a light, never as decoration.

Optional fields for any element: at (seconds when it appears), until (seconds when it disappears),
move_to [x, y] with move_at and move_time (seconds), shake (0 to 5), bob (0 to 5), pop (false turns
the pop-in off).
Motion fields for any element: enter (left, right, up, down: slides in from that side),
drift [dx, dy] (slow slide, percent per second), pulse (0.05 to 0.2: beating size). Use enter on most objects.

Rules for drawing:
- Every scene is a full picture: a sky or background, scenery (ground, sea, city, mountain...), the figure,
  and at least one icon, arrow or badge that shows the point of the sentence. Never a figure with two plain
  circles. Never a big empty area.
- Every scene must be different from the one before it. Change the sky, the scenery, the camera, the
  objects or the layout. Never reuse the same scene twice in a row.
- Place the figure standing on the ground or sea line when there is one. Keep it between x 25 and 75.
- Show the place and the danger of the narration with scenery and icons (a flooded city = city + sea +
  warning icon), not with abstract shapes.
- Use a badge for every number or date mentioned in the narration.
- Only use the types, colours and values listed here. Anything else makes the scene unusable.
- Time values are in seconds and must stay between 0 and 6.
- Every element is a FLAT object with a "type" key, like {"type": "sky", "style": "night"}.
  Never wrap it like {"sky": {...}}.
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
    body = {"model": _groq_model, "temperature": 0.8, "max_tokens": 8000,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"}}
    if "gpt-oss" in _groq_model:
        body["reasoning_effort"] = "low"
    try:
        res = _groq("/chat/completions", body)
    except RuntimeError as e:
        if "HTTP 400" not in str(e):
            raise
        del body["response_format"]
        res = _groq("/chat/completions", body)
    content = res["choices"][0]["message"].get("content")
    if not content:
        raise RuntimeError("Groq returned an empty answer")
    return _json_from(content)


# ---------- scene repair ----------
ALIAS = {"gold": "amber", "yellow": "amber", "orange": "amber", "coral": "red", "pink": "red",
         "green": "mint", "sky": "cyan", "lightblue": "cyan", "teal": "cyan", "black": "dark",
         "void": "dark", "grey": "gray", "silver": "gray", "tan": "cream", "beige": "cream",
         "violet": "purple", "indigo": "purple"}
BGMAP = {"space": "void", "night": "void", "black": "void", "dark": "void", "sunset": "dusk",
         "orange": "dusk", "blue": "navy", "ocean": "teal", "sea": "teal", "gray": "slate",
         "grey": "slate", "red": "dusk"}


def repair_spec(spec):
    """Fix small mistakes (unknown colour or background names, too few elements) instead of rejecting."""
    if not isinstance(spec, dict):
        return spec
    spec = dict(spec)
    bg = str(spec.get("background", "navy")).lower()
    spec["background"] = bg if bg in vector.BACKGROUNDS else BGMAP.get(bg, "navy")
    if spec.get("camera", "push") not in vector.CAMERAS:
        spec["camera"] = "push"
    els = [_flatten(e) for e in (spec.get("elements") or [])]
    els = [e for e in els if isinstance(e, dict) and e.get("type") in vector.TYPES]
    for e in els:
        for k in ("color", "body", "head", "hair"):
            if k in e:
                c = str(e[k]).lower()
                e[k] = c if c in vector.COLORS else ALIAS.get(c, "gray")
    if len([e for e in els if e.get("type") != "timer"]) < 3:
        if not any(e.get("type") == "sky" for e in els):
            els.insert(0, {"type": "sky", "style": "night"})
        if not any(e.get("type") in ("ground", "sea") for e in els):
            els.insert(1, {"type": "ground", "style": "dark", "x": 50, "y": 78, "s": 100})
    spec["elements"] = els[:vector.MAX_ELEMENTS]
    return spec
def _flatten(e):
    """Unwrap {"sky": {"style": "night"}} into {"type": "sky", "style": "night"}.
    Elements that already have a "type" key are returned unchanged."""
    if not isinstance(e, dict):
        return e
    if "type" in e:
        return dict(e)
    if len(e) == 1:
        k, v = next(iter(e.items()))
        if k in vector.TYPES and isinstance(v, dict):
            out = dict(v)
            out["type"] = k
            return out
    return dict(e)


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
        if i == 1:
            print("RAW SCENE 1:", json.dumps(s)[:1500])
        spec = repair_spec(spec)
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
            engines.append((m, functools.partial(ask_gemini, model=m), 2))
    if os.environ.get("GROQ_API_KEY"):
        engines.append(("Groq", ask_groq, 3))
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
                if n < tries:
                    time.sleep(60 if "429" in str(e) else 20)
    raise SystemExit("Script generation failed - nothing posted.")


if __name__ == "__main__":
    plan, tags, _, subject = generate([])
    print("\nTags:", " ".join(tags))
    for i, p in enumerate(plan, 1):
        print(f"{i:2}. [{p['spec'].get('background')}/{p['spec'].get('camera')}] {p['caption']}\n"
              f"      {p['narration']}")
    print("\nTotal words:", sum(len(p["narration"].split()) for p in plan))

# scenes.py - scene engine v1: draws one scene from a JSON description.
# Canvas 135x240. Keep drawings inside y=40..178 (title above, caption below).
import math, random

W, H = 135, 240
MAX_ELEMENTS = 12
BACKGROUNDS = ("space", "sky", "dark", "ocean")
TYPES = ("disc", "rect", "explosion")
COLORS = {
    "white": (240, 240, 255), "yellow": (255, 214, 10), "orange": (255, 140, 20),
    "red": (220, 60, 50), "blue": (70, 130, 255), "green": (60, 170, 90),
    "brown": (130, 80, 40), "gray": (130, 135, 150), "black": (20, 20, 28),
    "sand": (225, 195, 140), "cyan": (80, 210, 230), "purple": (150, 90, 210),
    "pink": (240, 130, 180),
}


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


_rng = random.Random(7)
STARS = [(_rng.randrange(W), _rng.randrange(H), _rng.random() * 6.28) for _ in range(90)]


# ---------- validation: a broken description is rejected, never drawn ----------
def _num(v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
        raise ValueError(f"bad number {v!r} (allowed {lo}..{hi})")


def check_scene(spec):
    """Return (True, "") if the scene is safe to draw, else (False, reason)."""
    try:
        if spec.get("background") not in BACKGROUNDS:
            return False, "unknown background"
        els = spec.get("elements")
        if not isinstance(els, list) or not 1 <= len(els) <= MAX_ELEMENTS:
            return False, "elements must be a list of 1 to %d" % MAX_ELEMENTS
        if len(str(spec.get("label", ""))) > 24:
            return False, "label too long"
        for e in els:
            if e.get("type") not in TYPES:
                return False, "unknown element type"
            if e["type"] != "explosion" and e.get("color", "white") not in COLORS:
                return False, "unknown color"
            _num(e.get("x"), -20, 155)
            _num(e.get("y"), 20, 200)
            for k in ("at", "until"):
                if k in e:
                    _num(e[k], 0, 12)
            if e["type"] in ("disc", "explosion"):
                _num(e.get("r"), 1, 120)
            if e["type"] == "rect":
                _num(e.get("w"), 1, 200)
                _num(e.get("h"), 1, 200)
            if "grow_to" in e:
                _num(e["grow_to"], 1, 120)
            if "move_to" in e:
                _num(e["move_to"][0], -20, 155)
                _num(e["move_to"][1], 20, 200)
            if "orbit" in e:
                o = e["orbit"]
                _num(o["cx"], 0, 135)
                _num(o["cy"], 40, 178)
                _num(o["radius"], 1, 100)
                _num(o["period"], 0.5, 30)
            if "shake" in e:
                _num(e["shake"], 0, 3)
    except Exception as ex:
        return False, str(ex)
    return True, ""


# ---------- backgrounds ----------
def background(d, kind, t):
    if kind == "space":
        d.rectangle([0, 0, W, H], fill=(6, 6, 22))
        for x, y, ph in STARS:
            v = int(70 + 150 * (0.55 + 0.45 * math.sin(t * 2.2 + ph)))
            d.point((x, y), fill=(v, v, min(255, v + 20)))
    elif kind == "dark":
        d.rectangle([0, 0, W, H], fill=(10, 10, 16))
    else:
        top, bot = ((70, 150, 230), (175, 220, 250)) if kind == "sky" else ((20, 90, 150), (5, 25, 60))
        for y in range(H):
            k = y / H
            d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))


# ---------- elements ----------
def place(e, t):
    x, y = e["x"], e["y"]
    at = e.get("at", 0)
    if "orbit" in e:
        o = e["orbit"]
        a = 2 * math.pi * (t - at) / o["period"] + o.get("phase", 0)
        x, y = o["cx"] + o["radius"] * math.cos(a), o["cy"] + o["radius"] * math.sin(a)
    elif "move_to" in e:
        k = ease((t - at) / e.get("move_time", 2.0))
        x += (e["move_to"][0] - x) * k
        y += (e["move_to"][1] - y) * k
    if e.get("shake"):
        x += round(math.sin(t * 40) * e["shake"])
    return int(x), int(y)


def draw_explosion(d, e, t):
    p = (t - e.get("at", 0)) / 1.2
    if not 0 <= p <= 1:
        return
    x, y, R = int(e["x"]), int(e["y"]), e["r"]
    ring = int(R * ease(p))
    shade = tuple(int(v * (1 - 0.6 * p)) for v in COLORS["white"])
    if ring > 1:
        d.ellipse([x - ring, y - ring, x + ring, y + ring], outline=shade, width=2)
    core = int(R * 0.55 * (1 - p))
    if core > 0:
        d.ellipse([x - core, y - core, x + core, y + core], fill=COLORS["orange"])
        c2 = int(core * 0.6)
        d.ellipse([x - c2, y - c2, x + c2, y + c2], fill=COLORS["yellow"])
    rnd = random.Random(int(x * 31 + y))
    for i in range(16):
        a = rnd.random() * 6.2832
        dist = R * (0.4 + 0.8 * rnd.random()) * ease(p)
        px, py = int(x + dist * math.cos(a)), int(y + dist * math.sin(a))
        d.rectangle([px, py, px + 1, py + 1], fill=COLORS["orange" if i % 2 else "red"])


def draw_element(d, e, t):
    if t < e.get("at", 0) or t > e.get("until", 99):
        return
    if e["type"] == "explosion":
        return draw_explosion(d, e, t)
    x, y = place(e, t)
    c = COLORS[e.get("color", "white")]
    if e["type"] == "disc":
        r = e["r"]
        if "grow_to" in e:
            r += (e["grow_to"] - r) * ease((t - e.get("at", 0)) / e.get("grow_time", 2.0))
        r = int(round(r))
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    else:
        d.rectangle([x, y, x + e["w"], y + e["h"]], fill=c)


def draw_scene(d, spec, t):
    """Draw one scene. Returns the label list in the same format as the old scenes."""
    background(d, spec["background"], t)
    for e in spec["elements"]:
        draw_element(d, e, t)
    label = str(spec.get("label", ""))
    return [(label.upper(), 67, 172)] if label else []

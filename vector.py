"""vector.py - flat 2D vector scene engine (story style).
Draws on a 540x960 canvas. In a scene description, x and sizes (s, h) are PERCENT of
the width, y is PERCENT of the height. render_scene() returns a 1080x1920 image."""
import math
import random

from PIL import Image, ImageDraw, ImageFont

CW, CH = 540, 960
OUT_W, OUT_H = 1080, 1920
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

COLORS = {
    "navy": (22, 25, 36), "slate": (34, 39, 51), "gray": (120, 130, 150),
    "cyan": (77, 208, 225), "mint": (129, 199, 132), "amber": (255, 183, 77),
    "red": (229, 115, 115), "white": (255, 255, 255), "cream": (255, 244, 214),
    "skin": (242, 205, 165), "dark": (30, 30, 40), "purple": (150, 110, 210),
    "brown": (120, 85, 60), "blue": (80, 130, 230),
}
BACKGROUNDS = {
    "navy": ((22, 25, 36), (34, 39, 51)),
    "slate": ((34, 39, 51), (58, 66, 86)),
    "teal": ((14, 40, 52), (26, 78, 94)),
    "dusk": ((38, 30, 62), (110, 70, 90)),
    "void": ((8, 9, 14), (18, 20, 30)),
}
TYPES = ("figure", "pod", "window", "skyline", "planet", "disc", "rect", "badge", "text", "clock")
NEEDS_SIZE = ("figure", "pod", "window", "skyline", "planet", "disc", "rect", "clock")
VIEWS = ("stars", "city", "planet", "ocean")
EYES = ("open", "closed", "wide")
POSES = ("stand", "lie")
CAMERAS = ("push", "pull", "static")
MAX_ELEMENTS = 16


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


_fonts = {}


def font(size):
    size = int(max(8, size))
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


def px(v):
    return v / 100.0 * CW


def py(v):
    return v / 100.0 * CH


# ---------- validation: a broken description is rejected, never drawn ----------
def _num(v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
        raise ValueError(f"bad number {v!r} (allowed {lo}..{hi})")


def check_scene(spec):
    """Return (True, "") if the scene is safe to draw, else (False, reason)."""
    try:
        if not isinstance(spec, dict):
            return False, "scene is not an object"
        if spec.get("background", "navy") not in BACKGROUNDS:
            return False, "unknown background"
        if spec.get("camera", "push") not in CAMERAS:
            return False, "unknown camera"
        els = spec.get("elements")
        if not isinstance(els, list) or not 1 <= len(els) <= MAX_ELEMENTS:
            return False, "elements must be a list of 1 to %d" % MAX_ELEMENTS
        for e in els:
            kind = e.get("type")
            if kind not in TYPES:
                return False, f"unknown element type {kind!r}"
            _num(e.get("x"), -30, 130)
            _num(e.get("y"), -30, 130)
            if kind in NEEDS_SIZE:
                _num(e.get("s"), 1, 150)
            elif "s" in e:
                _num(e["s"], 1, 30)
            for k in ("color", "body", "head", "hair"):
                if k in e and e[k] not in COLORS:
                    return False, f"unknown color {e[k]!r}"
            for k in ("at", "until", "move_at"):
                if k in e:
                    _num(e[k], 0, 60)
            if "move_time" in e:
                _num(e["move_time"], 0.2, 30)
            if "h" in e:
                _num(e["h"], 1, 150)
            for k in ("shake", "bob"):
                if k in e:
                    _num(e[k], 0, 5)
            if "angle" in e:
                _num(e["angle"], -360, 360)
            if "spin" in e:
                _num(e["spin"], -720, 720)
            if "move_to" in e:
                _num(e["move_to"][0], -30, 130)
                _num(e["move_to"][1], -30, 130)
            if kind in ("badge", "text"):
                if not isinstance(e.get("text"), str) or not 1 <= len(e["text"]) <= 24:
                    return False, "text must be 1 to 24 characters"
            if kind == "window" and e.get("view", "stars") not in VIEWS:
                return False, "unknown window view"
            if kind == "figure":
                if e.get("eyes", "open") not in EYES:
                    return False, "unknown eyes"
                if e.get("pose", "stand") not in POSES:
                    return False, "unknown pose"
    except Exception as ex:
        return False, str(ex)
    return True, ""


FALLBACK_SPEC = {
    "background": "navy", "camera": "push",
    "elements": [{"type": "figure", "x": 50, "y": 45, "s": 45, "eyes": "wide"}],
}

# ---------- background ----------
_bg_cache = {}


def _gradient(name):
    if name not in _bg_cache:
        top, bot = BACKGROUNDS[name]
        im = Image.new("RGB", (CW, CH))
        d = ImageDraw.Draw(im)
        for y in range(CH):
            k = y / (CH - 1)
            d.line([(0, y), (CW, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
        _bg_cache[name] = im
    return _bg_cache[name].copy()


_r = random.Random(11)
DUST = [(_r.random() * CW, _r.random() * CH, _r.uniform(4, 14), _r.choice([1, 1, 2, 2, 3])) for _ in range(45)]


def draw_dust(d, t):
    for x, y0, sp, r in DUST:
        y = (y0 - t * sp) % CH
        d.ellipse([x - r, y - r, x + r, y + r], fill=(160, 210, 230, 70))


# ---------- placement and animation ----------
def place(e, t):
    x, y = float(e["x"]), float(e["y"])
    if "move_to" in e:
        k = ease((t - e.get("move_at", e.get("at", 0.0))) / e.get("move_time", 2.0))
        x += (e["move_to"][0] - x) * k
        y += (e["move_to"][1] - y) * k
    if e.get("shake"):
        x += math.sin(t * 45) * e["shake"] * 0.4
    if e.get("bob"):
        y += math.sin(t * 2.2) * e["bob"]
    return px(x), py(y)


def pop_scale(e, t):
    if e.get("pop", True) is False:
        return 1.0
    u = (t - e.get("at", 0.0)) / 0.35
    if u >= 1:
        return 1.0
    if u < 0.7:
        return 1.05 * ease(u / 0.7)
    return 1.05 - 0.05 * ease((u - 0.7) / 0.3)


# ---------- elements ----------
def figure_layer(Hf, body, head, hair, eyes, arm_up):
    Hf = max(8, int(Hf))
    L = int(Hf * 1.5)
    im = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, top, r = L / 2, (L - Hf) / 2, 0.2 * Hf
    lw = max(2, int(0.07 * Hf))
    limb = (50, 58, 75)
    for sx in (-1, 1):
        d.line([(ox + sx * 0.07 * Hf, top + 0.72 * Hf), (ox + sx * 0.09 * Hf, top + Hf)], fill=limb, width=lw)
    d.rounded_rectangle([ox - 0.16 * Hf, top + 2 * r - 0.02 * Hf, ox + 0.16 * Hf, top + 0.76 * Hf],
                        radius=max(1, int(0.07 * Hf)), fill=body)
    aw = max(2, int(0.06 * Hf))
    d.line([(ox - 0.16 * Hf, top + 0.46 * Hf), (ox - 0.26 * Hf, top + 0.70 * Hf)], fill=body, width=aw)
    hx, hy = (ox + 0.30 * Hf, top + 0.30 * Hf) if arm_up else (ox + 0.26 * Hf, top + 0.70 * Hf)
    d.line([(ox + 0.16 * Hf, top + 0.46 * Hf), (hx, hy)], fill=body, width=aw)
    hr = 0.035 * Hf
    for cx, cy in ((ox - 0.26 * Hf, top + 0.70 * Hf), (hx, hy)):
        d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=head)
    d.ellipse([ox - r, top, ox + r, top + 2 * r], fill=head)
    d.pieslice([ox - r, top, ox + r, top + 2 * r], 190, 350, fill=hair)
    ey = top + r + 0.03 * Hf
    for sx in (-1, 1):
        ex = ox + sx * 0.08 * Hf
        if eyes == "closed":
            d.line([(ex - 0.05 * Hf, ey), (ex + 0.05 * Hf, ey)], fill=COLORS["dark"], width=max(2, int(0.02 * Hf)))
        else:
            rx, ry, pr = (0.08, 0.095, 0.02) if eyes == "wide" else (0.06, 0.07, 0.025)
            d.ellipse([ex - rx * Hf, ey - ry * Hf, ex + rx * Hf, ey + ry * Hf], fill=COLORS["white"])
            d.ellipse([ex - pr * Hf, ey - pr * Hf, ex + pr * Hf, ey + pr * Hf], fill=COLORS["dark"])
    return im


def draw_figure(img, e, t, sc):
    x, y = place(e, t)
    Hf = px(e["s"]) * sc
    layer = figure_layer(Hf, COLORS[e.get("body", "cyan")], COLORS[e.get("head", "skin")],
                         COLORS[e.get("hair", "dark")], e.get("eyes", "open"), e.get("arm_up", False))
    angle = e.get("angle", 0) + (90 if e.get("pose") == "lie" else 0)
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(x - layer.width / 2), int(y - layer.height / 2)), layer)


def draw_pod(d, e, t, sc):
    x, y = place(e, t)
    w = px(e["s"]) * sc
    h = w * 1.9
    d.rounded_rectangle([x - w / 2 - 10, y - h / 2 - 10, x + w / 2 + 10, y + h / 2 + 10],
                        radius=int(w * 0.45), fill=(77, 208, 225, 30))
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], radius=int(w * 0.4),
                        fill=(77, 208, 225, 45), outline=(77, 208, 225, 230), width=4)
    d.rectangle([x - w * 0.55, y + h / 2 - 14, x + w * 0.55, y + h / 2 + 10], fill=(55, 62, 80))
    d.rectangle([x - w * 0.45, y - h / 2 - 12, x + w * 0.45, y - h / 2 + 6], fill=(55, 62, 80))
    d.line([(x - w * 0.3, y - h * 0.35), (x - w * 0.3, y + h * 0.1)], fill=(255, 255, 255, 90), width=4)


def _view(w, h, kind, t):
    im = Image.new("RGB", (w, h), (8, 9, 14))
    d = ImageDraw.Draw(im, "RGBA")
    rng = random.Random(5)
    if kind == "city":
        for y in range(h):
            k = y / h
            d.line([(0, y), (w, y)], fill=(int(40 + 70 * k), int(30 + 40 * k), int(62 + 28 * k)))
        bw = w / 6
        for i in range(6):
            bh = h * rng.uniform(0.25, 0.6)
            x0 = int(i * bw) 
            x1 = max(x0, int(i * bw + bw - 4))  
            d.rectangle([x0, h - bh, x1, h], fill=(26, 28, 44))
            for _ in range(5):
                wx = i * bw + rng.uniform(6, max(7, bw - 16))
                wy = h - bh + rng.uniform(8, max(9, bh - 14))
                d.rectangle([wx, wy, wx + 6, wy + 8], fill=(255, 183, 77, 210))
    elif kind == "ocean":
        for y in range(h):
            k = y / h
            d.line([(0, y), (w, y)], fill=(int(14 + 12 * k), int(60 + 50 * k), int(80 + 50 * k)))
        for j in range(4):
            yb = h * (0.35 + 0.15 * j)
            d.line([(x, yb + 6 * math.sin(x / 18 + t * 1.5 + j)) for x in range(0, w + 1, 8)],
                   fill=(255, 255, 255, 70), width=3)
    else:
        for i in range(30):
            sx, sy = rng.uniform(0, w), rng.uniform(0, h)
            a = int(120 + 110 * math.sin(t * 2 + i))
            d.ellipse([sx - 1.5, sy - 1.5, sx + 1.5, sy + 1.5], fill=(255, 255, 255, max(30, a)))
        if kind == "planet":
            cx, cy, r = w * 0.62, h * 0.48, h * 0.28
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COLORS["blue"])
            d.ellipse([cx - r * 0.7, cy - r * 0.75, cx - r * 0.1, cy - r * 0.25], fill=(255, 255, 255, 40))
            d.ellipse([cx - r * 1.6, cy - r * 0.3, cx + r * 1.6, cy + r * 0.3], outline=COLORS["amber"] + (220,), width=4)
    return im


def draw_window(img, d, e, t, sc):
    x, y = place(e, t)
    w = int(max(20, px(e["s"]) * sc))
    h = int(w * 0.75)
    view = _view(w, h, e.get("view", "stars"), t)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=int(w * 0.08), fill=255)
    img.paste(view, (int(x - w / 2), int(y - h / 2)), mask)
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], radius=int(w * 0.08),
                        outline=COLORS["gray"], width=7)


def draw_skyline(d, e, t, sc):
    x, y = place(e, t)
    rng = random.Random(e.get("seed", 3))
    col = COLORS[e.get("color", "slate")]
    n = 9
    bw = CW * 1.05 / n
    hmax = px(e["s"]) * sc
    for i in range(n):
        h = hmax * rng.uniform(0.45, 1.0)
        x0 = i * bw - 12
        d.rectangle([x0, y - h, x0 + bw - 4, y], fill=col)
        for wy in range(int(y - h + 14), int(y - 8), 22):
            for wx in range(int(x0 + 8), int(x0 + bw - 14), 20):
                if rng.random() < 0.35:
                    d.rectangle([wx, wy, wx + 7, wy + 10], fill=(255, 183, 77, 200))


def draw_planet(d, e, t, sc):
    x, y = place(e, t)
    r = px(e["s"]) * sc / 2
    d.ellipse([x - r, y - r, x + r, y + r], fill=COLORS[e.get("color", "cyan")])
    d.ellipse([x - r * 0.7, y - r * 0.75, x - r * 0.1, y - r * 0.25], fill=(255, 255, 255, 45))
    if e.get("ring"):
        d.ellipse([x - r * 1.6, y - r * 0.3, x + r * 1.6, y + r * 0.3], outline=COLORS["amber"] + (230,), width=5)


def draw_clock(d, e, t, sc):
    x, y = place(e, t)
    r = px(e["s"]) * sc / 2
    d.ellipse([x - r, y - r, x + r, y + r], fill=(34, 39, 51, 235), outline=COLORS["cream"], width=5)
    for k in range(12):
        a = math.radians(k * 30)
        d.line([(x + r * 0.82 * math.cos(a), y + r * 0.82 * math.sin(a)),
                (x + r * 0.94 * math.cos(a), y + r * 0.94 * math.sin(a))], fill=COLORS["cream"], width=4)
    a = math.radians(-90 + e.get("spin", 90) * (t - e.get("at", 0.0)))
    d.line([(x, y), (x + 0.7 * r * math.cos(a), y + 0.7 * r * math.sin(a))], fill=COLORS["amber"], width=6)
    d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=COLORS["amber"])


def draw_element(img, d, e, t):
    if t < e.get("at", 0.0) or t > e.get("until", 999):
        return
    sc = pop_scale(e, t)
    if sc <= 0.02:
        return
    kind = e["type"]
    if kind == "figure":
        draw_figure(img, e, t, sc)
    elif kind == "pod":
        draw_pod(d, e, t, sc)
    elif kind == "window":
        draw_window(img, d, e, t, sc)
    elif kind == "skyline":
        draw_skyline(d, e, t, sc)
    elif kind == "planet":
        draw_planet(d, e, t, sc)
    elif kind == "clock":
        draw_clock(d, e, t, sc)
    elif kind == "disc":
        x, y = place(e, t)
        r = px(e["s"]) * sc / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=COLORS[e.get("color", "cyan")])
    elif kind == "rect":
        x, y = place(e, t)
        w, h = px(e["s"]) * sc, px(e.get("h", e["s"])) * sc
        d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], radius=8,
                            fill=COLORS[e.get("color", "slate")])
    elif kind == "badge":
        x, y = place(e, t)
        f = font(px(e.get("s", 7)) * sc)
        l, tp, rr, b = d.textbbox((0, 0), e["text"], font=f)
        tw, th = rr - l, b - tp
        pad = th * 0.7
        d.rounded_rectangle([x - tw / 2 - pad, y - th / 2 - pad * 0.7, x + tw / 2 + pad, y + th / 2 + pad * 0.7],
                            radius=int(th * 0.5), fill=COLORS[e.get("color", "amber")])
        d.text((x, y), e["text"], font=f, fill=COLORS["navy"], anchor="mm")
    elif kind == "text":
        x, y = place(e, t)
        d.text((x, y), e["text"], font=font(px(e.get("s", 7)) * sc), fill=COLORS[e.get("color", "white")],
               anchor="mm", stroke_width=3, stroke_fill=COLORS["navy"])


def render_scene(spec, lt, dur):
    """Draw scene `spec` at scene time lt (seconds). Returns a 1080x1920 RGB image."""
    img = _gradient(spec.get("background", "navy"))
    d = ImageDraw.Draw(img, "RGBA")
    draw_dust(d, lt)
    for e in spec["elements"]:
        draw_element(img, d, e, lt)
    p = min(1.0, max(0.0, lt / max(dur, 0.1)))
    cam = spec.get("camera", "push")
    z = 1 + 0.08 * p if cam == "push" else (1.08 - 0.08 * p if cam == "pull" else 1.0)
    w, h = CW / z, CH / z
    x0, y0 = (CW - w) / 2, (CH - h) / 2
    return img.resize((OUT_W, OUT_H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))

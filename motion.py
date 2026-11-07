"""motion.py - livelier animation for vector.py. Needs two lines at the END of vector.py:
import motion
motion.install(globals())
Adds: figure acts (walk, run, panic, wave, point) with blinking and breathing, flip, element fields
enter (left/right/up/down), drift [dx, dy], pulse, and cameras push_fast, pan_left, pan_right, shake."""
import math

from PIL import Image, ImageDraw, ImageFilter

_g = {}
ACTS = ("walk", "run", "panic", "wave", "point")
NEW_CAMERAS = ("push_fast", "pan_left", "pan_right", "shake")


def _pill(d, x0, y0, x1, y1, w, fill):
    d.line([(x0, y0), (x1, y1)], fill=fill, width=int(w))
    r = w / 2
    for cx, cy in ((x0, y0), (x1, y1)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def figure_layer(Hf, body, head, hair, eyes, arm_up, act, t):
    Hf = max(8, int(Hf))
    L = int(Hf * 1.5)
    im = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, top = L / 2, (L - Hf) / 2
    r, bw = 0.27 * Hf, 0.17 * Hf
    body_top, body_bot = top + 1.5 * r, top + 0.84 * Hf
    limb = tuple(int(c * 0.8) for c in body)
    run = act == "run"
    moving = act in ("walk", "run")
    sw = math.sin(t * (9 if run else 6.5)) if moving else 0.0
    for sx in (-1, 1):
        off = lift = 0.0
        if moving:
            off = -sx * sw * (0.16 if run else 0.11) * Hf
            lift = max(0.0, -sx * sw) * 0.03 * Hf
        elif act == "panic":
            off = sx * 0.06 * Hf
        _pill(d, ox + sx * 0.08 * Hf, body_bot - 0.04 * Hf, ox + sx * 0.08 * Hf + off,
              top + Hf - 0.03 * Hf - lift, 0.10 * Hf, limb)
    d.rounded_rectangle([ox - bw, body_top, ox + bw, body_bot], radius=int(bw), fill=body)
    aw = 0.075 * Hf
    lx, rx, sy = ox - bw + 0.02 * Hf, ox + bw - 0.02 * Hf, body_top + 0.07 * Hf
    lh = (ox - bw - 0.05 * Hf, body_top + 0.30 * Hf)
    rh = (ox + bw + 0.05 * Hf, body_top + 0.30 * Hf)
    if moving:
        a = sw * (0.16 if run else 0.12) * Hf
        up = 0.06 * Hf if run else 0.0
        lh = (lx - 0.03 * Hf + a, body_top + 0.28 * Hf - up)
        rh = (rx + 0.03 * Hf - a, body_top + 0.28 * Hf - up)
    elif act == "panic":
        lh = (ox - bw - 0.14 * Hf, body_top - 0.12 * Hf + math.sin(t * 14) * 0.05 * Hf)
        rh = (ox + bw + 0.14 * Hf, body_top - 0.12 * Hf + math.sin(t * 14 + 1.5) * 0.05 * Hf)
    elif act == "wave":
        rh = (rx + 0.12 * Hf + math.sin(t * 8) * 0.06 * Hf, body_top - 0.10 * Hf)
    elif act == "point":
        rh = (rx + 0.30 * Hf, body_top + 0.05 * Hf)
    elif arm_up:
        rh = (rx + 0.14 * Hf, body_top - 0.10 * Hf)
    _pill(d, lx, sy, lh[0], lh[1], aw, limb)
    _pill(d, rx, sy, rh[0], rh[1], aw, limb)
    d.ellipse([ox - r, top, ox + r, top + 2 * r], fill=head)
    if act == "panic":
        eyes = "wide"
    elif eyes == "open" and (t % 3.2) < 0.12:
        eyes = "closed"
    ey, spread = top + r + 0.01 * Hf, 0.105 * Hf
    ew, eh = (0.11, 0.17) if eyes == "wide" else (0.085, 0.135)
    glow = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    eye_col = (77, 208, 225)
    for sx in (-1, 1):
        ex = ox + sx * spread
        if eyes == "closed":
            box = [ex - 0.07 * Hf, ey - 0.012 * Hf, ex + 0.07 * Hf, ey + 0.012 * Hf]
        else:
            box = [ex - ew * Hf / 2, ey - eh * Hf / 2, ex + ew * Hf / 2, ey + eh * Hf / 2]
        g = 0.045 * Hf
        gd.ellipse([box[0] - g, box[1] - g, box[2] + g, box[3] + g], fill=eye_col + (170,))
    glow = glow.filter(ImageFilter.GaussianBlur(max(1, 0.045 * Hf)))
    im.alpha_composite(glow)
    d = ImageDraw.Draw(im)
    for sx in (-1, 1):
        ex = ox + sx * spread
        if eyes == "closed":
            d.rounded_rectangle([ex - 0.07 * Hf, ey - 0.012 * Hf, ex + 0.07 * Hf, ey + 0.012 * Hf],
                                radius=max(1, int(0.012 * Hf)), fill=eye_col)
        else:
            d.ellipse([ex - ew * Hf / 2, ey - eh * Hf / 2, ex + ew * Hf / 2, ey + eh * Hf / 2],
                      fill=(235, 252, 255))
    return im


def draw_figure(img, e, t, sc):
    g = _g
    x, y = g["place"](e, t)
    Hf = g["px"](e["s"]) * sc
    act = e.get("act") if e.get("act") in ACTS else None
    if act in ("walk", "run"):
        y -= abs(math.sin(t * (9 if act == "run" else 6.5))) * 0.03 * Hf
    elif act == "panic":
        x += math.sin(t * 40) * 0.012 * Hf
    else:
        y += math.sin(t * 2.2) * 0.008 * Hf
    C = g["COLORS"]
    head = e.get("head", "gray")
    head = "gray" if head == "skin" else head
    layer = figure_layer(Hf, C[e.get("body", "cyan")], C[head], C[e.get("hair", "dark")],
                         e.get("eyes", "open"), e.get("arm_up", False), act, t)
    if e.get("flip"):
        layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
    angle = e.get("angle", 0) + (90 if e.get("pose") == "lie" else 0)
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(x - layer.width / 2), int(y - layer.height / 2)), layer)


def render_scene(spec, lt, dur):
    g = _g
    CW, CH = g["CW"], g["CH"]
    img = g["_gradient"](spec.get("background", "navy"))
    d = ImageDraw.Draw(img, "RGBA")
    g["draw_dust"](d, lt)
    for e in spec["elements"]:
        g["draw_element"](img, d, e, lt)
    p = min(1.0, max(0.0, lt / max(dur, 0.1)))
    cam = spec.get("camera", "push")
    z, ox, oy = 1.0, 0.0, 0.0
    if cam == "push":
        z = 1 + 0.08 * p
    elif cam == "pull":
        z = 1.08 - 0.08 * p
    elif cam == "push_fast":
        z = 1 + 0.2 * g["ease"](p)
    elif cam in ("pan_left", "pan_right"):
        z = 1.12
        ox = CW * 0.06 * (1 - 2 * p) * (1 if cam == "pan_left" else -1)
    elif cam == "shake":
        z = 1.06
        ox, oy = math.sin(lt * 40) * 5, math.cos(lt * 37) * 5
    w, h = CW / z, CH / z
    x0 = min(max((CW - w) / 2 + ox, 0), CW - w)
    y0 = min(max((CH - h) / 2 + oy, 0), CH - h)
    return img.resize((g["OUT_W"], g["OUT_H"]), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))


def install(g):
    global _g
    _g = g
    orig_place, orig_pop = g["place"], g["pop_scale"]

    def place(e, t):
        x, y = orig_place(e, t)
        try:
            at = e.get("at", 0.0)
            en = e.get("enter")
            if en:
                u = g["ease"]((t - at) / 0.55)
                dx, dy = {"left": (-g["CW"] * 0.7, 0), "right": (g["CW"] * 0.7, 0),
                          "up": (0, -g["CH"] * 0.4), "down": (0, g["CH"] * 0.4)}.get(en, (0, 0))
                x += dx * (1 - u)
                y += dy * (1 - u)
            dr = e.get("drift")
            if dr:
                k = max(0.0, t - at)
                x += g["px"](float(dr[0])) * k
                y += g["py"](float(dr[1])) * k
        except Exception:
            pass
        return x, y

    def pop_scale(e, t):
        s = 1.0 if e.get("enter") else orig_pop(e, t)
        p = e.get("pulse")
        if isinstance(p, (int, float)) and not isinstance(p, bool):
            s *= 1 + max(0.0, min(0.3, p)) * math.sin(t * 4)
        return s

    g["place"], g["pop_scale"] = place, pop_scale
    g["draw_figure"], g["render_scene"] = draw_figure, render_scene
    g["CAMERAS"] = tuple(g["CAMERAS"]) + NEW_CAMERAS

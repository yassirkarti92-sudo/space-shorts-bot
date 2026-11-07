"""scenery.py - extra scene parts for vector.py (sky, ground, sea, city, crowd, mountain,
sun, moon, earth, cloud, tree, arrow, icon, particles). draw() gets pixel values on the 540x960 canvas."""
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

CW, CH = 540, 960
PAL = {
    "navy": (22, 25, 36), "slate": (34, 39, 51), "gray": (120, 130, 150),
    "cyan": (77, 208, 225), "mint": (129, 199, 132), "amber": (255, 183, 77),
    "red": (229, 115, 115), "white": (255, 255, 255), "cream": (255, 244, 214),
    "skin": (242, 205, 165), "dark": (30, 30, 40), "purple": (150, 110, 210),
    "brown": (120, 85, 60), "blue": (80, 130, 230),
}
SKIES = {"day": ((70, 150, 230), (190, 225, 250)), "dusk": ((50, 40, 90), (240, 130, 100)),
         "night": ((6, 8, 24), (26, 34, 70)), "storm": ((40, 46, 60), (90, 98, 112)),
         "red": ((60, 14, 24), (220, 80, 60)), "space": ((4, 4, 12), (14, 10, 34))}
GROUNDS = {"grass": ((76, 160, 90), (50, 120, 70)), "desert": ((230, 180, 100), (200, 140, 70)),
           "rock": ((110, 115, 130), (80, 84, 100)), "snow": ((240, 246, 255), (200, 215, 235)),
           "lava": ((70, 30, 30), (255, 100, 40)), "dark": ((40, 44, 60), (24, 26, 38))}
SEAS = {"water": ((30, 110, 170), (20, 80, 140)), "lava": ((255, 120, 40), (200, 60, 30)),
        "ice": ((150, 200, 230), (110, 160, 200))}
ICONS = ("drop", "flame", "bolt", "thermometer", "house", "heart", "warning", "hourglass")
PKINDS = ("rain", "snow", "embers")
TYPES = ("sky", "ground", "sea", "city", "crowd", "mountain", "sun", "moon", "earth", "cloud",
         "tree", "arrow", "icon", "particles")
NEEDS_SIZE = ("ground", "sea", "city", "crowd", "mountain", "sun", "moon", "earth", "cloud",
              "tree", "arrow", "icon")
STATIC = ("sky", "ground", "sea", "city", "particles")  # no pop-in


def check(e):
    k = e.get("type")
    bad = {"sky": ("style", SKIES, "day"), "ground": ("style", GROUNDS, "grass"),
           "sea": ("style", SEAS, "water")}
    if k in bad:
        f, table, dflt = bad[k]
        if e.get(f, dflt) not in table:
            return False, f"unknown {k} {f}"
    if k == "icon" and e.get("icon") not in ICONS:
        return False, "unknown icon"
    if k == "particles" and e.get("kind", "rain") not in PKINDS:
        return False, "unknown particles kind"
    if k == "crowd":
        n = e.get("n", 12)
        if isinstance(n, bool) or not isinstance(n, (int, float)) or not 1 <= n <= 40:
            return False, "crowd n must be 1..40"
    return True, ""


def col(e, dflt):
    return PAL.get(e.get("color", dflt), PAL[dflt])


def glow(img, x, y, r, c, a=150):
    r = int(max(4, r))
    s = r * 2
    lay = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([s - r, s - r, s + r, s + r], fill=tuple(c) + (a,))
    lay = lay.filter(ImageFilter.GaussianBlur(r * 0.5))
    img.paste(lay.convert("RGB"), (int(x - s), int(y - s)), lay.split()[3])


_sky_cache = {}
_r = random.Random(21)
STARS = [(_r.random() * CW, _r.random() * CH * 0.7, _r.uniform(0.8, 2.0)) for _ in range(70)]


def _sky(img, d, e, x, y, w, h, t):
    name = e.get("style", "day")
    if name not in _sky_cache:
        top, bot = SKIES[name]
        im = Image.new("RGB", (CW, CH))
        dd = ImageDraw.Draw(im)
        for yy in range(CH):
            k = min(1.0, yy / (CH * 0.62))
            dd.line([(0, yy), (CW, yy)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
        _sky_cache[name] = im
    img.paste(_sky_cache[name])
    if name in ("night", "space"):
        for i, (sx, sy, r) in enumerate(STARS):
            a = int(110 + 120 * math.sin(t * 2 + i))
            d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 255, 255, max(40, a)))


def _ground(img, d, e, x, y, w, h, t):
    c1, c2 = GROUNDS[e.get("style", "grass")]
    seed = e.get("seed", 1)
    pts = [(xx, y + 9 * math.sin(xx / 55 + seed)) for xx in range(0, CW + 1, 12)]
    d.polygon(pts + [(CW, CH), (0, CH)], fill=c1)
    d.rectangle([0, y + 40, CW, CH], fill=c2)
    if e.get("style") == "lava":
        d.line(pts, fill=(255, 190, 70, 255), width=5)
    elif e.get("style") == "grass":
        d.line(pts, fill=(110, 200, 120, 255), width=5)


def _sea(img, d, e, x, y, w, h, t):
    cols = SEAS[e.get("style", "water")]
    for j, c in enumerate(cols):
        top = y + j * 22
        pts = [(xx, top + 7 * math.sin(xx / 40 + t * 1.8 + j * 2)) for xx in range(0, CW + 1, 10)]
        d.polygon(pts + [(CW, CH), (0, CH)], fill=c)
        d.line(pts, fill=(255, 255, 255, 90), width=3)


def _city(img, d, e, x, y, w, h, t):
    rng = random.Random(e.get("seed", 3))
    for layer, (c, k, n) in enumerate([((30, 36, 56), 0.6, 12), ((22, 26, 42), 0.85, 9), ((14, 16, 28), 1.1, 7)]):
        bw = CW * 1.1 / n
        for i in range(n):
            bh = w * k * rng.uniform(0.5, 1.0)
            x0 = i * bw - 10 + layer * 14
            d.rectangle([x0, y - bh, x0 + bw - 3, y], fill=c)
            for wy in range(int(y - bh + 12), int(y - 8), 20):
                for wx in range(int(x0 + 7), int(x0 + bw - 12), 16):
                    if rng.random() < 0.3:
                        d.rectangle([wx, wy, wx + 6, wy + 9], fill=(255, 200, 90, 210))
    d.rectangle([0, y, CW, y + 6], fill=(14, 16, 28))


def _crowd(img, d, e, x, y, w, h, t):
    n = int(e.get("n", 12))
    rng = random.Random(e.get("seed", 7))
    fh = max(20, h if "h" in e else w * 0.16)
    cols = [PAL[c] for c in ("cyan", "amber", "red", "mint", "purple", "white")]
    for i in sorted(range(n), key=lambda i: i % 2):
        row = i % 2
        cx = x - w / 2 + w * (i + 0.5) / n + rng.uniform(-5, 5)
        H = fh * (1 - 0.2 * row)
        cy = y + row * fh * 0.25 + math.sin(t * 3 + i) * e.get("bob", 0)
        d.rounded_rectangle([cx - H * .17, cy - H * .3, cx + H * .17, cy + H * .45], radius=int(H * .17), fill=cols[i % 6])
        d.ellipse([cx - H * .26, cy - H * .75, cx + H * .26, cy - H * .23], fill=(150, 160, 180))
        for s in (-1, 1):
            d.ellipse([cx + s * H * .09 - 2, cy - H * .52 - 3, cx + s * H * .09 + 2, cy - H * .52 + 3], fill=(235, 252, 255))


def _mountain(img, d, e, x, y, w, h, t):
    c = col(e, "gray")
    hh = max(20, h if "h" in e else w * 0.8)
    d.polygon([(x - w / 2, y + hh / 2), (x, y - hh / 2), (x + w / 2, y + hh / 2)], fill=c)
    d.polygon([(x, y - hh / 2), (x + w / 2, y + hh / 2), (x + w * 0.08, y + hh / 2)], fill=tuple(int(v * .8) for v in c))
    d.polygon([(x, y - hh / 2), (x - w * 0.1, y - hh * 0.25), (x - w * 0.03, y - hh * 0.2), (x + w * 0.04, y - hh * 0.3),
               (x + w * 0.1, y - hh * 0.25)], fill=(245, 250, 255))


def _sun(img, d, e, x, y, w, h, t):
    r = w / 2
    glow(img, x, y, r * 1.8, PAL["amber"], 130)
    for i in range(12):
        a = math.radians(i * 30 + t * 12)
        d.line([(x + r * 1.25 * math.cos(a), y + r * 1.25 * math.sin(a)), (x + r * 1.6 * math.cos(a), y + r * 1.6 * math.sin(a))],
               fill=PAL["amber"] + (230,), width=max(3, int(r * .09)))
    d.ellipse([x - r, y - r, x + r, y + r], fill=PAL["amber"])


def _moon(img, d, e, x, y, w, h, t):
    r = w / 2
    glow(img, x, y, r * 1.6, PAL["cream"], 80)
    d.ellipse([x - r, y - r, x + r, y + r], fill=PAL["cream"])
    for dx, dy, k in ((-.3, -.2, .22), (.25, .15, .3), (-.1, .45, .15)):
        d.ellipse([x + dx * r - k * r, y + dy * r - k * r, x + dx * r + k * r, y + dy * r + k * r], fill=(225, 214, 180))


def _earth(img, d, e, x, y, w, h, t):
    r = int(w / 2)
    if r < 6:
        return
    glow(img, x, y, r * 1.2, PAL["cyan"], 100)
    lay = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=(50, 110, 220, 255))
    rng = random.Random(4)
    for _ in range(6):
        ang = rng.uniform(0, 6.28) + t * 0.2 * e.get("spin", 1)
        lat = rng.uniform(-.6, .6)
        vis = math.cos(ang)
        if vis > 0:
            bx, by, bw = r + r * math.sin(ang) * .85, r + r * lat, r * .35 * vis + 4
            ld.ellipse([bx - bw, by - bw * .8, bx + bw, by + bw * .8], fill=(90, 180, 110, 255))
    mask = Image.new("L", (2 * r, 2 * r), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
    a = ImageChops.multiply(lay.split()[3], mask)
    img.paste(lay.convert("RGB"), (int(x - r), int(y - r)), a)


def _cloud(img, d, e, x, y, w, h, t):
    c = col(e, "white") if "color" in e else (245, 248, 252)
    x += math.sin(t * .5) * 6
    for dx, dy, k in ((-.28, .05, .22), (0, -.1, .3), (.28, .05, .24), (.05, .1, .26)):
        d.ellipse([x + dx * w - k * w, y + dy * w - k * w * .8, x + dx * w + k * w, y + dy * w + k * w * .8], fill=c + (255,))


def _tree(img, d, e, x, y, w, h, t):
    c = col(e, "mint")
    d.rounded_rectangle([x - w * .06, y, x + w * .06, y + w * .5], radius=4, fill=PAL["brown"])
    for dx, dy, k in ((0, -.1, .38), (-.2, .1, .28), (.2, .1, .28)):
        d.ellipse([x + dx * w - k * w, y + dy * w - k * w, x + dx * w + k * w, y + dy * w + k * w], fill=c)


def _arrow(img, d, e, x, y, w, h, t):
    c = col(e, "red")
    a = math.radians(e.get("angle", 0))
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    L, sw, hl, hw = w / 2, w * .06, w * .28, w * .16
    tail = (x - ux * L, y - uy * L)
    neck = (x + ux * (L - hl), y + uy * (L - hl))
    tip = (x + ux * L, y + uy * L)
    d.polygon([(tail[0] + nx * sw, tail[1] + ny * sw), (neck[0] + nx * sw, neck[1] + ny * sw),
               (neck[0] + nx * hw, neck[1] + ny * hw), tip, (neck[0] - nx * hw, neck[1] - ny * hw),
               (neck[0] - nx * sw, neck[1] - ny * sw), (tail[0] - nx * sw, tail[1] - ny * sw)], fill=c)


def _icon(img, d, e, x, y, w, h, t):
    r = w / 2
    k = e["icon"]

    def T(p):
        return [(x + a * r, y + b * r) for a, b in p]

    def E(a, b, c2, d2, f):
        d.ellipse([x + a * r, y + b * r, x + c2 * r, y + d2 * r], fill=f)

    def R(a, b, c2, d2, f, rad=0.0):
        d.rounded_rectangle([x + a * r, y + b * r, x + c2 * r, y + d2 * r], radius=int(rad * r), fill=f)

    if k == "drop":
        c = col(e, "cyan")
        d.polygon(T([(0, -1), (.55, .05), (-.55, .05)]), fill=c)
        E(-.6, -.35, .6, .85, c)
    elif k == "flame":
        d.polygon(T([(0, -1), (.6, .1), (.45, .7), (0, 1), (-.45, .7), (-.6, .1)]), fill=col(e, "red"))
        d.polygon(T([(0, -.2), (.3, .35), (.2, .75), (0, .9), (-.2, .75), (-.3, .35)]), fill=PAL["amber"])
    elif k == "bolt":
        d.polygon(T([(.2, -1), (-.55, .15), (-.05, .15), (-.25, 1), (.55, -.2), (.05, -.2)]), fill=col(e, "amber"))
    elif k == "thermometer":
        R(-.15, -1, .15, .5, PAL["white"], .15)
        E(-.38, .27, .38, 1.03, col(e, "red"))
        R(-.06, -.2, .06, .65, col(e, "red"), .06)
    elif k == "house":
        d.polygon(T([(-1, -.1), (0, -1), (1, -.1)]), fill=col(e, "red"))
        R(-.7, -.1, .7, .9, PAL["cream"])
        R(-.18, .3, .18, .9, PAL["brown"])
    elif k == "heart":
        c = col(e, "red")
        E(-.75, -.75, .15, .15, c)
        E(-.15, -.75, .75, .15, c)
        d.polygon(T([(-.72, -.1), (.72, -.1), (0, .9)]), fill=c)
    elif k == "warning":
        d.polygon(T([(0, -1), (1, .8), (-1, .8)]), fill=col(e, "amber"))
        R(-.07, -.35, .07, .22, PAL["dark"], .05)
        E(-.08, .4, .08, .56, PAL["dark"])
    elif k == "hourglass":
        c = col(e, "cream")
        d.polygon(T([(-.6, -1), (.6, -1), (0, 0)]), fill=c)
        d.polygon(T([(0, 0), (.6, 1), (-.6, 1)]), fill=c)
        R(-.7, -1.1, .7, -.95, PAL["amber"])
        R(-.7, .95, .7, 1.1, PAL["amber"])


def _particles(img, d, e, x, y, w, h, t):
    kind = e.get("kind", "rain")
    rng = random.Random(e.get("seed", 2))
    for i in range(70):
        x0, y0, sp = rng.random() * CW, rng.random() * CH, rng.uniform(.6, 1.4)
        if kind == "rain":
            yy, xx = (y0 + t * 900 * sp) % CH, (x0 - t * 120 * sp) % CW
            d.line([(xx, yy), (xx - 5, yy + 20)], fill=(170, 210, 240, 150), width=2)
        elif kind == "snow":
            yy, xx, r = (y0 + t * 70 * sp) % CH, (x0 + 20 * math.sin(t + i)) % CW, 2 + sp
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(255, 255, 255, 200))
        else:
            yy, xx, r = (y0 - t * 90 * sp) % CH, (x0 + 15 * math.sin(t * 2 + i)) % CW, 1.5 + sp
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(255, 150, 60, 210))


_DRAW = {k: globals()["_" + k] for k in TYPES}


def draw(img, d, e, x, y, w, h, t):
    _DRAW[e["type"]](img, d, e, x, y, w, h, t)

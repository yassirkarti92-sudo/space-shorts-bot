#!/usr/bin/env python3
"""Space Shorts Bot - phase 1 local prototype.

Renders a vertical 1080x1920 pixel-art MP4 with 4 scenes and auto-fit captions.
No network, no API keys. Needs: Pillow, numpy (optional), ffmpeg.

Usage:
    python3 prototype.py                  # writes space_shorts_test.mp4
    python3 prototype.py --selftest       # only checks that captions fit
    python3 prototype.py --out my.mp4
"""
import argparse
import os
import math
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import audio
import scenes

# ---------------- Config ----------------
W, H = 135, 240          # low-res canvas (pixel art)
S = 8                    # upscale factor -> 1080x1920
OUT_W, OUT_H = W * S, H * S
FPS = 24
SCENE_LEN = 6.0          # seconds per scene
SPEED = 1.5              # animation speed multiplier
FADE = 0.3               # scene fade in/out (seconds)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TITLE = "SPACE FACTS"

CAPTION_BOX = (70, 1440, 1010, 1830)   # x0, y0, x1, y1 (hi-res)
CAPTION_PAD = 36
CAPTION_MAX_SIZE = 76
CAPTION_MIN_SIZE = 40

BG = (6, 6, 22)
WHITE = (240, 240, 255)
YELLOW = (255, 214, 10)
ORANGE = (255, 140, 20)

DEFAULT_PLAN = [
    {"scene": "planets", "caption": "Mercury races around the Sun in just 88 days.", "label": "MERCURY: 88 DAYS"},
    {"scene": "sizes", "caption": "Jupiter is so big that about 1,300 Earths could fit inside it.", "label": ""},
    {"scene": "zoom", "caption": "Sunlight takes about 8 minutes to travel to Earth.", "label": "OUR SUN IS A STAR"},
    {"scene": "rocket", "caption": "To orbit Earth, a rocket must reach about 28,000 km/h.", "label": "28,000 KM/H"},
]


# ---------------- Captions (auto-fit) ----------------
def wrap(text, font, max_w):
    """Greedy word wrap. Returns None if a single word is wider than max_w."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if font.getlength(trial) <= max_w:
            cur = trial
        else:
            if not cur or font.getlength(word) > max_w:
                return None
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_caption(text):
    """Largest font size where the wrapped text fits inside the caption box."""
    box_w = CAPTION_BOX[2] - CAPTION_BOX[0] - 2 * CAPTION_PAD
    box_h = CAPTION_BOX[3] - CAPTION_BOX[1] - 2 * CAPTION_PAD
    for size in range(CAPTION_MAX_SIZE, CAPTION_MIN_SIZE - 1, -2):
        font = ImageFont.truetype(FONT_PATH, size)
        lines = wrap(text, font, box_w)
        if lines is None:
            continue
        lh = int(size * 1.28)
        if len(lines) * lh <= box_h:
            return font, lines, lh
    raise ValueError(f"caption does not fit even at {CAPTION_MIN_SIZE}px: {text!r}")


def selftest():
    for c in [p["caption"] for p in DEFAULT_PLAN]:
        font, lines, lh = fit_caption(c)
        print(f"OK size={font.size:>2} lines={len(lines)}  {c[:48]}")
    print("all captions fit")


# ---------------- Helpers ----------------
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def disc(d, x, y, r, fill):
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


_rng = random.Random(7)
STARS = [(_rng.randrange(W), _rng.randrange(H), _rng.random() * 6.28) for _ in range(90)]
SCROLL_STARS = [
    (_rng.randrange(W), _rng.randrange(H), _rng.choice([30, 60, 110])) for _ in range(70)
]


def draw_twinkle(d, t):
    for x, y, ph in STARS:
        b = 0.55 + 0.45 * math.sin(t * 2.2 + ph)
        v = int(70 + 150 * b)
        d.point((x, y), fill=(v, v, min(255, v + 20)))


# ---------------- Scene 1: planet orbit ----------------
PLANETS = [  # orbit radius, planet radius, color, period (s)
    (16, 2, (200, 200, 205), 2.0),   # Mercury (fast!)
    (27, 2, (230, 180, 110), 5.0),   # Venus
    (39, 2, (70, 130, 255), 8.0),    # Earth
    (51, 2, (220, 90, 55), 13.0),    # Mars
]


def scene_planets(d, t):
    cx, cy = 67, 105
    draw_twinkle(d, t)
    for orbit, _, _, _ in PLANETS:
        for k in range(0, 360, 6):
            a = math.radians(k)
            d.point((int(cx + orbit * math.cos(a)), int(cy + orbit * math.sin(a))),
                    fill=(40, 44, 80))
    disc(d, cx, cy, 9, (120, 60, 10))
    disc(d, cx, cy, 7, ORANGE)
    disc(d, cx, cy, 5, YELLOW)
    for orbit, r, col, period in PLANETS:
        a = 2 * math.pi * (t / period) - 1.2
        disc(d, int(cx + orbit * math.cos(a)), int(cy + orbit * math.sin(a)), r, col)
    return [("MERCURY: 88 DAYS", 67, 168)]


# ---------------- Scene 2: size comparison ----------------
JUP_BANDS = [(222, 190, 150), (190, 130, 90), (235, 210, 175), (170, 105, 70),
             (225, 195, 155), (185, 120, 85), (232, 205, 165)]


def scene_sizes(d, t):
    draw_twinkle(d, t)
    cx, cy = 67, 88
    R = int(33 * ease(t / 1.4))
    if R >= 2:
        size = 2 * R + 1
        layer = Image.new("RGB", (size, size))
        ld = ImageDraw.Draw(layer)
        band_h = size / len(JUP_BANDS)
        for i, col in enumerate(JUP_BANDS):
            ld.rectangle([0, int(i * band_h), size, int((i + 1) * band_h) + 1], fill=col)
        spot_x, spot_y = int(R * 1.3), int(R * 1.35)
        ld.ellipse([spot_x - 4, spot_y - 2, spot_x + 4, spot_y + 2], fill=(200, 70, 40))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        d._image.paste(layer, (cx - R, cy - R), mask)
    labels = []
    if t > 1.4:
        labels.append(("JUPITER", cx, cy - 38))
    if t > 2.0:
        ey = 160 + int(round(math.sin(t * 3) * 1))
        disc(d, cx, ey, 3, (70, 130, 255))
        d.point((cx - 1, ey - 1), fill=(60, 190, 90))
        d.point((cx + 1, ey + 1), fill=(60, 190, 90))
        labels.append(("EARTH", cx, ey + 12))
    return labels


# ---------------- Scene 3: star zoom ----------------
def scene_zoom(d, t):
    cx, cy = 67, 100
    n = 80
    for i in range(n):
        rnd = random.Random(i * 97 + 3)
        ang = rnd.random() * 6.2832
        p = (t * 0.45 + i / n) % 1.0
        r1 = (p ** 2.2) * 110
        r2 = ((p + 0.05) ** 2.2) * 110
        v = int(60 + 190 * p)
        d.line([(int(cx + r1 * math.cos(ang)), int(cy + r1 * math.sin(ang))),
                (int(cx + r2 * math.cos(ang)), int(cy + r2 * math.sin(ang)))],
               fill=(v, v, min(255, v + 25)))
    R = int(2 + 12 * ease(t / 6.0))
    disc(d, cx, cy, R + 4, (60, 30, 10))
    disc(d, cx, cy, R + 2, (140, 70, 10))
    disc(d, cx, cy, R, ORANGE)
    disc(d, cx, cy, max(1, R - 2), YELLOW)
    return [("OUR SUN IS A STAR", 67, 160)]


# ---------------- Scene 4: rocket ----------------
ROCKET = [
    ".....R.....",
    "....RRR....",
    "...RRRRR...",
    "...WWWWW...",
    "..WWWWWWW..",
    "..WWBBBWW..",
    "..WBBBBBW..",
    "..WWBBBWW..",
    "..WWWWWWW..",
    "..WWWWWWW..",
    "..WWWWWWW..",
    "..RRRRRRR..",
    "..WWWWWWW..",
    ".GWWWWWWWG.",
    "GGWWWWWWWGG",
    "GG.WWWWW.GG",
    "RR..GGG..RR",
]
ROCKET_COL = {"R": (220, 50, 50), "W": (235, 235, 245), "B": (60, 170, 255),
              "G": (130, 130, 150)}


def scene_rocket(d, t):
    for x, y0, spd in SCROLL_STARS:
        y = int((y0 + t * spd) % H)
        v = 90 + spd
        d.point((x, y), fill=(v, v, min(255, v + 20)))
        if spd >= 60:
            d.point((x, (y - 1) % H), fill=(v // 2, v // 2, v // 2))
    top = 175 + 50 * ease(t / 5.0)
    d.ellipse([67 - 132, top - 2, 67 + 132, top + 262], fill=(70, 130, 225))
    d.ellipse([67 - 130, top, 67 + 130, top + 260], fill=(20, 55, 140))
    k = 2  # sprite scale
    ry = int(130 - 50 * ease(t / 2.0))
    shake = int(round(math.sin(t * 40) * 0.6))
    rx = 67 - 11 + shake
    fl = (7 + int(4 * abs(math.sin(t * 25)))) * k
    base = ry + 17 * k
    d.polygon([(rx + 6, base), (rx + 16, base), (rx + 11, base + fl)], fill=ORANGE)
    d.polygon([(rx + 8, base), (rx + 14, base), (rx + 11, base + fl - 6)], fill=YELLOW)
    for j, row in enumerate(ROCKET):
        for i, ch in enumerate(row):
            if ch != ".":
                d.rectangle([rx + i * k, ry + j * k, rx + i * k + k - 1, ry + j * k + k - 1],
                            fill=ROCKET_COL[ch])
    return [("28,000 KM/H", 67, 52)]


SCENES = {"planets": scene_planets, "sizes": scene_sizes, "zoom": scene_zoom, "rocket": scene_rocket}


# ---------------- Frame composition ----------------
def compose(t, fonts_cache, plan):
    idx = min(int(t // SCENE_LEN), len(plan) - 1)
    lt = t - idx * SCENE_LEN

    low = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(low)
    spec = plan[idx].get("spec")
    if spec and scenes.check_scene(spec)[0]:
        labels = scenes.draw_scene(d, spec, lt * SPEED)
    else:
        name = plan[idx]["scene"] if plan[idx]["scene"] in SCENES else "zoom"
        labels = SCENES[name](d, lt * SPEED)
    if plan[idx].get("label") and plan[idx]["scene"] != "sizes" and labels:
        labels = [(plan[idx]["label"].upper(),) + tuple(labels[0][1:])]

    fade = min(1.0, lt / FADE, (SCENE_LEN - lt) / FADE)
    if fade < 1.0:
        low = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), low, max(0.0, fade))

    big = low.resize((OUT_W, OUT_H), Image.NEAREST).convert("RGBA")
    ov = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    title_font = fonts_cache.setdefault("title", ImageFont.truetype(FONT_PATH, 84))
    od.text((OUT_W // 2, 190), TITLE, font=title_font, fill=YELLOW + (255,),
            anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0, 255))

    label_font = fonts_cache.setdefault("label", ImageFont.truetype(FONT_PATH, 42))
    for text, lx, ly in labels:
        od.text((lx * S, ly * S), text, font=label_font, fill=WHITE + (255,),
                anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 255))

    ca = min(1.0, max(0.0, (lt - 0.3) / 0.4), max(0.0, (SCENE_LEN - 0.3 - lt) / 0.4))
    if ca > 0:
        if idx not in fonts_cache:
            fonts_cache[idx] = fit_caption(plan[idx]["caption"])
        font, lines, lh = fonts_cache[idx]
        x0, y0, x1, y1 = CAPTION_BOX
        od.rounded_rectangle(CAPTION_BOX, radius=36, fill=(8, 8, 30, int(185 * ca)),
                             outline=YELLOW + (int(255 * ca),), width=5)
        block_h = len(lines) * lh
        ty = y0 + (y1 - y0 - block_h) // 2 + lh // 2
        for ln in lines:
            od.text(((x0 + x1) // 2, ty), ln, font=font,
                    fill=(255, 255, 255, int(255 * ca)), anchor="mm",
                    stroke_width=4, stroke_fill=(0, 0, 0, int(255 * ca)))
            ty += lh

    return Image.alpha_composite(big, ov).convert("RGB")


def render(out_path, plan=None):
    plan = plan or DEFAULT_PLAN
    total = len(plan) * SCENE_LEN
    wav = out_path + ".wav"
    import voice
    clips = voice.make_clips(plan, os.path.dirname(os.path.abspath(out_path)), SCENE_LEN - 0.8)
    audio.make_audio(wav, plan, SCENE_LEN, seed=sum(map(ord, plan[0]["caption"])), voices=clips)
    n_frames = int(total * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-preset", "veryfast", "-c:a", "aac", "-b:a", "160k", "-shortest",
           "-movflags", "+faststart", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cache = {}
    for i in range(n_frames):
        proc.stdin.write(compose(i / FPS, cache, plan).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    os.remove(wav)
    for c in clips or []:
        os.remove(c)
    print(f"wrote {out_path} ({total:.0f}s, {n_frames} frames)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="space_shorts_test.mp4")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    selftest()
    if not args.selftest:
        render(args.out)

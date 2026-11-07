#!/usr/bin/env python3
"""render2.py - story-style vertical video: flat 2D scenes, hard cuts, lower-third captions."""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import audio
import vector

FPS = 24
OUT_W, OUT_H = vector.OUT_W, vector.OUT_H
LEAD = 0.45            # narration starts this long after the video starts
TAIL = 1.5             # silence at the end
MIN_SCENE = 1.8
WORDS_PER_SEC = 2.4    # used only when there is no real narration length

CAP_REGION = (0, 1230, OUT_W, 1790)
CAP_MAX_W = 940
WHITE, CYAN, DARK = (255, 255, 255), (77, 208, 225), (10, 12, 20)


def fit_caption(text):
    """Return (font, lines, line_height). A word written as *word* is highlighted."""
    toks = []
    for w in text.split():
        hl = len(w) > 2 and w.startswith("*") and w.endswith("*")
        toks.append((w.strip("*") if hl else w, hl))
    for size in range(78, 45, -2):
        f = ImageFont.truetype(vector.FONT, size)
        sp = f.getlength(" ")
        lines, cur, cw = [], [], 0.0
        ok = True
        for w, hl in toks:
            wl = f.getlength(w)
            if wl > CAP_MAX_W:
                ok = False
                break
            if cur and cw + sp + wl > CAP_MAX_W:
                lines.append(cur)
                cur, cw = [], 0.0
            cw += (sp if cur else 0) + wl
            cur.append((w, hl))
        if not ok:
            continue
        if cur:
            lines.append(cur)
        if len(lines) <= 3:
            return f, lines, int(size * 1.3)
    raise ValueError(f"caption too long: {text!r}")


def draw_caption(img, layout, alpha):
    f, lines, lh = layout
    a = int(255 * alpha)
    region = img.crop(CAP_REGION).convert("RGBA")
    ov = Image.new("RGBA", region.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    sp = f.getlength(" ")
    y = (region.height - len(lines) * lh) / 2 + lh / 2
    for line in lines:
        total = sum(f.getlength(w) for w, _ in line) + sp * (len(line) - 1)
        x = (region.width - total) / 2
        for w, hl in line:
            od.text((x, y), w, font=f, fill=(CYAN if hl else WHITE) + (a,), anchor="lm",
                    stroke_width=7, stroke_fill=DARK + (a,))
            x += f.getlength(w) + sp
        y += lh
    img.paste(Image.alpha_composite(region, ov).convert("RGB"), CAP_REGION[:2])


def scene_durations(plan, narration_secs):
    """Share the narration time between scenes by word count."""
    words = [max(1, len(str(p.get("narration") or p.get("caption", "")).split())) for p in plan]
    total = sum(words)
    speech = narration_secs if narration_secs else total / WORDS_PER_SEC
    durs = [max(MIN_SCENE, speech * w / total) for w in words]
    durs[0] += LEAD
    durs[-1] += TAIL
    return durs


def render(out_path, plan, narration=None, narration_secs=None):
    n = len(plan)
    durs = scene_durations(plan, narration_secs)
    starts = [sum(durs[:i]) for i in range(n)]
    total = sum(durs)

    specs = []
    for i, p in enumerate(plan):
        spec = p.get("spec")
        ok, why = vector.check_scene(spec) if spec else (False, "no spec")
        if not ok:
            print(f"scene {i + 1} rejected ({why}); using fallback scene")
            spec = vector.FALLBACK_SPEC
        specs.append(spec)
    layouts = [fit_caption(p["caption"]) for p in plan]

    wav = out_path + ".wav"
    audio.make_audio(wav, plan, durs[0], seed=sum(map(ord, plan[0]["caption"])),
                     narration=narration, speed=1.0, durs=durs)

    n_frames = int(total * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-preset", "veryfast", "-c:a", "aac", "-b:a", "160k", "-shortest",
           "-movflags", "+faststart", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    idx = 0
    for fi in range(n_frames):
        t = fi / FPS
        while idx < n - 1 and t >= starts[idx + 1]:
            idx += 1
        lt = t - starts[idx]
        img = vector.render_scene(specs[idx], lt, durs[idx])
        draw_caption(img, layouts[idx], min(1.0, lt / 0.15))
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    os.remove(wav)
    print(f"wrote {out_path} ({total:.0f}s, {n_frames} frames)")

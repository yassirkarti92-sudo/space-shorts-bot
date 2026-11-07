"""Synthesized ambient soundtrack + sound effects + narration: no downloads, no copyright."""
import math
import random
import wave

import numpy as np

SR = 44100
A = 220.0
PROGS = [[0, -4, -2, -7], [0, 5, 3, -2], [0, -5, 3, -2]]   # chord roots (semitones)
CHORD = [0, 7, 12, 14, 19]                                  # open, airy voicing
PENTA = [0, 3, 5, 7, 10, 12, 15, 19]
SFX_TYPES = ("whoosh", "rumble", "swell", "boom")           # "none" = no effect


def hz(semi):
    return A * 2 ** (semi / 12)


def lowpass(x, n):
    return np.convolve(x, np.ones(n) / n, mode="same")


def noise(n, width, rng):
    x = lowpass(rng.standard_normal(n), width)
    return x / (x.std() + 1e-9)


def read_wav(path):
    with wave.open(path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    return x


def sfx_signal(kind, ts, nrng):
    """Effect signal for time array ts (seconds since the effect started)."""
    L = len(ts)
    if kind == "whoosh":    # rising rush, about 1.8 s
        env = np.clip(ts / 1.4, 0, 1) ** 2 * np.clip((1.8 - ts) / 0.4, 0, 1)
        return noise(L, 25, nrng) * env * 0.22
    if kind == "rumble":    # engine rumble until the scene ends
        return noise(L, 160, nrng) * np.minimum(1.0, ts / 1.5) * 0.30
    if kind == "swell":     # sub swell, about 2.6 s
        x = np.clip(ts / 1.4, 0, 1)
        return np.sin(2 * np.pi * (45 + 12 * x) * ts) * np.sin(np.pi * np.clip(ts / 2.6, 0, 1)) * 0.22
    if kind == "boom":      # falling sub tone + low noise burst
        phase = 2 * np.pi * (35 * ts + 70 * (1 - np.exp(-6 * ts)) / 6)
        return np.sin(phase) * np.exp(-2.2 * ts) * 0.7 + noise(L, 60, nrng) * np.exp(-5 * ts) * 0.35
    return np.zeros(L)


def scene_sfx(scene):
    """List of (kind, seconds). Returns None when the scene has no sfx field."""
    if "sfx" not in scene:
        return None
    raw = scene["sfx"]
    if isinstance(raw, str):
        raw = [raw]
    out = []
    for e in raw or []:
        if isinstance(e, str):
            e = {"type": e, "at": 0}
        if isinstance(e, dict) and e.get("type") in SFX_TYPES:
            at = e.get("at", 0)
            if isinstance(at, (int, float)) and 0 <= at <= 12:
                out.append((e["type"], float(at)))
    return out


def make_audio(path, plan, scene_len, seed=0, voices=None, narration=None, speed=1.5, durs=None):
    """durs: list of scene lengths in seconds (new story style). Without it, every scene lasts
    scene_len and the sound is the same as before.
    narration: path to ONE wav for the whole video. voices: old per-scene wavs.
    speed: divides sfx 'at' times (old scenes use animation seconds, new ones pass 1.0)."""
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    n = len(plan)
    story = durs is not None
    if durs is None:
        durs = [scene_len] * n
    starts = [sum(durs[:i]) for i in range(n)]
    total = sum(durs)
    N = int(total * SR)
    t = np.arange(N) / SR
    out = np.zeros(N)
    prog = rng.choice(PROGS)

    block = 8.0 if story else scene_len          # music changes chord once per block
    nb = int(math.ceil(total / block)) if story else max(1, int(round(total / block)))
    for i in range(nb):
        root = prog[i % len(prog)]
        tt = t - (i * block - 0.5)
        dur = block + 1.0
        env = np.where((tt >= 0) & (tt <= dur),
                       np.minimum(np.minimum(tt, 1.0), np.minimum(dur - tt, 1.0)), 0.0)
        trem = 0.8 + 0.2 * np.sin(2 * np.pi * 0.25 * t + i)
        for semi in CHORD:
            f = hz(root + semi - 12)
            out += 0.045 * env * trem * (np.sin(2 * np.pi * f * t)
                                         + 0.5 * np.sin(2 * np.pi * f * 1.004 * t))

    for i in range(n):
        s0 = int(starts[i] * SR)
        L = min(int(durs[i] * SR), N - s0)
        if L <= 0:
            continue
        ts = np.arange(L) / SR
        effects = scene_sfx(plan[i])
        if effects is not None:
            for kind, at in effects:
                start = int(at / speed * SR)
                if start >= L:
                    continue
                Lx = (L - start) if kind == "rumble" else int(3.0 * SR)
                Lx = min(Lx, N - (s0 + start))
                if Lx <= 0:
                    continue
                out[s0 + start:s0 + start + Lx] += sfx_signal(kind, np.arange(Lx) / SR, nrng)
        else:
            kind = plan[i].get("scene")
            if kind == "zoom":
                out[s0:s0 + L] += noise(L, 25, nrng) * (ts / durs[i]) ** 2 * 0.22
            elif kind == "rocket":
                out[s0:s0 + L] += noise(L, 160, nrng) * np.minimum(1.0, ts / 1.5) * 0.30
            elif kind == "sizes":
                x = np.clip(ts / 1.4, 0, 1)
                out[s0:s0 + L] += (np.sin(2 * np.pi * (45 + 12 * x) * ts)
                                   * np.sin(np.pi * np.clip(ts / 2.6, 0, 1)) * 0.22)

    k = 0.4
    while k < total - 1.3:  # sparkle notes
        if rng.random() < 0.7:
            i = min(int(k // block), nb - 1)
            f = hz(prog[i % len(prog)] + rng.choice(PENTA) + 12)
            a = int(k * SR)
            m = int(1.2 * SR)
            tau = np.arange(m) / SR
            out[a:a + m] += 0.05 * np.sin(2 * np.pi * f * tau) * np.exp(-5 * tau)
        k += 0.6

    have_voice = bool(voices) or narration is not None
    out *= (0.45 if have_voice else 0.8) / (np.abs(out).max() + 1e-9)

    if have_voice:  # narration on top, music ducked while talking
        v = np.zeros(N)
        if narration is not None:
            clip = read_wav(narration)
            a = int(0.45 * SR)
            m = max(0, min(len(clip), N - a))
            v[a:a + m] += clip[:m]
        else:
            for i, p in enumerate(voices):
                clip = read_wav(p)
                a = int((starts[i] + 0.45) * SR)
                m = max(0, min(len(clip), N - a, int((durs[i] - 0.8) * SR)))
                v[a:a + m] += clip[:m]
        mask = lowpass((np.abs(v) > 0.02).astype(float), SR // 4)
        out *= 1 - 0.6 * np.clip(mask * 1.5, 0, 1)
        out += v * 0.85 / (np.abs(v).max() + 1e-9)
        out /= max(1.0, np.abs(out).max() / 0.95)

    out *= np.minimum(1.0, t / 0.3) * np.minimum(1.0, (t[-1] - t) / 0.6)
    pcm = (np.repeat(out[:, None], 2, axis=1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

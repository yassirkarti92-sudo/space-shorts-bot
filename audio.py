"""Synthesized ambient space soundtrack: no downloads, no copyright."""
import random
import wave

import numpy as np

SR = 44100
A = 220.0
PROGS = [[0, -4, -2, -7], [0, 5, 3, -2], [0, -5, 3, -2]]   # chord roots (semitones)
CHORD = [0, 7, 12, 14, 19]                                  # open, airy voicing
PENTA = [0, 3, 5, 7, 10, 12, 15, 19]


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


def make_audio(path, plan, scene_len, seed=0, voices=None):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    n = len(plan)
    N = int(n * scene_len * SR)
    t = np.arange(N) / SR
    out = np.zeros(N)
    prog = rng.choice(PROGS)

    for i in range(n):
        root = prog[i % len(prog)]
        tt = t - (i * scene_len - 0.5)
        dur = scene_len + 1.0
        env = np.where((tt >= 0) & (tt <= dur),
                       np.minimum(np.minimum(tt, 1.0), np.minimum(dur - tt, 1.0)), 0.0)
        trem = 0.8 + 0.2 * np.sin(2 * np.pi * 0.25 * t + i)
        for semi in CHORD:
            f = hz(root + semi - 12)
            out += 0.045 * env * trem * (np.sin(2 * np.pi * f * t)
                                         + 0.5 * np.sin(2 * np.pi * f * 1.004 * t))

        s0 = int(i * scene_len * SR)
        L = int(scene_len * SR)
        ts = np.arange(L) / SR
        kind = plan[i]["scene"]
        if kind == "zoom":      # rising whoosh
            out[s0:s0 + L] += noise(L, 25, nrng) * (ts / scene_len) ** 2 * 0.22
        elif kind == "rocket":  # engine rumble
            amp = np.minimum(1.0, ts / 1.5) * 0.30
            out[s0:s0 + L] += noise(L, 160, nrng) * amp
        elif kind == "sizes":   # sub swell while Jupiter grows
            x = np.clip(ts / 1.4, 0, 1)
            sw = np.sin(2 * np.pi * (45 + 12 * x) * ts) * np.sin(np.pi * np.clip(ts / 2.6, 0, 1)) * 0.22
            out[s0:s0 + L] += sw

    k = 0.4
    while k < n * scene_len - 1.3:  # sparkle notes
        if rng.random() < 0.7:
            i = min(int(k // scene_len), n - 1)
            f = hz(prog[i % len(prog)] + rng.choice(PENTA) + 12)
            a = int(k * SR)
            m = int(1.2 * SR)
            tau = np.arange(m) / SR
            out[a:a + m] += 0.05 * np.sin(2 * np.pi * f * tau) * np.exp(-5 * tau)
        k += 0.6

    out *= (0.45 if voices else 0.8) / (np.abs(out).max() + 1e-9)
    if voices:  # narration on top, music ducked while talking
        v = np.zeros(N)
        for i, p in enumerate(voices):
            clip = read_wav(p)
            a = int((i * scene_len + 0.45) * SR)
            m = max(0, min(len(clip), N - a, int((scene_len - 0.8) * SR)))
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

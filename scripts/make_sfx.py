"""Write small original sound effects into a project (16-bit PCM WAV).

Everything is synthesised here, so the files carry no third-party rights:

  creak.wav      wooden creak for a rocking prop (~0.3 s)
  room_tone.wav  low office room tone for ``motion_plan.audio_bed`` (4 s, loops)
  pop.wav        soft comic pop for an appearing symbol (~0.12 s)

Usage: python scripts/make_sfx.py <project> [--out audio/sfx]
"""
import argparse
import math
import random
import struct
import wave
from pathlib import Path

RATE = 48000


def _write(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max(1e-9, max(abs(v) for v in samples))
    scale = 0.89 / peak if peak > 0.89 else 1.0
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v * scale)) * 32767)) for v in samples))


def _one_pole(samples, cutoff, high=False):
    a = math.exp(-2 * math.pi * cutoff / RATE)
    out, low = [], 0.0
    for value in samples:
        low = (1 - a) * value + a * low
        out.append(value - low if high else low)
    return out


def creak(seed=7, duration=0.32):
    rng = random.Random(seed)
    n = int(duration * RATE)
    out = [0.0] * n
    t = 0.0
    while t < duration:
        rate = 70 - 40 * (t / duration) + rng.gauss(0, 6)
        start = int(t * RATE)
        gain = 0.6 + 0.4 * rng.random()
        for k in range(int(0.006 * RATE)):
            if start + k >= n:
                break
            env = math.exp(-k / (0.0015 * RATE))
            out[start + k] += gain * env * (math.sin(2 * math.pi * 850 * k / RATE) + 0.6 * math.sin(2 * math.pi * 1750 * k / RATE))
        t += 1 / max(rate, 15)
    out = _one_pole(_one_pole(out, 3200), 400, high=True)
    return [v * math.sin(math.pi * i / n) ** 0.6 * 0.5 for i, v in enumerate(out)]


def room_tone(seed=11, duration=4.0, level_db=-28):
    rng = random.Random(seed)
    n = int(duration * RATE)
    noise = _one_pole(_one_pole([rng.gauss(0, 1) for _ in range(n)], 1800), 60, high=True)
    rms = math.sqrt(sum(v * v for v in noise) / n)
    gain = 10 ** (level_db / 20) / rms
    fade = int(0.05 * RATE)  # short crossfade so the loop point does not click
    out = [v * gain for v in noise]
    for i in range(fade):
        w = i / fade
        out[i] = out[i] * w + out[n - fade + i] * (1 - w)
    return out[: n - fade]


def pop(duration=0.12):
    n = int(duration * RATE)
    return [0.6 * math.exp(-i / (0.025 * RATE)) * math.sin(2 * math.pi * (900 - 500 * i / n) * i / RATE) for i in range(n)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--out", default="audio/sfx", help="Folder inside the project")
    args = parser.parse_args(argv)
    folder = args.project.resolve() / args.out
    written = []
    for name, samples in (("creak.wav", creak()), ("room_tone.wav", room_tone()), ("pop.wav", pop())):
        _write(folder / name, samples)
        written.append(str(Path(args.out) / name))
    print("\n".join(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

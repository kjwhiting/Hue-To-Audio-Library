import random
from pathlib import Path
from typing import Optional

from src.synth import SAMPLE_RATE_DEFAULT
from src.composer import render_code_bytes, write_wav, DEFAULT_BPM, SAMPLE_RATE_DEFAULT, VOLUME_MIN, VOLUME_MAX
from tests.demo_composer import compose_demo_bytes

def compose_demo_bytes(
    bpm: int = DEFAULT_BPM,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
    rng: Optional[random.Random] = None,
) -> bytes:
    """
    Build a demo that alternates NOTE codes (7..13) with mirrored REST codes (6..0)
    for each voice. Deterministic when rng is seeded.
    """
    if rng is None:
        rng = random.Random()

    buf = bytearray()
    for note_code in range(1, 20, 1):
        loud = rng.uniform(VOLUME_MIN, VOLUME_MAX)
        buf += render_code_bytes(note_code/20,  bpm, sample_rate, loud)
        # buf += render_code_bytes(rest_code,  bpm, sample_rate, loudness=0.0)
    return bytes(buf)

def sample(
    bpm = DEFAULT_BPM,
    sample_rate = SAMPLE_RATE_DEFAULT,
    seed=42,
):
    rng = random.Random(seed) if seed is not None else None
    pcm = compose_demo_bytes(bpm=bpm, sample_rate=sample_rate, rng=rng)
    out = write_wav(None, pcm, sample_rate)
    print(f"Wrote {out.resolve()} @ {bpm} BPM, sr={sample_rate}")
    return out

if __name__ == "__main__":
    sample()
    print("No image specified or --demo provided; rendering built-in demo …")
    pcm = compose_demo_bytes(DEFAULT_BPM, SAMPLE_RATE_DEFAULT)
    out = write_wav(None, pcm, SAMPLE_RATE_DEFAULT)
    print(f"Wrote {out.resolve()}  (BPM={DEFAULT_BPM}, SR={SAMPLE_RATE_DEFAULT})")
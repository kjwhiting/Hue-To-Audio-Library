"""
Composer: builds playable note buffers using synth.py.

Public testable surface:
- beats_to_seconds(beats, bpm)
- duration_code_to_seconds(code, bpm)
- compose_demo_bytes(bpm=120, sample_rate=44100, rng=None) -> bytes
- write_wav(path, pcm_bytes, sample_rate)
- sample(...)  # local audition/demo writer
"""

from __future__ import annotations

import random
import wave
from array import array
from pathlib import Path
from typing import Mapping, Optional

from src.synth import synthesize_note, SAMPLE_RATE_DEFAULT, ALLOWED_VOICES

# ===== CONFIG / CONSTANTS (EDIT HERE) =====
DEFAULT_BPM = 120
TEST_FREQUENCY_HZ = 440.0       # A4, safely within C2..C6
VOLUME_MIN = 0.35               # audible but safe (synth has extra headroom)
VOLUME_MAX = 0.95
INTER_NOTE_GAP_S = 0.06         # brief silence between notes
NOTE_CODES = (1, 2, 3, 4, 5, 6) # 0 = rest not used in this demo

_CODE_TO_BEATS: Mapping[int, float] = {
    1: 4.0,    # whole
    2: 1.0,    # quarter
    3: 0.5,    # eighth
    4: 0.25,   # sixteenth
    5: 0.125,  # thirtysecond
    6: 0.0625, # sixtyfourth
}


# ===== PURE HELPERS =====
def beats_to_seconds(beats: float, bpm: int) -> float:
    """Convert beats to seconds; raises on non-positive BPM."""
    if bpm <= 0:
        raise ValueError("BPM must be > 0")
    return (60.0 / bpm) * beats


def duration_code_to_seconds(code: int, bpm: int) -> float:
    """Map duration code 1..6 to seconds at BPM. Code 0 (rest) not used here."""
    if code not in _CODE_TO_BEATS:
        raise ValueError(f"Unsupported duration code: {code}")
    return beats_to_seconds(_CODE_TO_BEATS[code], bpm)


def _silence_pcm(frames: int) -> bytes:
    """Return PCM16 mono silence for the requested number of frames."""
    a = array("h", [0] * max(0, frames))
    return a.tobytes()


# ===== TESTABLE CORE =====
def compose_demo_bytes(
    bpm: int = DEFAULT_BPM,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
    rng: Optional[random.Random] = None,
) -> bytes:
    """
    Create a PCM buffer that plays each available voice at each duration code (1..6),
    using TEST_FREQUENCY_HZ and randomized loudness per note.

    Deterministic when 'rng' is a seeded random.Random.
    """
    if rng is None:
        rng = random.Random()  # non-deterministic default

    buf = bytearray()
    gap_frames = int(round(INTER_NOTE_GAP_S * sample_rate))
    gap_bytes = _silence_pcm(gap_frames)

    for voice in sorted(ALLOWED_VOICES):  # stable iteration
        for code in NOTE_CODES:
            dur_s = duration_code_to_seconds(code, bpm)
            loud = rng.uniform(VOLUME_MIN, VOLUME_MAX)
            note = synthesize_note(
                freq_hz=TEST_FREQUENCY_HZ,
                duration_s=dur_s,
                loudness=loud,
                voice=voice,
                sample_rate=sample_rate,
            )
            buf += note
            buf += gap_bytes

    return bytes(buf)


# ===== IO UTILITY =====
def write_wav(path: str | Path, pcm_bytes: bytes, sample_rate: int) -> Path:
    """Write PCM16 mono to a WAV file."""
    p = Path(path)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return p


# ===== LOCAL AUDITION =====
def sample(
    output_path: str | Path = "composer_sample.wav",
    bpm: int = DEFAULT_BPM,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
    seed: Optional[int] = 42,  # deterministic by default for reproducibility
) -> Path:
    """
    Write a demo WAV that plays each voice across duration codes with varied loudness.
    """
    rng = random.Random(seed) if seed is not None else None
    pcm = compose_demo_bytes(bpm=bpm, sample_rate=sample_rate, rng=rng)
    out = write_wav(output_path, pcm, sample_rate)
    print(f"Wrote {out.resolve()} @ {bpm} BPM, sr={sample_rate}")
    return out


# if __name__ == "__main__":
#     sample()

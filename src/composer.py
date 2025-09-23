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

DEFAULT_BPM = 120
TEST_FREQUENCY_HZ = 440.0
VOLUME_MIN = 0.35
VOLUME_MAX = 0.95
NOTE_CODES = (7, 8, 9, 10, 11, 12, 13)  # notes
REST_CODES = (0, 1, 2, 3, 4, 5, 6)      # rests (silence)

# Beats relative to quarter note (quarter=1.0 beat)
REST_CODE_TO_BEATS: Mapping[int, float] = {
    0: 1 / 64,  # 0.0625
    1: 1 / 32,  # 0.125
    2: 1 / 16,  # 0.25
    3: 1 / 8,   # 0.5
    4: 1 / 4,   # 1.0
    5: 1 / 2,   # 2.0
    6: 1,       # 4.0
}
NOTE_CODE_TO_BEATS: Mapping[int, float] = {
    7: 1,       # whole       = 4.0 beats
    8: 1 / 2,   # half        = 2.0 beats
    9: 1 / 4,   # quarter     = 1.0 beat
    10: 1 / 8,  # eighth      = 0.5
    11: 1 / 16, # sixteenth   = 0.25
    12: 1 / 32, # thirtysecond= 0.125
    13: 1 / 64, # sixtyfourth = 0.0625
}

def beats_to_seconds(beats: float, bpm: int) -> float:
    if bpm <= 0:
        raise ValueError("BPM must be > 0")
    return (60.0 / bpm) * beats * 4.0  # convert "note fraction" to beats (whole=4 beats)


def code_to_seconds(code: int, bpm: int) -> float:
    if code in REST_CODE_TO_BEATS:
        return beats_to_seconds(REST_CODE_TO_BEATS[code], bpm)
    if code in NOTE_CODE_TO_BEATS:
        return beats_to_seconds(NOTE_CODE_TO_BEATS[code], bpm)
    raise ValueError(f"Unsupported duration/rest code: {code}")


def _silence_pcm(frames: int) -> bytes:
    return array("h", [0] * max(0, frames)).tobytes()


def render_code_bytes(
    code: int,
    voice: str,
    bpm: int,
    sample_rate: int,
    loudness: float,
    freq_hz: float = TEST_FREQUENCY_HZ,
) -> bytes:
    """Render either a rest (silence) or a played note for this code."""
    dur_s = code_to_seconds(code, bpm)
    if code in REST_CODE_TO_BEATS:
        return _silence_pcm(int(round(dur_s * sample_rate)))
    else:
        return synthesize_note(
            freq_hz=freq_hz,
            duration_s=dur_s,
            loudness=loudness,
            voice=voice,
            sample_rate=sample_rate,
        )


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
    for voice in sorted(ALLOWED_VOICES):
        for note_code in NOTE_CODES:
            rest_code = 13 - note_code  # 7->6, 8->5, ..., 13->0
            loud = rng.uniform(VOLUME_MIN, VOLUME_MAX)
            buf += render_code_bytes(note_code, voice, bpm, sample_rate, loud)
            buf += render_code_bytes(rest_code, voice, bpm, sample_rate, loudness=0.0)
    return bytes(buf)


def write_wav(path: str | Path, pcm_bytes: bytes, sample_rate: int) -> Path:
    p = Path(path)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return p


def sample(
    output_path: str | Path = "composer_sample.wav",
    bpm: int = DEFAULT_BPM,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
    seed: Optional[int] = 42,
) -> Path:
    rng = random.Random(seed) if seed is not None else None
    pcm = compose_demo_bytes(bpm=bpm, sample_rate=sample_rate, rng=rng)
    out = write_wav(output_path, pcm, sample_rate)
    print(f"Wrote {out.resolve()} @ {bpm} BPM, sr={sample_rate}")
    return out


if __name__ == "__main__":
    sample()

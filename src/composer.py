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
import uuid
from array import array
from pathlib import Path
from typing import Mapping, Optional

from src.synth import synthesize_note, SAMPLE_RATE_DEFAULT

DEFAULT_BPM = 120
TEST_FREQUENCY_HZ = 440.0
VOLUME_MIN = 0.35
VOLUME_MAX = 0.95
NOTE_CODES = (7, 8, 9, 10, 11, 12, 13)  
REST_CODES = (0, 1, 2, 3, 4, 5, 6)      

REST_CODE_TO_BEATS: Mapping[int, float] = {
    0: 1 / 4, 
    1: 1 / 8, 
    2: 1 / 16,  
}
NOTE_CODE_TO_BEATS: Mapping[int, float] = {
    3: 1 / 2,   
    4: 1 / 4,   
    5: 1 / 8,   
    6: 1 / 4,       
    7: 1,       
    8: 1 / 2,   
    9: 1 / 4,   
    10: 1 / 8,  
    11: 1 / 16, 
    12: 1 / 8, 
    13: 1 / 16, 
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
    for note_code in NOTE_CODES:
        rest_code = 13 - note_code  # 7->6, 8->5, ..., 13->0
        loud = rng.uniform(VOLUME_MIN, VOLUME_MAX)
        buf += render_code_bytes(note_code,  bpm, sample_rate, loud)
        buf += render_code_bytes(rest_code,  bpm, sample_rate, loudness=0.0)
    return bytes(buf)


# src/composer.py
from pathlib import Path
import wave
import uuid

def _unique_wav_path(dir_path: Path, prefix: str = "audio") -> Path:
    """Return a unique WAV path under dir_path using a UUID filename."""
    dir_path.mkdir(parents=True, exist_ok=True)
    # UUID collisions are practically impossible, but keep a guard anyway.
    while True:
        cand = dir_path / f"{prefix}_{uuid.uuid4().hex}.wav"
        if not cand.exists():
            return cand

def _avoid_overwrite(p: Path) -> Path:
    """If p exists, append ' (n)' before suffix until unique."""
    if not p.exists():
        return p
    stem, suffix = p.stem, (p.suffix or ".wav")
    n = 1
    while True:
        cand = p.with_name(f"{stem} ({n}){suffix}")
        if not cand.exists():
            return cand
        n += 1

def write_wav(
    path: str | Path | None,
    pcm_bytes: bytes,
    sample_rate: int,
    *,
    default_dir: str | Path = "output",
    prefix: str = "audio",
    ensure_unique: bool = True,
) -> Path:
    """
    Write PCM 16-bit mono WAV.

    Behavior:
      - path is None                -> output/<prefix>_<uuid>.wav
      - path points to a directory  -> <that_dir>/<prefix>_<uuid>.wav
      - path is a file:
          * if ensure_unique=True and it exists, write to 'name (1).wav', etc.
          * else overwrite
    """
    if path is None:
        p = _unique_wav_path(Path(default_dir), prefix=prefix)
    else:
        p = Path(path)
        # Treat "no suffix" or existing directory as a directory target.
        if (p.suffix == "" and not p.exists()) or (p.exists() and p.is_dir()):
            p = _unique_wav_path(p if p.exists() else Path(p), prefix=prefix)
        elif ensure_unique and p.exists():
            p = _avoid_overwrite(p)

    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)      # 16-bit
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

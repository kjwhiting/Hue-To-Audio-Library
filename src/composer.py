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


# ===== AUDIO BED DEFAULTS (EDIT HERE) =====
# Steady, subtle bass pulse to sit under the main render.
BASS_BED_BPM_DEFAULT = 84          # gentle head-nodding tempo
BASS_BED_SUBDIVISION = 2           # 2 = eighth notes at given BPM
BASS_PULSE_MS = 110                # length of each thump (ms)
BASS_GAP_MS = 30                   # tiny gap between pulses (ms)
BASS_ROOT_HZ = 55.0                # A1 ≈ 55 Hz; sits under most content
BASS_LOUDNESS_ONBEAT = 0.45        # main thump (0..1, scaled by synth HEADROOM)
BASS_LOUDNESS_OFFBEAT = 0.32       # softer off-beat
BASS_SAMPLE_RATE = 44_100          # keep in sync with synth default


# ===== AUDIO: Steady bass rhythm bed =====
def _frames_for_seconds(seconds: float, sample_rate: int) -> int:
    return max(0, int(round(seconds * sample_rate)))

def render_bass_pulse_bed(
    duration_s: float,
    *,
    bpm: int = BASS_BED_BPM_DEFAULT,
    subdivision: int = BASS_BED_SUBDIVISION,
    root_hz: float = BASS_ROOT_HZ,
    sample_rate: int = BASS_SAMPLE_RATE,
    pulse_ms: int = BASS_PULSE_MS,
    gap_ms: int = BASS_GAP_MS,
    loud_on: float = BASS_LOUDNESS_ONBEAT,
    loud_off: float = BASS_LOUDNESS_OFFBEAT,
) -> bytes:
    """
    Render a steady, muted bass rhythm (PCM16 mono) to layer under your main WAV.

    This version is frame-locked (sample-accurate) to eliminate timing drift:
      - All durations converted to integer frame counts.
      - Each pulse period is exactly the same number of frames.
    """
    if duration_s <= 0:
        return b""

    from src.synth import synthesize_note  # lazy import

    # --- Grid math (frame-locked) ---
    pulses_per_second = (bpm / 60.0) * max(1, subdivision)
    period_frames = max(1, int(round(sample_rate / pulses_per_second)))

    note_frames = max(1, int(round(sample_rate * (pulse_ms / 1000.0))))
    gap_frames_cfg = max(0, int(round(sample_rate * (gap_ms / 1000.0))))

    # Ensure the pulse (note + gap) fits into one period; shrink note if needed
    if note_frames + gap_frames_cfg >= period_frames:
        note_frames = max(1, period_frames - max(0, gap_frames_cfg) - 1)

    # Precompute one period worth of audio for ON and OFF beats
    def make_period(loud: float) -> bytes:
        note = synthesize_note(
            freq_hz=root_hz,
            duration_s=note_frames / sample_rate,
            loudness=loud,
            voice="bass",
            sample_rate=sample_rate,
        )
        # Fill: gap (config) + remaining rest to reach exact period
        produced_frames = len(note) // 2
        gap_frames = min(gap_frames_cfg, max(0, period_frames - produced_frames))
        rest_frames = max(0, period_frames - (produced_frames + gap_frames))
        return note + (b"\x00\x00" * gap_frames) + (b"\x00\x00" * rest_frames)

    period_on = make_period(loud_on)
    period_off = make_period(loud_off)

    # Build full length by repeating periods exactly
    target_frames = int(round(duration_s * sample_rate))
    target_bytes = target_frames * 2

    chunks: List[bytes] = []
    pulse_index = 0
    frames_accum = 0

    while frames_accum < target_frames:
        onbeat = (pulse_index % subdivision) == 0
        block = period_on if onbeat else period_off
        # If the next full period would exceed target, trim it
        remaining_bytes = target_bytes - (frames_accum * 2)
        if len(block) > remaining_bytes:
            block = block[:remaining_bytes]
        chunks.append(block)
        frames_accum += len(block) // 2
        pulse_index += 1

    audio = b"".join(chunks)
    # Pad if needed (rare due to trimming above)
    if len(audio) < target_bytes:
        audio += b"\x00\x00" * ((target_bytes - len(audio)) // 2)

    return audio


if __name__ == "__main__":
    sample()

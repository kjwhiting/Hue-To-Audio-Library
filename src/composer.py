import random
import wave
import uuid
from array import array
from pathlib import Path
from typing import List
from src.synth import synthesize_note, SAMPLE_RATE_DEFAULT

DEFAULT_BPM = 120
TEST_FREQUENCY_HZ = 440.0
VOLUME_MIN = 0.35
VOLUME_MAX = 0.95  


def beats_to_seconds(beats, bpm):
    return (60.0 / bpm) * beats

def code_to_seconds(code, bpm):
    return beats_to_seconds(code, bpm)

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
    dur_s = beats_to_seconds(code, bpm)

    return synthesize_note(
        freq_hz=freq_hz,
        duration_s=dur_s,
        loudness=loudness,
        sample_rate=sample_rate,
    )



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

def write_wav(
    path,
    pcm_bytes,
    sample_rate,
):
    if path is None:
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        p = output_dir / f"{path}_{uuid.uuid4().hex}.wav"
    else:
        p= path

    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)      # 16-bit
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return p

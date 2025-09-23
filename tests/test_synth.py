# tests/test_synth.py
from pathlib import Path
from array import array
import math
import pytest

from src.synth import synthesize_note, C2_HZ, C6_HZ, SAMPLE_RATE_DEFAULT


def _as_int16(buf: bytes) -> array:
    a = array("h")
    a.frombytes(buf)
    return a


@pytest.mark.parametrize("voice", ["sine", "triangle", "bell"])
def test_length_and_clip_safety(voice):
    sr = SAMPLE_RATE_DEFAULT
    buf = synthesize_note(freq_hz=440.0, duration_s=0.25, loudness=1.0, voice=voice, sample_rate=sr)
    samples = _as_int16(buf)

    # expected length within 1 sample of rounding
    assert abs(len(samples) - int(round(0.25 * sr))) <= 1

    # no clipping to int16 extremes
    peak = max(abs(x) for x in samples)
    assert peak < 32000  # headroom (32767 is int16 max)


def test_loudness_scales_amplitude():
    sr = SAMPLE_RATE_DEFAULT
    buf_lo = _as_int16(synthesize_note(440.0, 0.2, 0.25, "sine", sr))
    buf_hi = _as_int16(synthesize_note(440.0, 0.2, 1.00, "sine", sr))

    # Compare RMS of middle chunk to avoid fades
    def rms(a: array) -> float:
        # skip first/last 10ms
        skip = int(0.01 * sr)
        vals = a[skip: -skip] if len(a) > skip * 2 else a
        return math.sqrt(sum(x * x for x in vals) / max(1, len(vals)))

    assert rms(buf_hi) > rms(buf_lo) * 1.5  # clearly louder; not exact ratio due to fades


def test_bell_decays_over_time():
    sr = SAMPLE_RATE_DEFAULT
    samples = _as_int16(synthesize_note(440.0, 0.5, 0.8, "bell", sr))
    n = len(samples)
    assert n > 0

    # Split into quarters and compute RMS for early vs late sections.
    q = n // 4

    def rms(arr):
        return math.sqrt(sum(x * x for x in arr) / max(1, len(arr)))

    # Skip the first/last ~10ms to avoid fades dominating the measurement.
    skip = max(1, int(0.01 * sr))
    early = samples[q + skip : 2 * q]          # early middle
    late = samples[3 * q : max(3 * q + 1, n - skip)]  # late (avoid final fade-only)

    first = rms(early)
    last = rms(late)

    # Sanity: early section should have non-trivial energy
    assert first > 1.0

    # Decay check: the tail should be notably quieter than the early section.
    ratio = last / first
    assert ratio < 0.8  # 20% drop or more; generous to avoid flakiness


def test_frequency_guard_raises():
    with pytest.raises(Exception):
        synthesize_note(freq_hz=C2_HZ - 1.0, duration_s=0.1, loudness=0.5, voice="sine")
    with pytest.raises(Exception):
        synthesize_note(freq_hz=C6_HZ + 1.0, duration_s=0.1, loudness=0.5, voice="sine")


def test_zero_or_negative_duration_returns_empty():
    assert synthesize_note(440.0, 0.0, 0.5, "sine") == b""
    assert synthesize_note(440.0, -1.0, 0.5, "sine") == b""

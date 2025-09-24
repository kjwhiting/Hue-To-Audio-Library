import math

import pytest

from src.synth import (
    synthesize_note,
    synthesize_bass_bed,
    SAMPLE_RATE_DEFAULT,
)


def test_bass_voice_basic_bytes():
    data = synthesize_note(
        freq_hz=60.0, duration_s=0.25, loudness=0.3, sample_rate=SAMPLE_RATE_DEFAULT
    )
    assert isinstance(data, (bytes, bytearray))
    # 0.25s * 44100 * 2 bytes = ~22050 bytes (mono int16)
    assert len(data) > 10_000


def test_bass_bed_helper_works_and_length():
    dur = 0.5
    data = synthesize_bass_bed(duration_s=dur, loudness=0.2, root_hz=55.0)
    assert isinstance(data, (bytes, bytearray))
    # allow small rounding error
    expected_frames = int(round(dur * SAMPLE_RATE_DEFAULT))
    assert len(data) // 2 in range(expected_frames - 2, expected_frames + 3)


def test_low_frequency_guard_allows_c1_to_c6():
    # Lower edge within range (C1≈33 Hz)
    data = synthesize_note(33.0, 0.1, 0.3)
    assert len(data) > 0
    # Upper edge still acceptable
    data2 = synthesize_note(1050.0, 0.1, 0.3)
    assert len(data2) > 0



# tests/test_composer.py
from __future__ import annotations

import random
from pathlib import Path
import wave

import pytest

from src.composer import (
    DEFAULT_BPM,
    beats_to_seconds,
    duration_code_to_seconds,
    compose_demo_bytes,
    write_wav,
)
from src.synth import SAMPLE_RATE_DEFAULT, ALLOWED_VOICES


def test_beats_to_seconds_and_code_mapping():
    # At 120 BPM: quarter = 0.5s, whole = 2.0s
    assert beats_to_seconds(1.0, 120) == pytest.approx(0.5)
    assert duration_code_to_seconds(2, 120) == pytest.approx(0.5)   # quarter
    assert duration_code_to_seconds(1, 120) == pytest.approx(2.0)   # whole

    # Bad BPM
    with pytest.raises(ValueError):
        _ = beats_to_seconds(1.0, 0)

    # Bad code
    with pytest.raises(ValueError):
        _ = duration_code_to_seconds(0, 120)


def test_compose_demo_bytes_deterministic_with_seed():
    rng1 = random.Random(1234)
    rng2 = random.Random(1234)
    pcm1 = compose_demo_bytes(bpm=DEFAULT_BPM, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng1)
    pcm2 = compose_demo_bytes(bpm=DEFAULT_BPM, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng2)
    assert pcm1 == pcm2
    assert len(pcm1) > 0


def test_compose_demo_bytes_bpm_affects_length():
    rng = random.Random(7)
    pcm_fast = compose_demo_bytes(bpm=180, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng)
    rng = random.Random(7)  # reset to keep loudness choices identical
    pcm_slow = compose_demo_bytes(bpm=60, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng)
    # Slower BPM => longer note buffers
    assert len(pcm_slow) > len(pcm_fast)


def test_write_wav_roundtrip(tmp_path: Path):
    rng = random.Random(99)
    pcm = compose_demo_bytes(bpm=DEFAULT_BPM, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng)
    out = tmp_path / "demo.wav"
    write_wav(out, pcm, SAMPLE_RATE_DEFAULT)
    assert out.exists() and out.stat().st_size > 44  # larger than a bare WAV header

    # Light sanity on header via wave module
    with wave.open(str(out), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == SAMPLE_RATE_DEFAULT
        assert w.getnframes() > 0

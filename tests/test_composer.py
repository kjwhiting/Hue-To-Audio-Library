from __future__ import annotations

import random
from array import array
from pathlib import Path
import wave

import pytest

from src.composer import (
    DEFAULT_BPM,
    beats_to_seconds,
    code_to_seconds,
    compose_demo_bytes,
    render_code_bytes,
    write_wav,
)
from src.synth import SAMPLE_RATE_DEFAULT, ALLOWED_VOICES


def _as_int16(buf: bytes) -> array:
    a = array("h"); a.frombytes(buf); return a


def test_code_to_seconds_mapping_boundaries():
    # Whole note length at 120 BPM: 2.0s
    assert code_to_seconds(7, 120) == pytest.approx(2.0)   # whole note
    assert code_to_seconds(9, 120) == pytest.approx(0.5)   # quarter
    assert code_to_seconds(13, 120) == pytest.approx(0.03125)  # 1/64: 0.0625 beats @120 = 0.03125s

    # Rests mirror, e.g., code 6 = whole rest
    assert code_to_seconds(6, 120) == pytest.approx(2.0)
    assert code_to_seconds(0, 120) == pytest.approx(0.03125)


def test_render_code_bytes_rest_is_silence(tmp_path: Path):
    dur_s = code_to_seconds(6, DEFAULT_BPM)  # whole rest at default BPM
    frames = int(round(dur_s * SAMPLE_RATE_DEFAULT))
    buf = render_code_bytes(6, "sine", DEFAULT_BPM, SAMPLE_RATE_DEFAULT, loudness=0.8)
    assert len(buf) == frames * 2  # 16-bit mono
    samples = _as_int16(buf)
    assert all(v == 0 for v in samples)


def test_render_code_bytes_note_is_nonzero():
    buf = render_code_bytes(9, "sine", DEFAULT_BPM, SAMPLE_RATE_DEFAULT, loudness=0.6)  # quarter note
    samples = _as_int16(buf)
    assert any(v != 0 for v in samples)


def test_compose_demo_bytes_deterministic_with_seed():
    rng1 = random.Random(1234)
    rng2 = random.Random(1234)
    pcm1 = compose_demo_bytes(bpm=DEFAULT_BPM, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng1)
    pcm2 = compose_demo_bytes(bpm=DEFAULT_BPM, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng2)
    assert pcm1 == pcm2 and len(pcm1) > 0


def test_write_wav_roundtrip(tmp_path: Path):
    rng = random.Random(99)
    pcm = compose_demo_bytes(bpm=DEFAULT_BPM, sample_rate=SAMPLE_RATE_DEFAULT, rng=rng)
    out = tmp_path / "demo.wav"
    write_wav(out, pcm, SAMPLE_RATE_DEFAULT)
    assert out.exists() and out.stat().st_size > 44
    with wave.open(str(out), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == SAMPLE_RATE_DEFAULT
        assert w.getnframes() > 0

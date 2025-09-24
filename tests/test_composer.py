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
    render_code_bytes,
    write_wav,
)
from src.synth import SAMPLE_RATE_DEFAULT


def _as_int16(buf: bytes) -> array:
    a = array("h"); a.frombytes(buf); return a



def test_render_code_bytes_note_is_nonzero():
    buf = render_code_bytes(9,  DEFAULT_BPM, SAMPLE_RATE_DEFAULT, loudness=0.6)  # quarter note
    samples = _as_int16(buf)
    assert any(v != 0 for v in samples)
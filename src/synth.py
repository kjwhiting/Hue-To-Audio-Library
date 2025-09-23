# src/synth.py
"""
Simple, beautiful note synthesis (stdlib-only).

Public API:
    synthesize_note(freq_hz: float,
                    duration_s: float,
                    loudness: float,
                    voice: str = "sine",
                    sample_rate: int = 44100) -> bytes

Voices:
    - "sine":     Pure sine with gentle fades. Clean and clear.
    - "triangle": Warm, odd-harmonic additive triangle (band-limited).
    - "bell":     Pleasant inharmonic bell with exponential partial decays.

Output:
    - PCM 16-bit mono (little-endian) as bytes. Composer can concatenate these.
"""

from __future__ import annotations

import math
from array import array
from typing import Iterable

from src.exceptions import OutsideAllowableRange

# ===== CONFIG / CONSTANTS (EDIT HERE) =====
SAMPLE_RATE_DEFAULT = 44_100
HEADROOM = 0.85            # global safety margin (do not push to 1.0)
FADE_MS = 8                # fade-in/out (ms) to avoid clicks

# Musical range guard (C2..C6)
C2_HZ = 60          # ~ C2
C6_HZ = 1050        # ~ C6

ALLOWED_VOICES = {"sine", "triangle", "bell"}


# ===== UTILITIES =====
def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _frames_for_duration(duration_s: float, sample_rate: int) -> int:
    if duration_s <= 0:
        return 0
    return max(0, int(round(duration_s * sample_rate)))


def _apply_fades(buf: list[float], sample_rate: int, fade_ms: int) -> None:
    """In-place half-sine fades at start and end to prevent clicks."""
    n = len(buf)
    if n == 0:
        return
    fade_n = max(1, min(n // 2, int(sample_rate * (fade_ms / 1000.0))))
    # Fade-in
    for i in range(fade_n):
        w = math.sin((i / fade_n) * (math.pi / 2))  # 0..1 half-sine
        buf[i] *= w
    # Fade-out
    for i in range(fade_n):
        w = math.sin(((fade_n - 1 - i) / fade_n) * (math.pi / 2))
        buf[n - 1 - i] *= w


def _pcm16_from_float(buf: Iterable[float]) -> bytes:
    """Convert float samples in [-1, 1] to PCM int16 little-endian bytes."""
    out = array("h")
    for x in buf:
        # hard clip as last resort
        if x < -1.0:
            x = -1.0
        elif x > 1.0:
            x = 1.0
        out.append(int(round(x * 32767.0)))
    return out.tobytes()


def _bandlimited_triangle_sample_table(freq_hz: float, sample_rate: int) -> list[tuple[int, float]]:
    """
    Build list of (k, weight) for odd harmonics of triangle wave,
    band-limited to Nyquist. Triangle Fourier:
        x(t) = (8/pi^2) * sum_{n odd} [(-1)^((n-1)/2) * sin(2πnft) / n^2]
    We normalize by sum |weights| so peak stays reasonable.
    """
    nyquist = sample_rate / 2.0
    weights = []
    k = 1
    norm = 0.0
    base = 8.0 / (math.pi ** 2)
    while k * freq_hz < nyquist:
        sign = -1.0 if ((k - 1) // 2) % 2 else 1.0  # alternate + - + - ...
        w = sign * base / (k * k)
        weights.append((k, w))
        norm += abs(w)
        k += 2  # odd only
        if k > 199:  # safety bound
            break
    if norm == 0.0:
        return []
    # Normalize to sum of abs(weights) == 1.0
    return [(k, w / norm) for (k, w) in weights]


def _bell_partials(freq_hz: float, sample_rate: int) -> list[tuple[float, float, float]]:
    """
    Inharmonic bell partials: (ratio, amp, tau_seconds)
      Ratios chosen to sound pleasant while staying well below Nyquist across C2..C6.
    """
    nyquist = sample_rate / 2.0
    partials = [
        (1.00, 1.00, 1.20),  # fundamental, slow decay
        (2.70, 0.55, 0.80),
        (5.80, 0.25, 0.50),
        (9.20, 0.12, 0.35),
    ]
    # Drop any that would exceed Nyquist at this pitch
    usable = [(r, a, tau) for (r, a, tau) in partials if r * freq_hz < nyquist]
    # Normalize amplitudes to sum to 1.0
    total = sum(a for (_, a, _) in usable) or 1.0
    return [(r, a / total, tau) for (r, a, tau) in usable]


# ===== SYNTH CORE =====
def synthesize_note(
    freq_hz: float,
    duration_s: float,
    loudness: float,
    voice: str = "sine",
    sample_rate: int = SAMPLE_RATE_DEFAULT,
) -> bytes:
    """
    Generate a single note buffer (PCM 16-bit mono) for the given voice.

    Args:
        freq_hz:    Frequency in Hz. Must be within C2..C6 for safety.
        duration_s: Note length in seconds (>0).
        loudness:   Scalar 0..1. Overall output is scaled by HEADROOM * loudness.
        voice:      "sine" | "triangle" | "bell"
        sample_rate:Samples per second (default 44100).

    Returns:
        bytes: PCM int16 mono samples.

    Raises:
        OutsideAllowableRange: if freq_hz is outside C2..C6.
        ValueError: for bad args (duration <= 0, unknown voice).
    """
    if not (C2_HZ <= freq_hz <= C6_HZ):
        raise OutsideAllowableRange(f"Frequency {freq_hz:.2f} Hz outside C2..C6 range")
    if duration_s <= 0:
        return b""
    if voice not in ALLOWED_VOICES:
        raise ValueError(f"Unknown voice '{voice}'. Allowed: {sorted(ALLOWED_VOICES)}")

    n = _frames_for_duration(duration_s, sample_rate)
    if n == 0:
        return b""

    loud = _clamp01(loudness) * HEADROOM
    two_pi_f_over_sr = 2.0 * math.pi * freq_hz / sample_rate

    # Render per voice
    buf = [0.0] * n

    if voice == "sine":
        for i in range(n):
            buf[i] = math.sin(two_pi_f_over_sr * i) * loud

    elif voice == "triangle":
        terms = _bandlimited_triangle_sample_table(freq_hz, sample_rate)
        if not terms:
            # fallback to sine if too high
            for i in range(n):
                buf[i] = math.sin(two_pi_f_over_sr * i) * loud
        else:
            for i in range(n):
                s = 0.0
                phase = two_pi_f_over_sr * i
                for k, w in terms:
                    s += w * math.sin(phase * k)
                buf[i] = s * loud

    elif voice == "bell":
        parts = _bell_partials(freq_hz, sample_rate)
        for i in range(n):
            t = i / sample_rate
            phase = two_pi_f_over_sr * i
            s = 0.0
            for ratio, amp, tau in parts:
                s += amp * math.sin(phase * ratio) * math.exp(-t / tau)
            buf[i] = s * loud

    # Clickless fades (attack/release)
    _apply_fades(buf, sample_rate, FADE_MS)

    # Convert to PCM16
    return _pcm16_from_float(buf)

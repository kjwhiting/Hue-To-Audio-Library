from __future__ import annotations

import math
from array import array
from typing import Iterable, List

SAMPLE_RATE_DEFAULT = 44_100
HEADROOM = 0.85            # global safety margin (do not push to 1.0)
FADE_MS = 8                # fade-in/out (ms) to avoid clicks (legacy API)

# Musical range guard (C1..C6) — widened to allow deep bass pads
C1_HZ = 33          # ~ C1 (rounded 32.7 -> 33)
C6_HZ = 1050        # ~ C6

ALLOWED_VOICES = {"sine", "triangle", "bell", "bass"}


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
      Ratios chosen to sound pleasant while staying well below Nyquist across C1..C6.
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


def _soft_clip(x: float, drive: float = 1.2) -> float:
    """Mild, musical soft clip using tanh. drive≈1.0–1.5 recommended."""
    return math.tanh(x * drive)


# ===== NEW: ADSR envelope =====
def _adsr_envelope(
    n_frames: int,
    sample_rate: int,
    attack_ms: int,
    decay_ms: int,
    sustain: float,
    release_ms: int,
    extend_tail: bool,
) -> list[float]:
    """
    Build an ADSR envelope. If extend_tail=True, we append release frames,
    returning a list longer than n_frames so the tail fully decays (no cut-off).
    """
    sustain = _clamp01(sustain)
    a = max(0, int(round(sample_rate * (attack_ms / 1000.0))))
    d = max(0, int(round(sample_rate * (decay_ms / 1000.0))))
    r = max(0, int(round(sample_rate * (release_ms / 1000.0))))

    body_frames = n_frames
    total_frames = body_frames + (r if extend_tail else 0)
    env = [0.0] * total_frames

    # Attack (0 -> 1)
    for i in range(min(a, total_frames)):
        env[i] = i / max(1, a)

    # Decay (1 -> sustain)
    start = a
    end = min(a + d, total_frames)
    for i in range(start, end):
        t = (i - start) / max(1, (end - start))
        env[i] = 1.0 + (sustain - 1.0) * t

    # Sustain (flat)
    for i in range(end, min(body_frames, total_frames)):
        env[i] = sustain

    # Release (sustain -> 0)
    rel_start = body_frames
    rel_end = min(body_frames + r, total_frames)
    if rel_start < rel_end:
        for i in range(rel_start, rel_end):
            t = (i - rel_start) / max(1, (rel_end - rel_start))
            env[i] = sustain * (1.0 - t)

    # Ensure very start/end are not exactly zero to avoid all-zero chunks
    if total_frames:
        env[0] *= 1.0
        env[-1] *= 1.0
    return env


# ===== SYNTH CORE =====
def synthesize_note(
    freq_hz: float,
    duration_s: float,
    loudness: float,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
) -> bytes:
    if duration_s <= 0:
        return b""

    n = _frames_for_duration(duration_s, sample_rate)
    if n == 0:
        return b""

    loud = _clamp01(loudness) * HEADROOM
    two_pi_f_over_sr = 2.0 * math.pi * freq_hz / sample_rate

    # Render per voice
    buf = [0.0] * n

   
    sub_ok = (freq_hz * 0.5) >= 20.0
    for i in range(n):
        phase = two_pi_f_over_sr * i
        s_fund = math.sin(phase)
        s_sub = math.sin(phase * 0.5) if sub_ok else 0.0
        s_2nd = math.sin(phase * 2.0)
        s = 0.82 * s_fund + 0.30 * s_sub + 0.06 * s_2nd
        s = _soft_clip(s, drive=1.10)
        buf[i] = s * loud


    for i in range(n):
        buf[i] = math.sin(two_pi_f_over_sr * i) * loud

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

    parts = _bell_partials(freq_hz, sample_rate)
    for i in range(n):
        t = i / sample_rate
        phase = two_pi_f_over_sr * i
        s = 0.0
        for ratio, amp, tau in parts:
            s += amp * math.sin(phase * ratio) * math.exp(-t / tau)
        buf[i] = s * loud



    # Clickless fades (attack/release for legacy API)
    _apply_fades(buf, sample_rate, FADE_MS)

    # Convert to PCM16
    return _pcm16_from_float(buf)


# ===== NEW: ADSR variant (smooth, natural tails) =====
def synthesize_note_env(
    freq_hz: float,
    duration_s: float,
    loudness: float,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
    *,
    attack_ms: int = 8,
    decay_ms: int = 60,
    sustain: float = 0.85,
    release_ms: int = 160,
    extend_tail: bool = True,
) -> bytes:
    if duration_s <= 0:
        return b""

    n_body = _frames_for_duration(duration_s, sample_rate)
    if n_body == 0:
        return b""

    # Build envelope (may extend tail)
    env = _adsr_envelope(n_body, sample_rate, attack_ms, decay_ms, sustain, release_ms, extend_tail)
    n_total = len(env)

    loud = _clamp01(loudness) * HEADROOM
    two_pi_f_over_sr = 2.0 * math.pi * freq_hz / sample_rate

    buf = [0.0] * n_total

    for i in range(n_total):
        buf[i] = math.sin(two_pi_f_over_sr * i) * loud * env[i]

    terms = _bandlimited_triangle_sample_table(freq_hz, sample_rate)
    if not terms:
        for i in range(n_total):
            buf[i] = math.sin(two_pi_f_over_sr * i) * loud * env[i]
    else:
        for i in range(n_total):
            s = 0.0
            phase = two_pi_f_over_sr * i
            for k, w in terms:
                s += w * math.sin(phase * k)
            buf[i] = s * loud * env[i]

    parts = _bell_partials(freq_hz, sample_rate)
    for i in range(n_total):
        t = i / sample_rate
        phase = two_pi_f_over_sr * i
        s = 0.0
        for ratio, amp, tau in parts:
            s += amp * math.sin(phase * ratio) * math.exp(-t / tau)
        buf[i] = s * loud * env[i]

    sub_ok = (freq_hz * 0.5) >= 20.0
    for i in range(n_total):
        phase = two_pi_f_over_sr * i
        s_fund = math.sin(phase)
        s_sub = math.sin(phase * 0.5) if sub_ok else 0.0
        s_2nd = math.sin(phase * 2.0)
        s = 0.82 * s_fund + 0.30 * s_sub + 0.06 * s_2nd
        s = _soft_clip(s, drive=1.08)
        buf[i] = s * loud * env[i]

    # No extra end fades needed; ADSR handles attack/release.
    return _pcm16_from_float(buf)


def make_render_all_voices_perfect_fifth(sample_rate: int, f_root: float):
    """
    Precompute data for root and perfect fifth (3/2) and return a per-frame
    renderer that combines ALL voices (sine, triangle, bell, bass) into one sample.

    Returns:
        render(i: int) -> float   # dry oscillator sample in roughly [-1, 1]
    """
    f5 = f_root * 1.5
    two_pi_over_sr_root = 2.0 * math.pi * f_root / sample_rate
    two_pi_over_sr_f5   = 2.0 * math.pi * f5     / sample_rate

    # Precompute triangle weight tables (band-limited) for root and fifth
    tri_terms_root = _bandlimited_triangle_sample_table(f_root, sample_rate)
    tri_terms_f5   = _bandlimited_triangle_sample_table(f5, sample_rate)

    # Precompute bell partials for root and fifth
    bell_parts_root = _bell_partials(f_root, sample_rate)
    bell_parts_f5   = _bell_partials(f5, sample_rate)

    # Bass sub-octave validity (avoid sub < 20 Hz)
    bass_sub_root_ok = (f_root * 0.5) >= 20.0
    bass_sub_f5_ok   = (f5 * 0.5)   >= 20.0

    def render(i: int) -> float:
        # Phases for root and fifth
        phase_r = two_pi_over_sr_root * i
        phase_5 = two_pi_over_sr_f5   * i
        t = i / sample_rate

        # ---- SINE (root + fifth) ----
        sine_r = math.sin(phase_r)
        sine_5 = math.sin(phase_5)
        v_sine = 0.5 * (sine_r + sine_5)  # average root & fifth

        # ---- TRIANGLE (additive, band-limited) ----
        if tri_terms_root:
            tri_r = sum(w * math.sin(phase_r * k) for k, w in tri_terms_root)
        else:
            tri_r = math.sin(phase_r)
        if tri_terms_f5:
            tri_5 = sum(w * math.sin(phase_5 * k) for k, w in tri_terms_f5)
        else:
            tri_5 = math.sin(phase_5)
        v_tri = 0.5 * (tri_r + tri_5)

        # ---- BELL (inharmonic partials, exponential decays) ----
        bell_r = 0.0
        for ratio, amp, tau in bell_parts_root:
            bell_r += amp * math.sin(phase_r * ratio) * math.exp(-t / tau)
        bell_5 = 0.0
        for ratio, amp, tau in bell_parts_f5:
            bell_5 += amp * math.sin(phase_5 * ratio) * math.exp(-t / tau)
        v_bell = 0.5 * (bell_r + bell_5)

        # ---- BASS (fundamental + optional sub + tiny 2nd) ----
        # Root
        b_r_fund = math.sin(phase_r)
        b_r_sub  = math.sin(phase_r * 0.5) if bass_sub_root_ok else 0.0
        b_r_2nd  = math.sin(phase_r * 2.0)
        bass_r   = 0.82 * b_r_fund + 0.30 * b_r_sub + 0.06 * b_r_2nd
        # Fifth
        b_5_fund = math.sin(phase_5)
        b_5_sub  = math.sin(phase_5 * 0.5) if bass_sub_f5_ok else 0.0
        b_5_2nd  = math.sin(phase_5 * 2.0)
        bass_5   = 0.82 * b_5_fund + 0.30 * b_5_sub + 0.06 * b_5_2nd
        v_bass = 0.5 * (bass_r + bass_5)
        v_bass = _soft_clip(v_bass, drive=1.06)

        # ---- Mix all voices (average) and polish ----
        v = (v_sine + v_tri + v_bell + v_bass) * 0.25  # equal-voice average
        return _soft_clip(v, drive=1.04)

    return render


# ===== CONVENIENCE: Bass bed helper (unchanged) =====
def synthesize_bass_bed(
    duration_s: float,
    loudness: float = 0.25,
    root_hz: float = 55.0,  # A1 ≈ 55 Hz; sits well under most content
    sample_rate: int = SAMPLE_RATE_DEFAULT,
) -> bytes:
    """
    Generate a gentle deep-bass bed (mono) suitable for background underlays.

    Args:
        duration_s: Length in seconds.
        loudness:   0..1 scalar; defaults to subtle (0.25).
        root_hz:    Fundamental frequency in Hz (default A1 ≈ 55 Hz).
        sample_rate:Samples per second.

    Returns:
        bytes: PCM 16-bit mono.

    Notes:
        - Uses the "bass" voice.
        - Keep loudness low (0.15–0.35) to avoid masking primary content.
    """
    return synthesize_note(
        freq_hz=root_hz,
        duration_s=duration_s,
        loudness=loudness,
        sample_rate=sample_rate,
    )

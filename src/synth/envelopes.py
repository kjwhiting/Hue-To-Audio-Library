# envelopes.py
"""
Two envelope families:
- Filter envelopes (fenv_*): ADSR + small fade-in/out to prevent clicks.
- Amplifier envelopes (aenv_*): ADSR only (no fade by default).

Both operate on PCM16 mono sample arrays (list[int]).
"""

from typing import List
from src.synth.oscillators import SAMPLE_RATE

# ===== Core ADSR =====
def _apply_adsr(samples: List[int],
                attack: float,
                decay: float,
                sustain: float,
                release: float) -> List[int]:
    n_total = len(samples)
    sr = SAMPLE_RATE

    n_attack = max(0, int(sr * max(attack, 0.0)))
    n_decay = max(0, int(sr * max(decay, 0.0)))
    n_release = max(0, int(sr * max(release, 0.0)))
    n_sustain = max(0, n_total - (n_attack + n_decay + n_release))

    if n_attack + n_decay + n_release > n_total:
        # Too short for full ADSR: scale everything to sustain level.
        return [int(s * float(sustain)) for s in samples]

    env: List[float] = []

    # Attack: 0 → 1
    if n_attack > 0:
        env += [i / n_attack for i in range(n_attack)]
    # Decay: 1 → sustain
    if n_decay > 0:
        env += [1.0 - (1.0 - sustain) * (i / n_decay) for i in range(n_decay)]
    # Sustain: flat
    env += [float(sustain)] * n_sustain
    # Release: sustain → 0
    if n_release > 0:
        env += [float(sustain) * (1.0 - i / n_release) for i in range(n_release)]

    # Match length exactly
    if len(env) < n_total:
        env += [0.0] * (n_total - len(env))
    elif len(env) > n_total:
        env = env[:n_total]

    return [int(s * e) for s, e in zip(samples, env)]


# ===== Simple linear fade used by FILTER envelopes only =====
def _fade(samples: List[int], fade_time: float = 0.01) -> List[int]:
    """Linear fade-in/out at the head and tail (default 10 ms)."""
    n_total = len(samples)
    if n_total == 0:
        return samples
    n_fade = max(0, int(SAMPLE_RATE * max(fade_time, 0.0)))
    if n_fade == 0 or n_fade * 2 > n_total:
        return samples

    out = samples[:]
    # Fade in
    for i in range(n_fade):
        factor = i / n_fade
        out[i] = int(out[i] * factor)
    # Fade out
    for i in range(n_fade):
        factor = 1.0 - (i / n_fade)
        out[-(i + 1)] = int(out[-(i + 1)] * factor)
    return out


# ===== FILTER ENVELOPES (ADSR + FADE) =====
def fenv_piano(samples: List[int],
               attack: float = 0.01,
               decay: float = 0.20,
               sustain: float = 0.30,
               release: float = 0.20,
               fade_time: float = 0.01) -> List[int]:
    shaped = _apply_adsr(samples, attack, decay, sustain, release)
    return _fade(shaped, fade_time)


def fenv_string(samples: List[int],
                attack: float = 0.10,
                decay: float = 0.30,
                sustain: float = 0.60,
                release: float = 0.30,
                fade_time: float = 0.01) -> List[int]:
    shaped = _apply_adsr(samples, attack, decay, sustain, release)
    return _fade(shaped, fade_time)


def fenv_drums(samples: List[int],
               attack: float = 0.005,
               decay: float = 0.15,
               sustain: float = 0.00,
               release: float = 0.05,
               fade_time: float = 0.01) -> List[int]:
    shaped = _apply_adsr(samples, attack, decay, sustain, release)
    return _fade(shaped, fade_time)


# ===== AMPLIFIER ENVELOPES (ADSR only) =====
def aenv_piano(samples: List[int],
               attack: float = 0.01,
               decay: float = 0.20,
               sustain: float = 0.30,
               release: float = 0.20) -> List[int]:
    return _apply_adsr(samples, attack, decay, sustain, release)


def aenv_string(samples: List[int],
                attack: float = 0.10,
                decay: float = 0.30,
                sustain: float = 0.60,
                release: float = 0.30) -> List[int]:
    return _apply_adsr(samples, attack, decay, sustain, release)


def aenv_drums(samples: List[int],
               attack: float = 0.005,
               decay: float = 0.15,
               sustain: float = 0.00,
               release: float = 0.05) -> List[int]:
    return _apply_adsr(samples, attack, decay, sustain, release)

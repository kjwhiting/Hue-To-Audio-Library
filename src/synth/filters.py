# filters.py
"""
Bare-bones filters + FILTER envelopes.
Apply these BEFORE amplifiers.

Filters:
- low_pass_one_pole(cutoff_hz)
- high_pass_one_pole(cutoff_hz)
- dc_block()

Filter envelopes (ADSR + fade):
- fenv_piano / fenv_string / fenv_drums
"""

from typing import List
import math
from src.synth.oscillators import (
    sine_wave,
    square_wave,
    saw_wave,
    write_wav,
    play_file,
    SAMPLE_RATE,
)
from src.synth.envelopes import fenv_piano, fenv_string, fenv_drums

# ===== ONE-POLE FILTER HELPERS =====
def _alpha_lowpass(cutoff_hz: float, sr: int) -> float:
    rc = 1.0 / (2.0 * math.pi * max(cutoff_hz, 1e-6))
    dt = 1.0 / sr
    return dt / (rc + dt)

def _alpha_highpass(cutoff_hz: float, sr: int) -> float:
    rc = 1.0 / (2.0 * math.pi * max(cutoff_hz, 1e-6))
    dt = 1.0 / sr
    return rc / (rc + dt)

# ===== PUBLIC FILTERS =====
def low_pass_one_pole(samples: List[int], cutoff_hz: float) -> List[int]:
    a = _alpha_lowpass(cutoff_hz, SAMPLE_RATE)
    if not samples:
        return samples
    y: List[int] = []
    y_prev = samples[0]
    for x in samples:
        y_prev = y_prev + a * (x - y_prev)
        y.append(int(y_prev))
    return y

def high_pass_one_pole(samples: List[int], cutoff_hz: float) -> List[int]:
    a = _alpha_highpass(cutoff_hz, SAMPLE_RATE)
    if not samples:
        return samples
    y: List[int] = []
    y_prev = samples[0]
    x_prev = samples[0]
    for x in samples:
        y_prev = a * (y_prev + x - x_prev)
        y.append(int(y_prev))
        x_prev = x
    return y

def dc_block(samples: List[int], cutoff_hz: float = 20.0) -> List[int]:
    return high_pass_one_pole(samples, cutoff_hz)

# ===== DEMO: oscillators → filters → filter-envelope → (amp later) =====
if __name__ == "__main__":
    from amplifiers import amplifier  # keep the chain intact

    print("Demo: oscillators → filters → filter-envelope → amplifier → wav")

    # 1) Square → LPF → piano env (with fade) → amp
    sq = square_wave()
    sq_lp = low_pass_one_pole(sq, cutoff_hz=1200.0)
    sq_env = fenv_piano(sq_lp, attack=0.01, decay=0.15, sustain=0.25, release=0.20)
    sq_out = amplifier(sq_env)
    p1 = write_wav("square_lp_piano.wav", sq_out)
    play_file(p1)

    # 2) Saw → HPF → string env → amp
    sw = saw_wave()
    sw_hp = high_pass_one_pole(sw, cutoff_hz=80.0)
    sw_env = fenv_string(sw_hp, attack=0.08, decay=0.25, sustain=0.60, release=0.30)
    sw_out = amplifier(sw_env)
    p2 = write_wav("saw_hp_string.wav", sw_out)
    play_file(p2)

    # 3) Sine → DC block → drums env → amp
    si = sine_wave()
    si_dc = dc_block(si)
    si_env = fenv_drums(si_dc, attack=0.005, decay=0.12, sustain=0.0, release=0.05)
    si_out = amplifier(si_env)
    p3 = write_wav("sine_dc_drums.wav", si_out)
    play_file(p3)

    print("Done. Files saved in ./output/")

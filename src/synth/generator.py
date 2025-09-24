# sound_generator.py
"""
Bare-bones sound generator:
oscillators → filters → filter-envelope → amplifier-envelope → amplifier → WAV/play

Usage (see __main__ demos at bottom):
- play_tone(freq, dur, ["sine", "saw"], filters=[...], fenv=..., aenv=..., gain=0.75)
"""

from typing import List, Callable, Iterable, Optional
from pathlib import Path

# Project-local modules (from previous steps)
from src.synth.oscillators import sine_wave, square_wave, saw_wave, write_wav, play_file
from filters import low_pass_one_pole, high_pass_one_pole, dc_block
from src.synth.envelopes import fenv_piano, fenv_string, fenv_drums, aenv_piano, aenv_string, aenv_drums
from amplifiers import amplifier


# ----- Helpers -----
OscFn = Callable[..., List[int]]
Samples = List[int]


_OSC_LOOKUP: dict[str, OscFn] = {
    "sine": sine_wave,
    "square": square_wave,
    "saw": saw_wave,
}


def _mix_layers(layers: Iterable[Samples]) -> Samples:
    """
    Sum-and-average mix. Assumes all layers are same length.
    Clips to 16-bit range.
    """
    layers = list(layers)
    if not layers:
        return []
    n = len(layers[0])
    if any(len(ch) != n for ch in layers):
        # Truncate to shortest length
        n = min(len(ch) for ch in layers)
        layers = [ch[:n] for ch in layers]

    out: Samples = []
    inv = 1.0 / len(layers)
    for i in range(n):
        s = int(sum(ch[i] for ch in layers) * inv)
        # clip to int16
        if s > 32767:
            s = 32767
        elif s < -32768:
            s = -32768
        out.append(s)
    return out


def _apply_filters(samples: Samples, filters: Optional[List[Callable[[Samples], Samples]]]) -> Samples:
    if not filters:
        return samples
    out = samples
    for f in filters:
        out = f(out)
    return out


# ----- Public API -----
def play_tone(
    frequency: float,
    duration: float,
    oscillators: List[str],
    filters: Optional[List[Callable[[Samples], Samples]]] = None,
    fenv: Optional[Callable[[Samples], Samples]] = None,
    aenv: Optional[Callable[[Samples], Samples]] = None,
    gain: float = 0.75,
    filename: str = "tone.wav",
) -> Path:
    """
    Generate a tone by layering oscillators, then apply:
    filters → filter-envelope → amplifier-envelope → amplifier.

    Args:
        frequency: Hz
        duration: seconds
        oscillators: e.g. ["sine"], ["sine","saw"], ["square","saw"], etc.
        filters: list of callables that each take/return Samples
        fenv: a filter-envelope function (e.g., fenv_piano)
        aenv: an amplifier-envelope function (e.g., aenv_string)
        gain: amplifier clamp (<= 0.75 is enforced in amplifier())
        filename: output WAV name (saved in ./output/ via oscillators.write_wav)

    Returns:
        Path to the written WAV file.
    """
    # 1) Build oscillator layers
    layers: List[Samples] = []
    for name in oscillators:
        fn = _OSC_LOOKUP.get(name.lower())
        if fn is None:
            raise ValueError(f"Unknown oscillator: {name!r} (valid: {list(_OSC_LOOKUP)})")
        layers.append(fn(frequency=frequency, duration=duration))

    # 2) Mix layers
    mixed = _mix_layers(layers)

    # 3) Filters (before envelopes)
    mixed = _apply_filters(mixed, filters)

    # 4) Filter envelope (includes fade internally if using fenv_* family)
    if fenv is not None:
        mixed = fenv(mixed)

    # 5) Amplifier envelope (ADSR only)
    if aenv is not None:
        mixed = aenv(mixed)

    # 6) Amplifier clamp (0.75 max)
    mixed = amplifier(mixed, gain=gain)

    # 7) Write & play
    out_path = write_wav(filename, mixed)
    play_file(out_path)
    return out_path


# ----- Demo -----
if __name__ == "__main__":
    print("Demo 1: Single sine, gentle low-pass + piano filter-envelope + amp")
    play_tone(
        frequency=440.0,
        duration=2.0,
        oscillators=["sine"],
        filters=[
            lambda s: low_pass_one_pole(s, cutoff_hz=1500.0),
            dc_block,  # optional DC cleanup
        ],
        fenv=lambda s: fenv_piano(s, attack=0.01, decay=0.15, sustain=0.3, release=0.2),
        aenv=lambda s: aenv_piano(s, attack=0.02, decay=0.20, sustain=0.4, release=0.2),
        gain=0.75,
        filename="demo_sine_lp_piano.wav",
    )

    print("Demo 2: Layered sine + saw, HPF + string envelope, then amp")
    play_tone(
        frequency=220.0,
        duration=2.5,
        oscillators=["sine", "saw"],
        filters=[
            lambda s: high_pass_one_pole(s, cutoff_hz=80.0),
        ],
        fenv=lambda s: fenv_string(s, attack=0.08, decay=0.25, sustain=0.6, release=0.3),
        aenv=lambda s: aenv_string(s, attack=0.05, decay=0.20, sustain=0.6, release=0.3),
        gain=0.7,
        filename="demo_sine_saw_hp_string.wav",
    )

    print("Demo 3: Layered square + saw, LPF + drums envelope, then amp")
    play_tone(
        frequency=110.0,
        duration=1.5,
        oscillators=["square", "saw"],
        filters=[
            lambda s: low_pass_one_pole(s, cutoff_hz=1000.0),
        ],
        fenv=lambda s: fenv_drums(s, attack=0.003, decay=0.45, sustain=.1, release=0.18,fade_time=0.008),
        aenv=lambda s: aenv_drums(s, attack=0.003, decay=0.35, sustain=.1, release=0.2),
        gain=0.85,
        filename="demo_square_saw_lp_drums.wav",
    )

    print("Demos complete. Files saved in ./output/")

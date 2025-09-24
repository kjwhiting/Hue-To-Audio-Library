# composer_pixels.py
"""
Compose a song from an image's pixels.

Flow:
  Read file -> PixelHSV -> hue_to_frequency_true_color -> pixels_to_beats
  -> build N tracks from the tracks -> schedule notes on a steady beat
  -> synth chain (oscillators -> filters -> envelopes -> amplifier) -> WAV/play

Assumptions (kept simple on purpose):
- Time signature = 4/4 with a steady quarter-note beat.
- Each factor f creates a track that iterates pixels by stride f.
- For that track, each chosen pixel plays for f beats (2 beats when f=2, etc),
  as you described ("loop by 2 and play for 2 beats", and "do the same for other tracks").
- Lower tracks => drum-like envelopes; higher tracks => piano/pluck envelopes.
- Frequencies come from hue_to_frequency_true_color(PixelHSV).

Requires:
- pillow (for py image load)
- your local modules: oscillators.py, filters.py, envelopes.py, amplifiers.py, py
"""

from __future__ import annotations
from typing import List, Callable, Optional
import sys
import math
from src.converter import image_to_pixel_hsv, pixels_to_beats, hue_to_frequency_true_color, get_averages
from src.pixel_hsv import PixelHSV


# Local synth pieces
from src.synth.oscillators import SAMPLE_RATE, write_wav, play_file, sine_wave, square_wave, saw_wave
from src.synth.filters import low_pass_one_pole, high_pass_one_pole, dc_block
from src.synth.envelopes import fenv_piano, fenv_string, fenv_drums, aenv_piano, aenv_string, aenv_drums
from src.synth.amplifiers import amplifier

Samples = List[int]
OscFn = Callable[..., Samples]

OSC_LOOKUP = {
    "sine": sine_wave,
    "square": square_wave,
    "saw": saw_wave,
}

# ---------- tiny audio utils ----------
def seconds_to_samples(sec: float) -> int:
    return max(0, int(sec * SAMPLE_RATE))

def clip16(x: int) -> int:
    return -32768 if x < -32768 else 32767 if x > 32767 else x

def mix_into(buf: Samples, part: Samples, start: int) -> None:
    end = start + len(part)
    if end > len(buf):
        buf.extend([0] * (end - len(buf)))
    for i, s in enumerate(part):
        buf[start + i] = clip16(buf[start + i] + s)

def average_mix(layers: List[Samples]) -> Samples:
    if not layers:
        return []
    n = min(len(ch) for ch in layers)
    inv = 1.0 / len(layers)
    return [clip16(int(sum(ch[i] for ch in layers) * inv)) for i in range(n)]

# ---------- single note synth ----------
def synth_note(
    frequency: float,
    duration: float,
    oscillators: List[str],
    filters: Optional[List[Callable[[Samples], Samples]]] = None,
    fenv: Optional[Callable[[Samples], Samples]] = None,
    aenv: Optional[Callable[[Samples], Samples]] = None,
    gain: float = 0.75,
) -> Samples:
    layers: List[Samples] = []
    for name in oscillators:
        fn = OSC_LOOKUP.get(name)
        if fn is None:
            raise ValueError(f"Unknown oscillator: {name}")
        layers.append(fn(frequency=frequency, duration=duration))
    mixed = layers[0] if len(layers) == 1 else average_mix(layers)

    if filters:
        for f in filters:
            mixed = f(mixed)
    if fenv:
        mixed = fenv(mixed)  # fenv_* has built-in fade
    if aenv:
        mixed = aenv(mixed)  # aenv_* is ADSR only

    return amplifier(mixed, gain=gain)  # clamp to ≤0.75

# ---------- beat/time helpers ----------
def beat_seconds(bpm: int) -> float:
    # 4/4 quarter-note beat
    return 60.0 / bpm

# ---------- main composition from pixels ----------
def compose_from_image(
    image_path: str,
    base_osc_sets: Optional[List[List[str]]] = None,
) -> Samples:
    """
    Compose according to pixels and factor tracks.

    - Determines tracks, total beats, and song_length_minutes via pixels_to_beats.
    - Each factor f makes a track: iterate pixels by stride f; each selected pixel -> note of f beats.
    - Lower tracks get drum-ish treatment; higher tracks get piano/pluck-ish treatment.
    - Returns a single PCM16 sample array (mono).
    """
    # 1) Load & convert image to PixelHSV list
    w, h, pixels = image_to_pixel_hsv(image_path)
    saturation_average, value_average = get_averages(pixels)
    bpm = int(350 * value_average) # slower if non vibrant color


    # 2) Determine tracks / beats / song length (minutes)
    tracks = pixels_to_beats(saturation_average)
    total_seconds = 60
    total_samples = seconds_to_samples(total_seconds)
    master: Samples = [0] * total_samples
    print(bpm, saturation_average, value_average, len(pixels), tracks)

    beat_sec = beat_seconds(bpm)

    # 3) Choose oscillator sets if not provided (kept simple)
    if not base_osc_sets:
        base_osc_sets = [
            ["square"],         # percussive-ish
            ["sine"],           # pure
            ["saw"],            # bright
            ["sine", "saw"],    # hybrid
            ["sine", "square"], # hybrid
        ]

    # 4) Build tracks from tracks
    # Sort ascending; reserve smaller tracks for drum-like sounds.
    tracks_sorted = sorted(tracks)

    # Split “small” vs “large” around median
    mid = max(1, len(tracks_sorted) // 2)
    small_tracks = tracks_sorted[:mid]
    large_tracks = tracks_sorted[mid:]

    # Helper: pick treatment by factor group
    def drum_chain() -> tuple[list[str], list[Callable[[Samples], Samples]], Callable[[Samples], Samples], Callable[[Samples], Samples]]:
        oscs = ["square"]
        filts = [lambda s: high_pass_one_pole(s, cutoff_hz=80.0), dc_block]
        return oscs, filts, (lambda s: fenv_drums(s, attack=0.004, decay=0.12, sustain=0.02, release=0.07)), (
            lambda s: aenv_drums(s, attack=0.004, decay=0.12, sustain=0.02, release=0.09)
        )

    def piano_or_pluck_chain(ix: int) -> tuple[list[str], list[Callable[[Samples], Samples]], Callable[[Samples], Samples], Callable[[Samples], Samples]]:
        oscs = base_osc_sets[(ix) % len(base_osc_sets)]
        # mellow a tad; keep DC clean
        filts = [lambda s: low_pass_one_pole(s, cutoff_hz=1500.0), dc_block]
        # alternate piano/string feel
        if ix % 2 == 0:
            return oscs, filts, (lambda s: fenv_piano(s, attack=0.01, decay=0.18, sustain=0.35, release=0.22)), (
                lambda s: aenv_piano(s, attack=0.02, decay=0.18, sustain=0.4, release=0.22)
            )
        else:
            return oscs, filts, (lambda s: fenv_string(s, attack=0.06, decay=0.25, sustain=0.6, release=0.3)), (
                lambda s: aenv_string(s, attack=0.05, decay=0.20, sustain=0.55, release=0.27)
            )

    # 5) For each factor track, walk the pixels with stride=f and place notes of f beats
    # Frequency comes from hue_to_frequency_true_color(pixel)
    for idx, f in enumerate(tracks_sorted):
        is_drumy = f in small_tracks
        oscs, filts, fenv, aenv = (drum_chain() if is_drumy else piano_or_pluck_chain(idx))

        note_beats = f  # "play for 2 beats when stride 2; same for other tracks"
        note_sec = note_beats * beat_sec

        # stride through pixels
        for p_i in range(0, len(pixels), f):
            freq = hue_to_frequency_true_color(pixels[p_i])
            # generate note
            note = synth_note(
                frequency=freq,
                duration=note_sec,
                oscillators=oscs,
                filters=filts,
                fenv=fenv,
                aenv=aenv,
                gain=0.7,
            )
            # schedule on grid: each note occupies f beats; advance a per-track cursor
            # Track start positions interleave across tracks by aligning them to the same beat grid.
            # We map pixel index -> beat start = (p_i // f) * (f beats)
            beat_start_index = (p_i // f) * note_beats
            start_sample = seconds_to_samples(beat_start_index * beat_sec)
            if start_sample >= total_samples:
                break
            mix_into(master, note, start_sample)

    return master

# ---------- simple CLI/demo ----------
if __name__ == "__main__":
    path = "images/personal-artwork-4.jpg"

    print(f"Reading: {path}")
    song = compose_from_image(path, 120)

    out = write_wav("pixels_song.wav", song)
    play_file(out)
    print(f"Done. Wrote {out}")

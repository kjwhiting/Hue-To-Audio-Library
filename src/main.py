# src/main.py
"""
Orchestrator: Image -> PixelHSV -> Audio WAV

Pipeline:
  1) Load image -> (w, h, [PixelHSV]) via src.conversion.image_to_pixel_hsv
  2) Map:
       - hue (0..360, already inverted in PixelHSV) -> frequency in C2..C6
       - saturation (0..10_000) -> loudness 0..1
       - v code (0..13) -> rest or note duration (seconds) at BPM
  3) Render each pixel to PCM using src.composer.render_code_bytes / synth.synthesize_note
  4) Write a single WAV

CLI:
  python -m src.main --image path/to/file.jpg --out song.wav --bpm 120 --voice-strategy hue
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Literal, Tuple

from src.conversion import image_to_pixel_hsv
from src.pixel_hsv import PixelHSV
from src.composer import (
    compose_demo_bytes,  # handy for a quick sanity run
    write_wav,
    render_code_bytes,
    code_to_seconds,     # exposed if you need direct mapping
)
from src.synth import SAMPLE_RATE_DEFAULT, ALLOWED_VOICES

# ===== CONFIG / CONSTANTS (EDIT HERE) =========================================
DEFAULT_BPM = 120
DEFAULT_SAMPLE_RATE = SAMPLE_RATE_DEFAULT
DEFAULT_VOICE_STRATEGY: Literal["sine", "triangle", "bell", "cycle", "hue"] = "hue"
PIXEL_STRIDE = 1  # process every Nth pixel to shorten render time
LOUDNESS_MIN = 0.10
LOUDNESS_MAX = 1.00

# Musical range (inclusive)
MIDI_C2 = 36
MIDI_C6 = 84
A4_MIDI = 69
A4_FREQ = 440.0


# ===== MODEL / SERVICES (pure logic) ==========================================
def midi_to_hz(midi_note: int) -> float:
    """12-TET frequency for a MIDI note number."""
    return A4_FREQ * (2.0 ** ((midi_note - A4_MIDI) / 12.0))


def hue_to_midi(h_deg: int) -> int:
    """
    Map hue 0..360 to MIDI 36..84 (C2..C6).
    Uses a rounded chromatic mapping across the full range.
    """
    span = MIDI_C6 - MIDI_C2
    m = round(MIDI_C2 + (h_deg / 360.0) * span)
    if m < MIDI_C2:
        m = MIDI_C2
    elif m > MIDI_C6:
        m = MIDI_C6
    return m


def hue_to_freq_c2_c6(h_deg: int) -> float:
    """Convenience: hue -> MIDI in [C2,C6] -> Hz."""
    return midi_to_hz(hue_to_midi(h_deg))


def saturation_to_loudness(s_int: int) -> float:
    """
    Map saturation [0..10_000] -> loudness [0..1].
    Simple linear mapping with clamp and a floor to keep quiet parts audible.
    """
    x = max(0.0, min(1.0, s_int / 10_000.0))
    x = max(LOUDNESS_MIN, min(LOUDNESS_MAX, x))
    return x


def pick_voice(
    h_deg: int,
    index: int,
    strategy: Literal["sine", "triangle", "bell", "cycle", "hue"],
) -> str:
    """
    Choose a synth voice:
      - "sine"/"triangle"/"bell": fixed
      - "cycle": index-based rotation across allowed voices
      - "hue": partition hue wheel into 3 segments
    """
    if strategy in ALLOWED_VOICES:
        return strategy
    if strategy == "cycle":
        voices = sorted(ALLOWED_VOICES)
        return voices[index % len(voices)]
    # strategy == "hue"
    if h_deg < 120:
        return "sine"
    if h_deg < 240:
        return "triangle"
    return "bell"


def pixels_to_pcm(
    pixels: Iterable[PixelHSV],
    bpm: int,
    sample_rate: int,
    voice_strategy: Literal["sine", "triangle", "bell", "cycle", "hue"],
    stride: int = 1,
) -> bytes:
    """
    Convert a sequence of PixelHSV into a single PCM mono buffer.
    Uses composer.render_code_bytes to handle rests vs notes.
    """
    out = bytearray()
    for idx, px in enumerate(p for i, p in enumerate(pixels) if (i % max(1, stride) == 0)):
        freq = hue_to_freq_c2_c6(px.h_deg)
        loud = saturation_to_loudness(px.s)
        voice = pick_voice(px.h_deg, idx, strategy=voice_strategy)
        out += render_code_bytes(
            code=px.v,
            voice=voice,
            bpm=bpm,
            sample_rate=sample_rate,
            loudness=loud,
            freq_hz=freq,
        )
    return bytes(out)


# ===== CONTROLLER / CLI =======================================================
def compose_from_image(
    image_path: str | Path,
    out_wav: str | Path = "output.wav",
    bpm: int = DEFAULT_BPM,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    stride: int = PIXEL_STRIDE,
    voice_strategy: Literal["sine", "triangle", "bell", "cycle", "hue"] = DEFAULT_VOICE_STRATEGY,
) -> Path:
    """
    High-level convenience: read image, convert pixels, render audio, write WAV.
    Returns the output Path.
    """
    w, h, px = image_to_pixel_hsv(image_path)
    print(f"Loaded {image_path} -> {w}x{h} pixels (total {len(px)})")
    pcm = pixels_to_pcm(px, bpm=bpm, sample_rate=sample_rate, voice_strategy=voice_strategy, stride=stride)
    out = write_wav(out_wav, pcm, sample_rate)
    print(f"Wrote {out.resolve()}  (BPM={bpm}, SR={sample_rate}, stride={stride}, voice={voice_strategy})")
    return out


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Image → Sound composer")
    ap.add_argument("--image", "-i", required=False, help="Path to input image (jpg/png)")
    ap.add_argument("--out", "-o", default="output.wav", help="Output WAV path")
    ap.add_argument("--bpm", type=int, default=DEFAULT_BPM, help="Beats per minute")
    ap.add_argument("--sr", type=int, default=DEFAULT_SAMPLE_RATE, help="Sample rate (Hz)")
    ap.add_argument(
        "--voice-strategy",
        choices=["sine", "triangle", "bell", "cycle", "hue"],
        default=DEFAULT_VOICE_STRATEGY,
        help="How to choose voice per pixel",
    )
    ap.add_argument("--stride", type=int, default=PIXEL_STRIDE, help="Use every Nth pixel")
    ap.add_argument(
        "--demo",
        action="store_true",
        help="Ignore --image and render the built-in demo (each voice & duration)",
    )
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    if args.demo or not args.image:
        # Built-in sample: quick sanity file using composer’s demo
        print("No image specified or --demo provided; rendering built-in demo …")
        pcm = compose_demo_bytes(bpm=args.bpm, sample_rate=args.sr)
        out = write_wav(args.out, pcm, args.sr)
        print(f"Wrote {out.resolve()}  (BPM={args.bpm}, SR={args.sr})")
        return

    compose_from_image(
        image_path=Path(args.image),
        out_wav=Path(args.out),
        bpm=args.bpm,
        sample_rate=args.sr,
        stride=max(1, int(args.stride)),
        voice_strategy=args.voice_strategy,
    )


# ===== RUN INSTRUCTIONS =======================================================
# From repo root:
#   python -m src.main --demo
#   python -m src.main --image assets/picture.jpg --out song.wav --bpm 120 --voice-strategy hue --stride 2
if __name__ == "__main__":
    main()

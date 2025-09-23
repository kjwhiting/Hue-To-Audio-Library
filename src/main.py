# src/main.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Literal, Callable, Optional, Tuple, List

from src.conversion import image_to_pixel_hsv
from src.pixel_hsv import PixelHSV
from src.composer import (
    compose_demo_bytes,
    write_wav,
    render_code_bytes,
    code_to_seconds,
)
from src.synth import SAMPLE_RATE_DEFAULT, ALLOWED_VOICES

# ===== CONFIG / CONSTANTS (EDIT HERE) =========================================
DEFAULT_BPM = 120
DEFAULT_SAMPLE_RATE = SAMPLE_RATE_DEFAULT
DEFAULT_VOICE_STRATEGY: Literal["sine", "triangle", "bell", "cycle", "hue"] = "hue"
PIXEL_STRIDE = 1  # manual fixed stride when auto-stride is not used
LOUDNESS_MIN = 0.10
LOUDNESS_MAX = 1.00
DEFAULT_MAX_SECONDS = 60.0  # keep files ≤ ~1 minute by default

# Musical range
MIDI_C2 = 36
MIDI_C6 = 84
A4_MIDI = 69
A4_FREQ = 440.0


# ===== PROGRESS UTIL ==========================================================
def _make_console_progress(prefix: str = "Building audio") -> Callable[[int, int], None]:
    def cb(done: int, total: int) -> None:
        total = max(1, int(total))
        done = max(0, min(done, total))
        pct = int(round(done * 100 / total))
        msg = f"\r{prefix}: {pct:3d}% ({done}/{total})"
        print(msg, end="", file=sys.stderr, flush=True)
        if done >= total:
            print("", file=sys.stderr)
    return cb


# ===== MODEL / SERVICES (pure logic) ==========================================
def midi_to_hz(midi_note: int) -> float:
    return A4_FREQ * (2.0 ** ((midi_note - A4_MIDI) / 12.0))


def hue_to_midi(h_deg: int) -> int:
    span = MIDI_C6 - MIDI_C2
    m = round(MIDI_C2 + (h_deg / 360.0) * span)
    if m < MIDI_C2:
        m = MIDI_C2
    elif m > MIDI_C6:
        m = MIDI_C6
    return m


def hue_to_freq_c2_c6(h_deg: int) -> float:
    return midi_to_hz(hue_to_midi(h_deg))


def saturation_to_loudness(s_int: int) -> float:
    x = max(0.0, min(1.0, s_int / 10_000.0))
    x = max(LOUDNESS_MIN, min(LOUDNESS_MAX, x))
    return x


def pick_voice(
    h_deg: int,
    index: int,
    strategy: Literal["sine", "triangle", "bell", "cycle", "hue"],
) -> str:
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


# ===== AUTO-STRIDE HELPERS ====================================================
def _selected_duration(pixels: List[PixelHSV], stride: int, bpm: int) -> float:
    """Total seconds for pixels at positions i % stride == 0."""
    s = 0.0
    step = max(1, stride)
    for i, px in enumerate(pixels):
        if i % step == 0:
            s += code_to_seconds(px.v, bpm)
    return s


def estimate_auto_stride(
    pixels: List[PixelHSV],
    bpm: int,
    max_seconds: float,
) -> Tuple[int, int, float]:
    """
    Pick the smallest stride >= 1 such that the decimated set fits under max_seconds.
    Returns (stride, selected_count, selected_seconds).
    """
    if max_seconds <= 0:
        return max(1, len(pixels)), 0, 0.0

    # If the full thing already fits, stride=1.
    full = sum(code_to_seconds(px.v, bpm) for px in pixels)
    if full <= max_seconds:
        return 1, len(pixels), full

    # Initial guess using total duration ratio (ceil).
    guess = max(1, int((full + max_seconds - 1) // max_seconds))
    stride = guess

    # Refine upward until the actual decimated duration fits.
    while True:
        total = _selected_duration(pixels, stride, bpm)
        if total <= max_seconds:
            # Count how many pixels survive this stride
            cnt = (len(pixels) + stride - 1) // stride
            return stride, cnt, total
        stride += 1  # increase sparsity and re-check


def _decimate(pixels: List[PixelHSV], stride: int) -> List[PixelHSV]:
    step = max(1, stride)
    return [px for i, px in enumerate(pixels) if i % step == 0]


def pixels_to_pcm(
    pixels: Iterable[PixelHSV],
    bpm: int,
    sample_rate: int,
    voice_strategy: Literal["sine", "triangle", "bell", "cycle", "hue"],
    stride: int = 1,
    *,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    render_fn: Callable[[int, str, int, int, float, float], bytes] = render_code_bytes,
    max_seconds: Optional[float] = None,
) -> bytes:
    """
    Convert a sequence of PixelHSV into a single PCM mono buffer.

    If max_seconds is set and the next item would exceed it, we stop (truncate).
    """
    if not isinstance(pixels, list):
        pixels = list(pixels)
    total = (len(pixels) + max(1, stride) - 1) // max(1, stride)
    step = max(1, total // 100)

    out = bytearray()
    done = 0
    elapsed = 0.0

    for i, px in enumerate(pixels):
        if i % max(1, stride) != 0:
            continue

        dur = code_to_seconds(px.v, bpm)
        if (max_seconds is not None) and (elapsed + dur > max_seconds):
            break

        freq = hue_to_freq_c2_c6(px.h_deg)
        loud = saturation_to_loudness(px.s)
        voice = pick_voice(px.h_deg, done, strategy=voice_strategy)

        out += render_fn(px.v, voice, bpm, sample_rate, loud, freq)
        elapsed += dur
        done += 1

        if progress_cb and (done % step == 0 or done == total):
            progress_cb(done, total)

    if progress_cb and done < total:
        progress_cb(done, total)
    return bytes(out)


# ===== CONTROLLER / CLI =======================================================
def compose_from_image(
    image_path: str | Path,
    out_wav: str | Path = "output.wav",
    bpm: int = DEFAULT_BPM,
    sample_rate: int = SAMPLE_RATE_DEFAULT,
    stride: int = PIXEL_STRIDE,
    voice_strategy: Literal["sine", "triangle", "bell", "cycle", "hue"] = DEFAULT_VOICE_STRATEGY,
    *,
    show_progress: bool = True,
    max_seconds: Optional[float] = DEFAULT_MAX_SECONDS,
    auto_stride: bool = False,
) -> Path:
    w, h, px = image_to_pixel_hsv(image_path)
    print(f"Loaded {image_path} -> {w}x{h} pixels (total {len(px)})")

    # Auto-stride: decimate upfront to sample across the whole image
    if auto_stride and max_seconds:
        stride, kept, est_sec = estimate_auto_stride(px, bpm, max_seconds)
        print(f"Auto-stride selected stride={stride} (kept ~{kept} pixels, est {est_sec:.2f}s) to fit ≤{max_seconds}s")
        px = _decimate(px, stride)
        # After decimation we still keep the cap for safety, but it should already fit.
        stride = 1  # we already decimated; render everything left
    else:
        stride = max(1, stride)

    progress_cb = _make_console_progress() if show_progress else None
    pcm = pixels_to_pcm(
        px,
        bpm=bpm,
        sample_rate=sample_rate,
        voice_strategy=voice_strategy,
        stride=stride,
        progress_cb=progress_cb,
        max_seconds=max_seconds,
    )
    out = write_wav(out_wav, pcm, sample_rate)
    print(
        f"Wrote {out.resolve()}  (BPM={bpm}, SR={sample_rate}, stride={stride}, "
        f"voice={voice_strategy}, max_seconds={max_seconds}, auto_stride={auto_stride})"
    )
    return out


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Image → Sound composer")
    ap.add_argument("--image", "-i", required=False, help="Path to input image (jpg/png)")
    ap.add_argument("--out", "-o", default="output.wav", help="Output WAV path")
    ap.add_argument("--bpm", type=int, default=DEFAULT_BPM, help="Beats per minute")
    ap.add_argument("--sr", type=int, default=SAMPLE_RATE_DEFAULT, help="Sample rate (Hz)")
    ap.add_argument(
        "--voice-strategy",
        choices=["sine", "triangle", "bell", "cycle", "hue"],
        default=DEFAULT_VOICE_STRATEGY,
        help="How to choose voice per pixel",
    )
    ap.add_argument("--stride", type=int, default=PIXEL_STRIDE, help="Use every Nth pixel")
    ap.add_argument("--demo", action="store_true", help="Render the built-in demo (ignore --image)")
    ap.add_argument("--no-progress", action="store_true", help="Disable console progress updates")
    ap.add_argument(
        "--max-seconds", type=float, default=DEFAULT_MAX_SECONDS,
        help="Hard cap on output duration (seconds).",
    )
    ap.add_argument(
        "--auto-stride", action="store_true",
        help="Sample evenly across the whole image by auto-decimation to fit within --max-seconds.",
    )
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    if args.demo or not args.image:
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
        show_progress=not args.no_progress,
        max_seconds=args.max_seconds,
        auto_stride=args.auto_stride,
    )


if __name__ == "__main__":
    main()

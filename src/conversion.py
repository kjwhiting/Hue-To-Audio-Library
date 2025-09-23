from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import colorsys
import math

from src.pixel_hsv import PixelHSV  # NEW: use your strict data class

# ===== AUDIO BED DEFAULTS (EDIT HERE) =====
# Steady, subtle bass pulse to sit under the main render.
BASS_BED_BPM_DEFAULT = 84          # gentle head-nodding tempo
BASS_BED_SUBDIVISION = 2           # 2 = eighth notes at given BPM
BASS_PULSE_MS = 110                # length of each thump (ms)
BASS_GAP_MS = 15                   # tiny gap between pulses (ms)
BASS_ROOT_HZ = 55.0                # A1 ≈ 55 Hz; sits under most content
BASS_LOUDNESS_ONBEAT = 0.22        # main thump (0..1, scaled by synth HEADROOM)
BASS_LOUDNESS_OFFBEAT = 0.16       # softer off-beat
BASS_SAMPLE_RATE = 44_100          # keep in sync with synth default


def read_image_rgb(path: str | Path) -> Tuple[int, int, List[Tuple[int, int, int]]]:
    # (unchanged from earlier message)
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    try:
        from PIL import Image, ImageOps  # type: ignore
    except Exception as e:
        raise ImportError("Pillow is required: pip install pillow") from e
    try:
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            w, h = im.size
            pixels = list(im.getdata())
            if len(pixels) != w * h:
                raise ValueError("Pixel data length mismatch after RGB conversion")
            return w, h, pixels
    except OSError as e:
        raise ValueError(f"Failed to open/read image: {p.name}") from e


def rgb_to_hsv_scaled(r: int, g: int, b: int) -> Tuple[int, int, float]:
    """
    RGB (0..255) -> (h_deg:0..360 int, s_int:0..10_000 int, v_float:0..1)
    """
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
        raise ValueError("RGB components must be integers in 0..255")

    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

    h_deg = int(round(h * 360.0))
    if h_deg < 0:
        h_deg = 0
    elif h_deg > 360:
        h_deg = 360

    s_int = int(round(s * 10_000.0))
    if s_int < 0:
        s_int = 0
    elif s_int > 10_000:
        s_int = 10_000

    return h_deg, s_int, float(v)


def image_to_pixel_hsv(path: str | Path) -> Tuple[int, int, List[PixelHSV]]:
    """
    Read an image, convert each pixel to PixelHSV, and return:
      (width, height, [PixelHSV, ...]) in row-major order.
    """
    w, h, pixels = read_image_rgb(path)
    out: List[PixelHSV] = []
    for (r, g, b) in pixels:
        h_deg, s_int, v_float = rgb_to_hsv_scaled(r, g, b)
        out.append(PixelHSV(h_deg, s_int, v_float))
    return w, h, out


# ===== AUDIO: Steady bass rhythm bed =====
def _frames_for_seconds(seconds: float, sample_rate: int) -> int:
    return max(0, int(round(seconds * sample_rate)))


def _ms(ms: int) -> float:
    return ms / 1000.0

def render_bass_pulse_bed(
    duration_s: float,
    *,
    bpm: int = BASS_BED_BPM_DEFAULT,
    subdivision: int = BASS_BED_SUBDIVISION,
    root_hz: float = BASS_ROOT_HZ,
    sample_rate: int = BASS_SAMPLE_RATE,
    pulse_ms: int = BASS_PULSE_MS,
    gap_ms: int = BASS_GAP_MS,
    loud_on: float = BASS_LOUDNESS_ONBEAT,
    loud_off: float = BASS_LOUDNESS_OFFBEAT,
) -> bytes:
    """
    Render a steady, muted bass rhythm (PCM16 mono) to layer under your main WAV.

    This version is frame-locked (sample-accurate) to eliminate timing drift:
      - All durations converted to integer frame counts.
      - Each pulse period is exactly the same number of frames.
    """
    if duration_s <= 0:
        return b""

    from src.synth import synthesize_note  # lazy import

    # --- Grid math (frame-locked) ---
    pulses_per_second = (bpm / 60.0) * max(1, subdivision)
    period_frames = max(1, int(round(sample_rate / pulses_per_second)))

    note_frames = max(1, int(round(sample_rate * (pulse_ms / 1000.0))))
    gap_frames_cfg = max(0, int(round(sample_rate * (gap_ms / 1000.0))))

    # Ensure the pulse (note + gap) fits into one period; shrink note if needed
    if note_frames + gap_frames_cfg >= period_frames:
        note_frames = max(1, period_frames - max(0, gap_frames_cfg) - 1)

    # Precompute one period worth of audio for ON and OFF beats
    def make_period(loud: float) -> bytes:
        note = synthesize_note(
            freq_hz=root_hz,
            duration_s=note_frames / sample_rate,
            loudness=loud,
            voice="bass",
            sample_rate=sample_rate,
        )
        # Fill: gap (config) + remaining rest to reach exact period
        produced_frames = len(note) // 2
        gap_frames = min(gap_frames_cfg, max(0, period_frames - produced_frames))
        rest_frames = max(0, period_frames - (produced_frames + gap_frames))
        return note + (b"\x00\x00" * gap_frames) + (b"\x00\x00" * rest_frames)

    period_on = make_period(loud_on)
    period_off = make_period(loud_off)

    # Build full length by repeating periods exactly
    target_frames = int(round(duration_s * sample_rate))
    target_bytes = target_frames * 2

    chunks: List[bytes] = []
    pulse_index = 0
    frames_accum = 0

    while frames_accum < target_frames:
        onbeat = (pulse_index % subdivision) == 0
        block = period_on if onbeat else period_off
        # If the next full period would exceed target, trim it
        remaining_bytes = target_bytes - (frames_accum * 2)
        if len(block) > remaining_bytes:
            block = block[:remaining_bytes]
        chunks.append(block)
        frames_accum += len(block) // 2
        pulse_index += 1

    audio = b"".join(chunks)
    # Pad if needed (rare due to trimming above)
    if len(audio) < target_bytes:
        audio += b"\x00\x00" * ((target_bytes - len(audio)) // 2)

    return audio


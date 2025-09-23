# src/conversion.py
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import colorsys
import math

from src.pixel_hsv import PixelHSV  # NEW: use your strict data class


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

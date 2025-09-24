from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from src.pixel_hsv import PixelHSV


def read_image_rgb(path: str | Path) -> Tuple[int, int, List[Tuple[int, int, int]]]:
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
                raise ValueError("Pixel data length mismatch after RGB converter")
            return w, h, pixels
    except OSError as e:
        raise ValueError(f"Failed to open/read image: {p.name}") from e


def image_to_pixel_hsv(path):
    """
    Read an image, convert each pixel to PixelHSV, and return:
      (width, height, [PixelHSV, ...]) in row-major order.
    """
    w, h, pixels = read_image_rgb(path)
    out = []
    for (r, g, b) in pixels:
        out.append(PixelHSV(r,g,b))
    return w, h, out





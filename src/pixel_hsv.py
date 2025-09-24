
from __future__ import annotations
import math
import colorsys

from PIL import Image
import os
from math import floor


class PixelHSV:
    def __init__(self, r,g,b):
        h,s,v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self.h_deg = PixelHSV.hue_inversion(h)
        self.h = h
        self.s = s
        self.v = v

    def __repr__(self):
        return f"PixelHSV(h_deg={self.h_deg}, s={self.s}, v={self.v})"

    def __eq__(self, other):
        if not isinstance(other, PixelHSV):
            return NotImplemented
        return (
            math.isclose(self.h, other.h) and math.isclose(self.s, other.s) and math.isclose(self.v, other.v)
        ) 

    @staticmethod
    def hue_inversion(h):
        """Reverse hue direction on the to pair with physical light."""
        return 1- h




def make_hsv_hue_sweep_jpg(
    output_path: str = "output/hue_sweep.jpg",
    width: int = 1000,          # 1000 hues: 0.000..0.999 (step 0.001)
    height: int = 50,           # any visible height
    quality: int = 95
) -> str:
    """
    Create and save a JPEG where each column's hue is the next 0.001 step in HSV.

    Everything is done in this single function:
    - builds RGB pixels from HSV (S=1, V=1)
    - creates the image with Pillow
    - writes output JPEG (creates folder if needed)
    - returns the output path string
    """

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")

    # Build one scanline of 1000 hues: h = x/1000 for x in [0..999]
    # Keep last hue at 0.999 (not 1.0) so it doesn't wrap back to red.
    hues = []
    for x in range(width):
        # For exact 0.001 increments across 1000 columns use x/1000
        # If width != 1000, still distribute across [0,1) proportionally.
        h = x / 1000 if width == 1000 else (x / width)
        if h >= 1.0:
            h = 0.999999
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        hues.append((int(round(r * 255)), int(round(g * 255)), int(round(b * 255))))

    # Make full image by repeating the scanline 'height' times
    pixels = hues * height

    img = Image.new("RGB", (width, height))
    img.putdata(pixels)

    # Ensure folder exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, format="JPEG", quality=quality, optimize=True)
    return output_path


if __name__ == "__main__":
    path = make_hsv_hue_sweep_jpg()
    print(f"Wrote {path}")


# src/helper.py
from __future__ import annotations

import colorsys
from pathlib import Path
from typing import Dict, List, Tuple
from src.pixel_hsv import PixelHSV


def _require_pillow():
    try:
        from PIL import Image  # type: ignore
        return Image
    except Exception as e:
        raise ImportError("Pillow is required. Install with: pip install pillow") from e


def _hsv_to_rgb_bytes(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    h,s,v in [0,1] -> (r,g,b) in 0..255 ints
    """
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def _save_jpeg(path: Path, pixels: List[Tuple[int, int, int]], w: int, h: int) -> Path:
    Image = _require_pillow()
    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    # High quality, no chroma subsampling to reduce artifacts
    img.save(path, format="JPEG", quality=95, subsampling=0, optimize=True)
    return path


def _values_v_for_code(code: int) -> float:
    if code < 0 or code > 13:
        raise ValueError("code must be in 0..13")

    if code == 0:
        return 0.0
    if 1 <= code <= 6:
        # 6 bins across (0, 0.25]; midpoint of bin k (1..6)
        k = code
        low = ((k - 1) / 6.0) * 0.25
        high = (k / 6.0) * 0.25
        return (low + high) / 2.0  # strictly < 0.25
    # 7..13
    if code == 13:
        return 1.0
    j = code - 7 + 1  # 1..6 for codes 7..12 (we handle 13 above)
    low = (j - 1) / 7.0
    high = j / 7.0
    t = (low + high) / 2.0
    return 0.25 + 0.75 * t


def create_test_jpgs(output_dir: str | Path = "test_images") -> Dict[str, Path]:
    """
    Create three JPEGs for manual testing:

      hues.jpg         : width 361, 1 pixel per hue degree (0..360), s=1, v=1
      values.jpg       : width 14,  1 pixel per value code (0..13), h=0, s=1
      saturations.jpg  : width 10001, 1 pixel per saturation step (0..10_000), h=0, v=1

    Returns a dict of {name: Path}.
    """
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ---- 1) Hues: 0..360 ----
    hue_pixels: List[Tuple[int, int, int]] = []
    for deg in range(0, 361):
        h = (deg % 360) / 360.0  # 360 maps to 0
        hue_pixels.append( _hsv_to_rgb_bytes(h, 1.0, 1.0))
    hues_path = _save_jpeg(outdir / "hues.jpg", hue_pixels, w=361, h=1)

    # ---- 2) Values: codes 0..13 at hue=0, sat=1 ----
    value_pixels: List[Tuple[int, int, int]] = []
    for code in range(0, 14):
        v = _values_v_for_code(code)
        value_pixels.append(_hsv_to_rgb_bytes(0.0, 1.0, v))
    values_path = _save_jpeg(outdir / "values.jpg", value_pixels, w=14, h=1)

    # ---- 3) Saturations: 0..10_000 at hue=0, value=1 ----
    sat_pixels: List[Tuple[int, int, int]] = []
    for s_int in range(0, 10_001):
        s = s_int / 10_000.0
        sat_pixels.append(_hsv_to_rgb_bytes(0.0, s, 1.0))
    sats_path = _save_jpeg(outdir / "saturations.jpg", sat_pixels, w=10_001, h=1)

    return {"hues": hues_path, "values": values_path, "saturations": sats_path}


if __name__ == "__main__":
    paths = create_test_jpgs()
    for name, path in paths.items():
        print(f"Created {name}: {path.resolve()}")

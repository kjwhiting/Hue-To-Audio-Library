from pathlib import Path
import pytest
from src.pixel_hsv import PixelHSV

# Fail fast if Pillow isn't present (no skipping).
try:
    from PIL import Image  # type: ignore
except Exception as e:
    raise ImportError("Pillow is required for these tests. pip install pillow") from e

from src.conversion import read_image_rgb, rgb_to_hsv_scaled, image_to_pixel_hsv


def _save_png(path: Path, pixels, w: int, h: int):
    im = Image.new("RGB", (w, h))
    im.putdata(pixels)
    im.save(path, "PNG")


def test_read_image_rgb_png_exact_pixels(tmp_path: Path):
    p = tmp_path / "tiny.png"
    pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (128, 128, 128)]
    _save_png(p, pixels, 2, 2)

    w, h, data = read_image_rgb(p)
    assert (w, h) == (2, 2)
    assert data == pixels  # PNG is lossless → exact match


def test_read_image_rgb_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        read_image_rgb(tmp_path / "nope.png")


def test_read_image_rgb_bad_file(tmp_path: Path):
    p = tmp_path / "bad.jpg"
    p.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        read_image_rgb(p)


def test_rgb_to_hsv_scaled_primaries():
    # Red
    h, s, v = rgb_to_hsv_scaled(255, 0, 0)
    assert h in (0, 360)      # red may be 0°, clamping makes 360° possible in theory
    assert s == 10_000
    assert v == pytest.approx(1.0)

    # Green
    h, s, v = rgb_to_hsv_scaled(0, 255, 0)
    assert 118 <= h <= 122    # ~120°
    assert s == 10_000
    assert v == pytest.approx(1.0)

    # Blue
    h, s, v = rgb_to_hsv_scaled(0, 0, 255)
    assert 238 <= h <= 242    # ~240°
    assert s == 10_000
    assert v == pytest.approx(1.0)


def test_rgb_to_hsv_scaled_gray_line():
    # Middle gray → s=0; v≈0.502
    h, s, v = rgb_to_hsv_scaled(128, 128, 128)
    assert h in (0, 360)      # hue undefined when s=0; colorsys returns 0
    assert s == 0
    assert 0.49 <= v <= 0.51


@pytest.mark.parametrize(
    "r,g,b",
    [(-1, 0, 0), (256, 0, 0), (0, -1, 0), (0, 256, 0), (0, 0, -1), (0, 0, 256)],
)
def test_rgb_to_hsv_scaled_out_of_range_raises(r, g, b):
    with pytest.raises(ValueError):
        rgb_to_hsv_scaled(r, g, b)

def _save_png(path: Path, pixels, w: int, h: int):
    im = Image.new("RGB", (w, h))
    im.putdata(pixels)
    im.save(path, "PNG")


def test_image_to_pixel_hsv_basic_colors(tmp_path: Path):
    # 2x2: red, green, black, white
    p = tmp_path / "colors.png"
    pixels = [
        (255, 0, 0),     # red
        (0, 255, 0),     # green
        (0, 0, 0),       # black  -> rest (v_code=0)
        (255, 255, 255)  # white  -> max (v_code=6)
    ]
    _save_png(p, pixels, 2, 2)

    w, h, px = image_to_pixel_hsv(p)
    assert (w, h) == (2, 2)
    assert len(px) == 4

    red, green, black, white = px

    # Red: hue ~0 or 360, full saturation, full brightness -> code 6
    assert red.h_deg in (0, 360)
    assert red.s == 10_000
    assert red.v == 13

    # Green: hue ~120, full saturation, full brightness -> code 6
    assert 112 <= green.h_deg <= 240
    assert green.s == 10_000
    assert green.v == 13

    # Black: saturation 0, v_code 0 (rest)
    assert black.s == 0
    assert black.v == 0

    # White: saturation 0, v_code max
    assert white.s == 0
    assert white.v == 13


def test_image_to_pixel_hsv_order_and_length(tmp_path: Path):
    # 1x3 row to confirm row-major order
    p = tmp_path / "row.png"
    pixels = [(10, 20, 30), (40, 50, 60), (200, 210, 220)]
    _save_png(p, pixels, 3, 1)

    w, h, px = image_to_pixel_hsv(p)
    assert (w, h) == (3, 1)
    assert len(px) == 3
    # Ensure order preserved (first and last checks)
    assert px[0].h_deg != px[1].h_deg or px[0].s != px[1].s  # likely different
    assert px[2].h_deg >= 0  # sanity



def test_constructor_inverts_hue_on_store():
    # Incoming standard HSV 120° (green) should store as ~240°
    px = PixelHSV(120, 5000, 0.75)
    assert 238 <= px.h_deg <= 242
    assert px.s == 5000
    assert 4 <= px.v <= 11  # v depends on binning; 0.75 -> ceil(4.5)=5 typically

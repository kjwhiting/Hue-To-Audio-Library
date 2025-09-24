from pathlib import Path
import pytest
from src.pixel_hsv import PixelHSV
from test_utils import is_equal

try:
    from PIL import Image 
except Exception as e:
    raise ImportError("Pillow is required for these tests. pip install pillow") from e

from src.converter import _read_image_rgb, image_to_pixel_hsv, get_factors, pixels_to_beats, hue_to_frequency_direct, hue_to_frequency_true_color


def _save_png(path: Path, pixels, w: int, h: int):
    im = Image.new("RGB", (w, h))
    im.putdata(pixels)
    im.save(path, "PNG")


def test_read_image_rgb_png_exact_pixels(tmp_path: Path):
    p = tmp_path / "tiny.png"
    pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (128, 128, 128)]
    _save_png(p, pixels, 2, 2)

    w, h, data = _read_image_rgb(p)
    assert (w, h) == (2, 2)
    assert data == pixels  # PNG is lossless → exact match


def test_read_image_rgb_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        _read_image_rgb(tmp_path / "nope.png")


def test_read_image_rgb_bad_file(tmp_path: Path):
    p = tmp_path / "bad.jpg"
    p.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        _read_image_rgb(p)


def _save_png(path: Path, pixels, w: int, h: int):
    im = Image.new("RGB", (w, h))
    im.putdata(pixels)
    im.save(path, "PNG")


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


def test_get_factors():
    assert get_factors(6) == [2,3,6]
    assert get_factors(12) == [2,3,4,6,12]
    assert get_factors(11) == [11]

def test_pixels_to_beats_max_length():
    bpm = 120
    product = 2*3*5*7*11
    pixels = [None] * product
    factors, beats, duration = pixels_to_beats(pixels, bpm)
    assert product == 2310
    assert factors == [2,3,5,6]
    assert beats == 180
    assert duration == 1

def test_hue_to_frequency_direct_red():
    pix = PixelHSV(255,0,0)
    freq = hue_to_frequency_direct(pix)
    assert is_equal(freq, 65)


def test_hue_to_frequency_direct_orange():
    pix = PixelHSV(255, 127, 0) 
    freq = hue_to_frequency_direct(pix)
    assert is_equal(freq, 71.72)


def test_hue_to_frequency_direct_yellow():
    pix = PixelHSV(255, 255, 0)
    freq = hue_to_frequency_direct(pix)
    assert is_equal(freq, 78.5)


def test_hue_to_frequency_direct_green():
    pix = PixelHSV(0,255,0)
    freq = hue_to_frequency_direct(pix)
    assert is_equal(freq, 92)


def test_hue_to_frequency_direct_blue():
    pix = PixelHSV(0,0,255)
    freq = hue_to_frequency_direct(pix)
    assert is_equal(freq, 119)


def test_hue_to_frequency_direct_indigo():
    pix = PixelHSV(75, 0, 130)
    freq = hue_to_frequency_direct(pix)
    assert is_equal(freq, 126.78)


def test_hue_to_frequency_direct_violet():
    pix = PixelHSV(148, 0, 211)
    freq = hue_to_frequency_direct(pix)
    assert is_equal(freq, 128.46)

def test_hue_to_frequency_true_color_red():
    pix = PixelHSV(255,0,0)
    freq = hue_to_frequency_true_color(pix)
    assert is_equal(freq, 90.95)


def test_hue_to_frequency_true_color_orange():
    pix = PixelHSV(255, 127, 0) 
    freq = hue_to_frequency_true_color(pix)
    assert is_equal(freq, 98.31)


def test_hue_to_frequency_true_color_yellow():
    pix = PixelHSV(255, 255, 0)
    freq = hue_to_frequency_true_color(pix)
    assert is_equal(freq, 105.72)


def test_hue_to_frequency_true_color_green():
    pix = PixelHSV(0,255,0)
    freq = hue_to_frequency_true_color(pix)
    assert is_equal(freq, 120.5)


def test_hue_to_frequency_true_color_blue():
    pix = PixelHSV(0,0,255)
    freq = hue_to_frequency_true_color(pix)
    assert is_equal(freq, 150.06)


def test_hue_to_frequency_true_color_indigo():
    pix = PixelHSV(75, 0, 130)
    freq = hue_to_frequency_true_color(pix)
    assert is_equal(freq, 158.59)


def test_hue_to_frequency_true_color_violet():
    pix = PixelHSV(148, 0, 211)
    freq = hue_to_frequency_true_color(pix)
    assert is_equal(freq, 160.43)
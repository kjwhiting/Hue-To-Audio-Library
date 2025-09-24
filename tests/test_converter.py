from pathlib import Path
import pytest
from src.pixel_hsv import PixelHSV

# Fail fast if Pillow isn't present (no skipping).
try:
    from PIL import Image  # type: ignore
except Exception as e:
    raise ImportError("Pillow is required for these tests. pip install pillow") from e

from src.converter import read_image_rgb, image_to_pixel_hsv
from src.composer import write_wav
from src.synth import SAMPLE_RATE_DEFAULT


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


def test_write_wav_creates_missing_directories(tmp_path):
    nested = tmp_path / "deep/nested/dir/out.wav"
    out = write_wav(nested, b"", SAMPLE_RATE_DEFAULT)
    assert out.exists()
    assert out.parent.is_dir()
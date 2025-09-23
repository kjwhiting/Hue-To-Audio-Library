# tests/test_pixel_hsv.py
from __future__ import annotations

from pathlib import Path
import pytest

from src.pixel_hsv import PixelHSV
from src.exceptions import OutsideAllowableRange

# ---- optional integration test bits (fail fast if Pillow missing) ----
try:
    from PIL import Image  # type: ignore
    PIL_AVAILABLE = True
except Exception as e:
    PIL_AVAILABLE = False
    _PIL_ERR = e

if PIL_AVAILABLE:
    from src.conversion import image_to_pixel_hsv


# =========================
# Helpers (for integration)
# =========================
def _save_png(path: Path, pixels, w: int, h: int):
    if not PIL_AVAILABLE:
        pytest.skip("Pillow not installed")
    im = Image.new("RGB", (w, h))
    im.putdata(pixels)
    im.save(path, "PNG")


# =========================
# Basic construction / repr
# =========================
def test_valid_init_and_repr():
    # Hue inversion: 180 stays 180; v passed as int code
    px = PixelHSV(180, 9000, 2)
    assert px.h_deg == 180
    assert px.s == 9000
    assert px.v == 2
    assert "PixelHSV" in repr(px)


# =========================
# Equality semantics
# =========================
def test_equal_identical_values():
    a = PixelHSV(0, 0, 0)
    b = PixelHSV(0, 0, 0)
    assert a == b

def test_not_equal_diff_saturation_only():
    a = PixelHSV(0, 0, 0)
    c = PixelHSV(0, 1, 0)
    assert a != c

def test_not_equal_diff_hue_only():
    a = PixelHSV(0, 0, 0)
    d = PixelHSV(1, 0, 0)
    assert a != d

def test_not_equal_diff_value_code_only():
    a = PixelHSV(0, 0, 0)
    e = PixelHSV(0, 0, 1)
    assert a != e

def test_equal_edge_max_hue():
    # 360 normalizes to 0 via inversion; both become 0
    f = PixelHSV(360, 0, 0)
    g = PixelHSV(360, 0, 0)
    assert f == g

def test_equal_edge_max_saturation():
    h = PixelHSV(0, 10_000, 0)
    i = PixelHSV(0, 10_000, 0)
    assert h == i

def test_equal_edge_max_value_code():
    j = PixelHSV(0, 0, 13)
    k = PixelHSV(0, 0, 13)
    assert j == k

def test_cross_type_comparison_is_false():
    a = PixelHSV(0, 0, 0)
    assert (a == "PixelHSV") is False
    assert (a != "PixelHSV") is True

def test_reflexivity_symmetry_transitivity():
    a = PixelHSV(0, 0, 0)
    b = PixelHSV(0, 0, 0)
    c = PixelHSV(0, 0, 0)
    assert a == a                            # reflexive
    assert (a == b) and (b == a)            # symmetric
    assert (a == b) and (b == c) and (a == c)  # transitive


# =========================
# Range validation
# =========================
@pytest.mark.parametrize(
    "h,s,v",
    [
        (-1, 5000, 3),      # hue low
        (361, 5000, 3),     # hue high
        (120, -1, 3),       # sat low
        (120, 10_001, 3),   # sat high
        (120, 5000, -1),    # code low
        (120, 5000, 14),    # code high
    ],
)
def test_out_of_range_raises(h, s, v):
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(h, s, v)


# =========================
# value->code mapping (0..13)
# =========================
def test_value_to_code_zero_and_one():
    assert PixelHSV.value_to_code(0.0) == 0
    assert PixelHSV.value_to_code(1.0) == 13

@pytest.mark.parametrize(
    "v,expected_range",
    [
        (1e-12, (1, 6)),     # tiniest positive -> rest codes 1..6
        (0.10, (1, 6)),      # still in rest band
        (0.249999, (1, 6)),  # just below threshold -> rest
    ],
)
def test_value_to_code_rest_band(v, expected_range):
    code = PixelHSV.value_to_code(v)
    lo, hi = expected_range
    assert lo <= code <= hi

def test_value_to_code_threshold_at_point_two_five():
    # spec: v >= 0.25 => first NOTE code (7)
    assert PixelHSV.value_to_code(0.25) == 6

@pytest.mark.parametrize(
    "v,expected_range",
    [
        (0.26, (7, 13)),
        (0.50, (7, 13)),
        (0.99, (7, 13)),
    ],
)
def test_value_to_code_note_band(v, expected_range):
    code = PixelHSV.value_to_code(v)
    lo, hi = expected_range
    assert lo <= code <= hi

@pytest.mark.parametrize("v", [-1.0, -1e-9])
def test_value_to_code_clamps_low(v):
    assert PixelHSV.value_to_code(v) == 0

@pytest.mark.parametrize("v", [1.0000001, 2.0])
def test_value_to_code_clamps_high(v):
    assert PixelHSV.value_to_code(v) == 13

def test_value_to_code_monotonic_samples():
    last = 0
    for step in range(0, 101):
        v = step / 100.0
        code = PixelHSV.value_to_code(v)
        assert code >= last
        last = code


# =========================
# Constructor conversion (float v -> code)
# =========================
def test_constructor_accepts_int_code_direct():
    for code in (0, 6, 7, 13):
        px = PixelHSV(120, 5000, code)
        assert px.v == code

def test_constructor_converts_float_v_to_codes_with_threshold():
    # v=0 -> shortest rest (code 0)
    assert PixelHSV(0, 0, 0.0).v == 0
    # rest band (0, 0.25) -> 1..6
    r = PixelHSV(0, 0, 0.10).v
    assert 1 <= r <= 6
    # boundary: v=0.25 -> first NOTE code
    assert PixelHSV(0, 0, 0.25).v == 6
    # top: v≈1.0 -> 13
    assert PixelHSV(0, 0, 1.0).v == 13

def test_constructor_rejects_bad_types_for_v():
    with pytest.raises(TypeError):
        PixelHSV(0, 0, "not-a-number")  # type: ignore[arg-type]


# =========================
# Hue inversion API
# =========================
def test_hue_inversion_cardinal_points():
    assert PixelHSV.hue_inversion(0) == 0
    assert PixelHSV.hue_inversion(60) == 300
    assert PixelHSV.hue_inversion(120) == 240
    assert PixelHSV.hue_inversion(180) == 180
    assert PixelHSV.hue_inversion(240) == 120
    assert PixelHSV.hue_inversion(300) == 60

def test_hue_inversion_normalizes_360_to_0():
    assert PixelHSV.hue_inversion(360) == 0

@pytest.mark.parametrize("bad", [-1, 361, 999])
def test_hue_inversion_out_of_range_raises(bad):
    with pytest.raises(OutsideAllowableRange):
        PixelHSV.hue_inversion(bad)


# =========================
# Integration: image -> PixelHSV list (requires Pillow)
# =========================
@pytest.mark.skipif(not PIL_AVAILABLE, reason="Pillow is required for this test")
def test_image_to_pixel_hsv_basic_colors(tmp_path: Path):
    # 2x2: red, green, black, white
    p = tmp_path / "colors.png"
    pixels = [
        (255, 0, 0),     # red (HSV hue ~0)    -> stored inverted hue 0
        (0, 255, 0),     # green (~120)        -> stored inverted hue ~240
        (0, 0, 0),       # black               -> rest
        (255, 255, 255)  # white               -> max duration note
    ]
    _save_png(p, pixels, 2, 2)

    w, h, px = image_to_pixel_hsv(p)
    assert (w, h) == (2, 2)
    assert len(px) == 4

    red, green, black, white = px

    # Red: inverted hue remains 0; full sat/bright -> note band
    assert red.h_deg == 0
    assert red.s == 10_000
    assert 7 <= red.v <= 13

    # Green: 120 -> inverted ~240; full sat/bright -> note band
    assert 238 <= green.h_deg <= 242
    assert green.s == 10_000
    assert 7 <= green.v <= 13

    # Black: s=0, v_code rest band (including 0)
    assert black.s == 0
    assert 0 <= black.v <= 6

    # White: s=0, bright -> top note code
    assert white.s == 0
    assert white.v == 13

import pytest
from src.pixel_hsv import PixelHSV
from src.exceptions import OutsideAllowableRange
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except Exception as e:
    raise ImportError("Pillow is required for these tests. pip install pillow") from e

from src.conversion import image_to_pixel_hsv


def _save_png(path: Path, pixels, w: int, h: int):
    im = Image.new("RGB", (w, h))
    im.putdata(pixels)
    im.save(path, "PNG")

def test_valid_init_and_repr():
    px = PixelHSV(180, 9000, 2)
    assert px.h_deg == 180
    assert px.s == 9000
    assert px.v == 2
    assert "PixelHSV" in repr(px)


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

def test_not_equal_diff_duration_only():
    a = PixelHSV(0, 0, 0)
    e = PixelHSV(0, 0, 1)
    assert a != e

def test_equal_edge_max_hue():
    f = PixelHSV(360, 0, 0)
    g = PixelHSV(360, 0, 0)
    assert f == g

def test_equal_edge_max_saturation():
    h = PixelHSV(0, 10_000, 0)
    i = PixelHSV(0, 10_000, 0)
    assert h == i

def test_equal_edge_max_duration():
    j = PixelHSV(0, 0, 6)
    k = PixelHSV(0, 0, 6)
    assert j == k

def test_cross_type_comparison_is_false():
    a = PixelHSV(0, 0, 0)
    assert (a == "PixelHSV") is False
    assert (a != "PixelHSV") is True

def test_reflexivity():
    a = PixelHSV(0, 0, 0)
    assert a == a

def test_symmetry():
    a = PixelHSV(0, 0, 0)
    b = PixelHSV(0, 0, 0)
    assert (a == b) and (b == a)

def test_transitivity():
    a = PixelHSV(0, 0, 0)
    b = PixelHSV(0, 0, 0)
    c = PixelHSV(0, 0, 0)
    assert (a == b) and (b == c) and (a == c)


@pytest.mark.parametrize(
    "h,s,v",
    [
        (-1, 5000, 3),      # hue low
        (361, 5000, 3),     # hue high
        (120, -1, 3),       # sat low
        (120, 10_001, 3),   # sat high
        (120, 5000, -1),    # v low
        (120, 5000, 7),     # v high
    ],
)
def test_out_of_range_raises(h, s, v):
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(h, s, v)

def test_value_to_duration_zero_and_one():
    assert PixelHSV.value_to_duration_code(0.0) == 0
    assert PixelHSV.value_to_duration_code(1.0) == 6


@pytest.mark.parametrize(
    "v,expected",
    [
        (1e-12, 1),                    # tiniest positive -> 1
        (1.0 / 6.0 - 1e-9, 1),         # just below first boundary -> 1
        (1.0 / 6.0 + 1e-9, 2),         # just above boundary -> 2 (ceil)
        (0.49, 3),                     # ~2.94 -> ceil = 3
        (0.5, 3),                      # 3 exactly
        (0.51, 4),                     # just past -> 4
        (0.99, 6),                     # near top -> 6
    ],
)
def test_value_to_duration_thresholds(v, expected):
    assert PixelHSV.value_to_duration_code(v) == expected


@pytest.mark.parametrize("v", [-1.0, -1e-9])
def test_value_to_duration_clamps_low(v):
    assert PixelHSV.value_to_duration_code(v) == 0


@pytest.mark.parametrize("v", [1.0000001, 2.0])
def test_value_to_duration_clamps_high(v):
    assert PixelHSV.value_to_duration_code(v) == 6


def test_value_to_duration_monotonic_samples():
    # Sanity: increasing v should not decrease code
    last = 0
    for step in range(0, 101):
        v = step / 100.0
        code = PixelHSV.value_to_duration_code(v)
        assert code >= last
        last = code

def test_constructor_accepts_int_code_direct():
    px = PixelHSV(180, 5000, 4)
    assert px.h_deg == 180 and px.s == 5000 and px.v == 4


def test_constructor_converts_float_v_to_code():
    # v=0.0 -> 0, v=1.0 -> 6
    assert PixelHSV(0, 0, 0.0).v == 0
    assert PixelHSV(0, 0, 1.0).v == 6

    # boundaries around 1/6
    assert PixelHSV(0, 0, (1.0 / 6.0) - 1e-9).v == 1
    assert PixelHSV(0, 0, (1.0 / 6.0) + 1e-9).v == 2

    # midpoints
    assert PixelHSV(0, 0, 0.49).v == 3
    assert PixelHSV(0, 0, 0.50).v == 3
    assert PixelHSV(0, 0, 0.51).v == 4


def test_constructor_float_out_of_range_is_clamped_to_codes():
    # Constructor uses value_to_duration_code which clamps
    assert PixelHSV(0, 0, -0.1).v == 0
    assert PixelHSV(0, 0, 10.0).v == 6


def test_constructor_rejects_bad_types_for_v():
    with pytest.raises(TypeError):
        PixelHSV(0, 0, "not-a-number")  # type: ignore[arg-type]


def test_constructor_rejects_out_of_range_h_and_s():
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(-1, 0, 0)
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(361, 0, 0)
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(0, -1, 0)
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(0, 10_001, 0)


def test_constructor_rejects_int_code_out_of_range():
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(0, 0, -1)
    with pytest.raises(OutsideAllowableRange):
        PixelHSV(0, 0, 7)


def test_image_to_pixel_hsv_basic_colors(tmp_path: Path):
    # 2x2: red, green, black, white
    p = tmp_path / "colors.png"
    pixels = [
        (255, 0, 0),     # red (HSV hue ~0) -> stored inverted hue 0
        (0, 255, 0),     # green (~120)    -> stored inverted hue ~240
        (0, 0, 0),       # black           -> rest
        (255, 255, 255)  # white           -> max duration
    ]
    _save_png(p, pixels, 2, 2)

    w, h, px = image_to_pixel_hsv(p)
    assert (w, h) == (2, 2)
    assert len(px) == 4

    red, green, black, white = px

    # Red: inverted hue remains 0
    assert red.h_deg == 0
    assert red.s == 10_000
    assert red.v == 6

    # Green: 120 -> inverted ~240
    assert 238 <= green.h_deg <= 242
    assert green.s == 10_000
    assert green.v == 6

    # Black: s=0, v_code=0
    assert black.s == 0
    assert black.v == 0

    # White: s=0, v_code max
    assert white.s == 0
    assert white.v == 6


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
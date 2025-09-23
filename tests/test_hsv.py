import pytest
from src.pixel_hsv import PixelHSV
from src.exceptions import OutsideAllowableRange


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
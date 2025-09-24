# tests/test_pixel_hsv.py
from __future__ import annotations

import pytest

from src.pixel_hsv import PixelHSV

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


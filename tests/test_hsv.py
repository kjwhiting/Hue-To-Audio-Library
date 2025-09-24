import pytest
from test_utils import is_equal

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

def test_color_red():
    pix =PixelHSV(255,0,0)
    assert is_equal(pix.h, 0)


def test_color_orange():
    pix = PixelHSV(255, 127, 0) 
    assert is_equal(pix.h, .08)


def test_color_yellow():
    pix = PixelHSV(255, 255, 0)
    assert is_equal(pix.h, .16)


def test_color_green():
    pix = PixelHSV(0,255,0)
    assert is_equal(pix.h, .33)


def test_color_blue():
    pix = PixelHSV(0,0,255)
    assert is_equal(pix.h, .66)


def test_color_indigo():
    pix = PixelHSV(75, 0, 130)
    assert is_equal(pix.h, .76)


def test_color_violet():
    pix = PixelHSV(148, 0, 211)
    assert is_equal(pix.h, .78)


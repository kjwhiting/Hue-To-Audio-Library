import math
from typing import Union
from src.exceptions import OutsideAllowableRange


class PixelHSV:
    """
    Strict data container for a pixel's HSV.

    Assumptions:
      - Incoming hue (h_deg) is in STANDARD HSV orientation (red=0°, green=120°, blue=240°).
      - We invert hue on construction to better match the physical color spectrum direction
        (violet→red), so stored h_deg is the inverted hue.

    Stored fields:
    h_deg: Hue degrees [0..360]
    s:    Saturation [0..10_000]
    v:    Duration code [0..6]
          0 = rest (do not play)
          1 = whole
          2 = quarter
          3 = eighth
          4 = sixteenth
          5 = thirtysecond
          6 = sixtyfourth
    Constructor accepts:
      - v as float in [0,1]: mapped to 0..13 via value_to_code() with a 0.25 threshold
      - v as int   in [0,13]: stored directly
    """

    __slots__ = ("h_deg", "s", "v")

    def __init__(self, h_deg: int, s: int, v: Union[int, float]) -> None:
        if not (0 <= h_deg <= 360):
            raise OutsideAllowableRange(f"Hue {h_deg} outside 0–360")
        if not (0 <= s <= 10_000):
            raise OutsideAllowableRange(f"Saturation {s} outside 0–10_000")

        if isinstance(v, float):
            v_code = PixelHSV.value_to_code(v)  # 0..13 with rest thresholding
        elif isinstance(v, int):
            v_code = v
        else:
            raise TypeError("v must be float (0..1) or int (0..13)")

        if not (0 <= v_code <= 13):
            raise OutsideAllowableRange(f"Value code {v_code} outside 0–13")

        self.h_deg = PixelHSV.hue_inversion(int(h_deg))
        self.s = int(s)
        self.v = int(v_code)

    def __repr__(self) -> str:
        return f"PixelHSV(h_deg={self.h_deg}, s={self.s}, v={self.v})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PixelHSV):
            return NotImplemented
        return (
            self.h_deg == other.h_deg
            and self.s == other.s
            and self.v == other.v
        )

    @staticmethod
    def value_to_code(v: float) -> int:
        """
        Map brightness v∈[0,1] to code 0..13 using a 0.25 rest threshold.

        - v <= 0   → 0 (shortest rest)
        - 0 < v <= 0.25: REST codes 1..6, scaled by ceil(v / 0.25 * 6)
        - v > 0.25: NOTE codes 7..13, using t=(v-0.25)/0.75 and ceil(t*7)

        Values outside [0,1] are clamped.
        """
        if v <= 0.0:
            return 0
        if v >= 1.0:
            return 13

        if v <= 0.25:
            # scale (0,0.25] to 1..6
            k = math.ceil((v / 0.25) * 6.0)  # 1..6
            return max(1, min(6, k))
        else:
            t = (v - 0.25) / 0.75  # (0,1]
            k = math.ceil(t * 7.0)  # 1..7
            return 7 + max(1, min(7, k)) - 1  # 7..13

    @staticmethod
    def hue_inversion(h_deg: int) -> int:
        """Reverse hue direction on the 0..360° wheel; 360 normalizes to 0."""
        if not (0 <= h_deg <= 360):
            raise OutsideAllowableRange(f"Hue {h_deg} outside 0–360")
        base = 0 if h_deg == 360 else h_deg
        return (360 - base) % 360

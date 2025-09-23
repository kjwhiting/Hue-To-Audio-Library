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
      - v as float in [0,1]  -> converted to code via value_to_duration_code
      - v as int   in [0,6]  -> stored directly
    """

    __slots__ = ("h_deg", "s", "v")

    def __init__(self, h_deg: int, s: int, v: Union[int, float]) -> None:
        # Validate incoming HSV-scaled values
        if not (0 <= h_deg <= 360):
            raise OutsideAllowableRange(f"Hue {h_deg} outside 0–360")
        if not (0 <= s <= 10_000):
            raise OutsideAllowableRange(f"Saturation {s} outside 0–10_000")

        # Convert brightness to duration code if float was provided
        if isinstance(v, float):
            v_code = PixelHSV.value_to_duration_code(v)
        elif isinstance(v, int):
            v_code = v
        else:
            raise TypeError("v must be float (0..1) or int (0..6)")

        if not (0 <= v_code <= 6):
            raise OutsideAllowableRange(f"Value/duration code {v_code} outside 0–6")

        # Normalize and invert hue on storage to match physical spectrum direction
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
    def value_to_duration_code(v: float) -> int:
        """
        Map brightness v∈[0,1] -> duration code 0..6.
          0     => 0 (rest)
          (0,1] => ceil(v*6) clamped to [1..6]
        Values outside [0,1] are clamped: v<=0→0, v>=1→6.
        """
        if v <= 0.0:
            return 0
        code = math.ceil(v * 6.0)
        if code < 1:
            return 1
        if code > 6:
            return 6
        return code

    @staticmethod
    def hue_inversion(h_deg: int) -> int:
        """
        Reverse hue direction on the 0..360° wheel; 360 normalizes to 0.

        Examples:
          0 -> 0, 60 -> 300, 120 -> 240, 180 -> 180, 240 -> 120, 300 -> 60, 360 -> 0
        """
        if not (0 <= h_deg <= 360):
            raise OutsideAllowableRange(f"Hue {h_deg} outside 0–360")
        base = 0 if h_deg == 360 else h_deg  # normalize 360 to 0
        return (360 - base) % 360

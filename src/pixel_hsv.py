import math
from src.exceptions import OutsideAllowableRange


class PixelHSV:
    """
    Strict data container for a pixel's HSV, using integers for exact equality.

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
    """

    __slots__ = ("h_deg", "s", "v")

    def __init__(self, h_deg: int, s: int, v: int) -> None:
        if not (0 <= h_deg <= 360):
            raise OutsideAllowableRange(f"Hue {h_deg} outside 0–360")
        if not (0 <= s <= 10_000):
            raise OutsideAllowableRange(f"Saturation {s} outside 0–10_000")
        if not (0 <= v <= 6):
            raise OutsideAllowableRange(f"Value/duration code {v} outside 0–6")

        self.h_deg = int(h_deg)
        self.s = int(s)
        self.v = int(v)

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

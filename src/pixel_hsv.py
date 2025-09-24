import math
import colorsys


class PixelHSV:
    def __init__(self, r,g,b):
        h,s,v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self.h_deg = PixelHSV.hue_inversion(h)
        self.h = h
        self.s = s
        self.v = v

    def __repr__(self):
        return f"PixelHSV(h_deg={self.h_deg}, s={self.s}, v={self.v})"

    def __eq__(self, other):
        if not isinstance(other, PixelHSV):
            return NotImplemented
        return (
            math.isclose(self.h, other.h) and math.isclose(self.s, other.s) and math.isclose(self.v, other.v)
        ) 

    @staticmethod
    def hue_inversion(h):
        """Reverse hue direction on the 0..360° wheel to pair with physical light."""
        base = 0 if h == 360 else h
        return (360 - base) % 360

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from src.pixel_hsv import PixelHSV

def is_prime(factors):
    return len(factors)==1

def get_factors(n):
    """
    Returns a list of all factors of a given positive integer n.
    """
    factors = []
    for i in range(2, n + 1):
        if n % i == 0:
            factors.append(i)
    return factors

def pixels_to_beats(pixels, bpm):
    factors = get_factors(int(len(pixels)))
    if(is_prime(factors)):
        factors= [2,3,5,7]
    
    beats = math.prod(factors)
    song_length_minutes = beats/bpm

    # could dynamically set max length of song here
    # for now default to 2 minutes
    while song_length_minutes > 2: 
        factors.pop()
        beats = math.prod(factors)
        song_length_minutes = beats/bpm

    return (factors, beats, song_length_minutes)

def hue_to_frequency_direct(pixel_hsv):
    # Playable frequency is between c2 (65 hz) and c6 (146 hz). This range was chosen and can be exteneded
    # Hue is between 0-360 (normally red-violet pixel-hsv converts this to violet-red)

    # Convert hue to value between 0-1
    hue_percentage = pixel_hsv.h

    # option 2 --
    # Convert directly to playable frequency without visible light step
    max_hearable_freq = 146
    min_hearable_freq = 65
    upper_bound = 1
    lower_bound = min_hearable_freq / max_hearable_freq
    return (upper_bound - lower_bound) * hue_percentage * max_hearable_freq + min_hearable_freq


def hue_to_frequency_true_color(pixel_hsv):
    # Playable frequency is between c2 (65 hz) and c6 (146 hz). This range was chosen and can be exteneded
    # Visible light is between violet 400 Thz to red 790 Thz
    # Hue is between 0-360 (normally red-violet pixel-hsv converts this to violet-red)

    # Convert hue to value between 0-1
    hue_percentage = pixel_hsv.h

    # Map percentage to visible light
    max_visible_light = 790_000_000_000_000
    min_visible_light = 400_000_000_000_000
    upper_bound = 1
    lower_bound = min_visible_light / max_visible_light
    color = (upper_bound - lower_bound) * hue_percentage * max_visible_light + min_visible_light

    # option -- get_close
    # 4.0x10^14/2^42 ~90
    # 7.9x10^14/2^42 ~179 
    return color / 2**42


# def hue_to_note(pixel_hsv, beats, time_signature):

def _read_image_rgb(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    try:
        from PIL import Image, ImageOps
    except Exception as e:
        raise ImportError("Pillow is required: pip install pillow") from e
    try:
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            w, h = im.size
            pixels = list(im.getdata())
            if len(pixels) != w * h:
                raise ValueError("Pixel data length mismatch after RGB converter")
            return w, h, pixels
    except OSError as e:
        raise ValueError(f"Failed to open/read image: {p.name}") from e


def image_to_pixel_hsv(path):
    """
    Read an image, convert each pixel to PixelHSV, and return:
      (width, height, [PixelHSV, ...]) in row-major order.
    """
    w, h, pixels = _read_image_rgb(path)
    pixels_converted = []
    counter = 0
    for (r, g, b) in pixels:
        if(counter % w == 0):
            print(".", end="")
        pixels_converted.append(PixelHSV(r,g,b))
        counter +=1
    return w, h, pixels_converted





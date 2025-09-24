# oscillators.py
"""
Bare-bones oscillator functions: sine, square, saw.
Each returns a list of PCM16 samples in range [-32767, 32767].
Writing/playing .wav files happens only when run as a script.
"""

import math
import struct
import wave
import sys
import os
from pathlib import Path
from typing import List

SAMPLE_RATE = 44100
DURATION = 2.0      # seconds
FREQUENCY = 440.0   # Hz (A4 test tone)
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ===== OSCILLATORS =====
def sine_wave(frequency: float = FREQUENCY,
              duration: float = DURATION,
              sample_rate: int = SAMPLE_RATE) -> List[int]:
    samples = []
    for n in range(int(duration * sample_rate)):
        value = math.sin(2 * math.pi * frequency * n / sample_rate)
        samples.append(int(value * 32767.0))
    return samples


def square_wave(frequency: float = FREQUENCY,
                duration: float = DURATION,
                sample_rate: int = SAMPLE_RATE) -> List[int]:
    samples = []
    for n in range(int(duration * sample_rate)):
        value = 1.0 if math.sin(2 * math.pi * frequency * n / sample_rate) >= 0 else -1.0
        samples.append(int(value * 32767.0))
    return samples


def saw_wave(frequency: float = FREQUENCY,
             duration: float = DURATION,
             sample_rate: int = SAMPLE_RATE) -> List[int]:
    samples = []
    for n in range(int(duration * sample_rate)):
        value = 2.0 * ((n * frequency / sample_rate) % 1.0) - 1.0
        samples.append(int(value * 32767.0))
    return samples


# ===== TEST UTILITIES (used by filters/amplifiers demos too) =====
def write_wav(filename: str, samples: List[int],
              sample_rate: int = SAMPLE_RATE) -> Path:
    """Write samples to a mono 16-bit PCM WAV file."""
    path = OUTPUT_DIR / filename
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = b"".join(struct.pack("<h", s) for s in samples)
        w.writeframes(frames)
    return path


def play_file(path: Path) -> None:
    """Play WAV file using system default player."""
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore
    elif sys.platform.startswith("darwin"):
        os.system(f"afplay '{path}'")
    else:  # Linux
        os.system(f"aplay '{path}'")


# ===== MAIN (testing only) =====
if __name__ == "__main__":
    print("Generating test oscillators...")
    p1 = write_wav("sine.wav", sine_wave())
    play_file(p1)

    p2 = write_wav("square.wav", square_wave())
    play_file(p2)

    p3 = write_wav("saw.wav", saw_wave())
    play_file(p3)

    print("Done. Files saved in ./output/")

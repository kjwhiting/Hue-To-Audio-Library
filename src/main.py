# main.py
"""
Bare-bones entry point to compose a song from an image's pixels.
No CLI flags—just edit the constants below.

Flow:
  composer_pixels.compose_from_image -> write_wav -> play_file
"""

from pathlib import Path

from src.composer_pixels import compose_from_image
from src.synth.oscillators import write_wav, play_file

# ===== EDIT HERE (hard-coded constants) =====
IMAGE_PATH = "test_images/hues-a.jpg"     # path to your source image
OUTPUT_FILENAME = "pixels_song.wav"    # output file name (saved under ./output/)

def main() -> None:
    print(f"Composing from: {IMAGE_PATH}")
    samples = compose_from_image(IMAGE_PATH)
    out_path = write_wav(OUTPUT_FILENAME, samples)
    play_file(out_path)
    print(f"Done. Wrote {Path(out_path)}")

if __name__ == "__main__":
    main()

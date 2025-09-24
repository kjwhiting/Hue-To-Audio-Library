# Hue-To-Audio-Library
Python project that takes in an image and converts it to sound.

This package includes python modules that are used to convert an image to audio.

## Modules and what they do

### converter library
- Python has built in tools to help read in image files. Once the file is loaded we convert each pixel to a hue saturation and value. Hue is the note that gets played, value is the length it is played and saturation is loudness.
- We leverage `HSV` (Hue, Saturation, and Value)
  - Hue converter -- h/360 gives us a value from 0-1 that we then use to identify which color it is in the visible light spectrum. we then divide this value by 2^n until we get playable sound note within a hearable frequency. That then becomes the note that is played.
  - Saturation converter -- The default is mapped to loudness. If a pixel is fully saturated this note will play loudly. No saturation means a quite is played.
  - Value converter -- This indicates how long the note is played. 0 the note is skipped, 1 the note is played for a whole note.
- Visible light spectrum
  - 4 x 10^14 Hz to 7.9 x 10^14 Hz is the visible spectrum of light. 
  - Purple to Red means this is inverted from HSV spectrum. Part of the converter library is providing this inversion to get accurate color representation. 


### Break down of the sounds
- `synth.py` is responsible for the sound generation and creation. We leverage a basic sin wave for most of the sound generation. This is the place to go if you want to play around with the sounds in a synthesizer type setting.
- `composer.py` is the arrangment of the music. The functions for timing is established and the value range to beat ratio is defined.

### Tests
All tests and test cases are include in the `/tests` folder. This doubles as documentation for how to use the modules. The test files include a healthy amount of use cases to ensure the program works properly.

`main.py` is the entry point for the program

## Running locally
Install python and run this command to install pillow
```
pip install Pillow, pytest
```

### (optional) create the three test JPGs
```python -m src.helper```
### -> test_images/hues.jpg, test_images/values.jpg, test_images/saturations.jpg

### run the composer on any JPG/PNG
python -m src.main --image path/to/your.jpg --out song.wav --bpm 120 --voice-strategy hue --stride 1

# Hues sweep (361 px)
python -m src.main --image test_images/hues.jpg --out hues.wav --bpm 120 --voice-strategy hue --stride 1

# Values (rests+notes across codes 0..13)
python -m src.main --image test_images/values.jpg --out values.wav --bpm 120 --voice-strategy sine --stride 1

# Saturations (10,001 px → use stride to shorten render time)
python -m src.main --image test_images/saturations.jpg --out sats.wav --bpm 120 --voice-strategy triangle --stride 100

# Built-in sample (no image; plays all voices & durations)
python -m src.main --demo

| Flag | Type  | Default | Allowed values | What it |
| ------------------ | ------ | ---------------------------: | ---------------------------------------------- | ------------------------------------------------ |
| `--image`, `-i`    | path   | *(required unless `--demo`)* | any JPG/PNG Pillow can open                 | Input image to sonify |
| `--out`, `-o`      | path   |                 `output.wav` | file path                                      | Where to write the 16-bit mono WAV               |
| `--bpm`            | int    |                        `120` | `>0`                                           | Tempo for converting duration codes to seconds   |
| `--sr`             | int    |                      `44100` | common audio rates                             | Output sample rate                               |
| `--voice-strategy` | choice |                        `hue` | `sine` · `triangle` · `bell` · `cycle` · `hue` | How the voice is chosen per pixel (see below)    |
| `--stride`         | int    |                          `1` | `>=1`                                          | Use every Nth pixel (speed/length control)       |
| `--demo`           | flag   |                          off | —                                              | Ignore `--image` and render a built-in demo file |




To run the tests locally install `pytest` and run them with 
```
python -m pytest -q
```

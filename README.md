# Hue-To-Audio-Library
Python project that takes in an image and converts it to sound.

This package includes python modules that are used to convert an image to audio.

## Modules and what they do

### converter library
- Python has built in tools to help read in image files. Once the file is loaded we convert each pixel to a hue saturation and value. Hue is the note (frequency) that gets played.
- We leverage `HSV` (Hue, Saturation, and Value)
  - Hue converter -- Value from 0-1 that we then use to identify which color it is in the visible light spectrum. we then divide this value by 2^n until we get playable sound note within a hearable frequency. That then becomes the note that is played.
  - Saturation converter -- This is mapped to the pace of the music and is an average of the overall pixels. (can be modified or tweaked for different effects)
  - Value converter -- This is mapped to how many track variations and is based on an overall avarage. (can be modified or tweaked for different effects)
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

Generate the test files
```
python -m tests.test-image-generator
```

Modify the main.py file to point to the file you want to convert.
```
IMAGE_PATH = "test_images/hues.jpg"     # path to your source image
OUTPUT_FILENAME = "pixels_song.wav"    # output file name (saved under ./output/)
```

run the program with ```python -m src.main```

## running tests
To run the tests locally install `pytest` and run them with 
```
python -m pytest -q
```

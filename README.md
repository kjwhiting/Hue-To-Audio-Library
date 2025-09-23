# Hue-To-Audio-Library
Python project that takes in an image and converts it to sound.

This package includes python modules that are used to convert an image to audio.

## Modules and what they do

### Conversion library
- Python has built in tools to help read in image files. Once the file is loaded we convert each pixel to a hue saturation and value. Hue is the note that gets played, value is the length it is played and saturation is loudness.
- We leverage `HSV` (Hue, Saturation, and Value)
  - Hue conversion -- h/360 gives us a value from 0-1 that we then use to identify which color it is in the visible light spectrum. we then divide this value by 2^n until we get playable sound note within a hearable frequency. That then becomes the note that is played.
  - Saturation conversion -- The default is mapped to loudness. If a pixel is fully saturated this note will play loudly. No saturation means a quite is played.
  - Value conversion -- This indicates how long the note is played. 0 the note is skipped, 1 the note is played for a whole note.
- Visible light spectrum
  - 4 x 10^14 Hz to 7.9 x 10^14 Hz is the visible spectrum of light. 
  - Purple to Red means this is inverted from HSV spectrum. Part of the conversion library is providing this inversion to get accurate color representation. 


### Break down of the sounds
- `synth.py` is responsible for the sound generation and creation. We leverage a basic sin wave for most of the sound generation. This is the place to go if you want to play around with the sounds in a synthesizer type setting.
- `composer.py` is the arrangment of the music. The functions for timing is established and the value range to beat ratio is defined.

### Tests
All tests and test cases are include in the `/tests` folder. This doubles as documentation for how to use the modules. The test files include a healthy amount of use cases to ensure the program works properly.

`main.py` is the entry point for the program

## Running locally
Install python and from the `/src` directory run this command in terminal window
```
python main.py
```

To run the tests locally install `pytest` and run them with 
```
python -m pytest -q
```

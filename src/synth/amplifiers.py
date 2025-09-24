# amplifiers.py
"""
Bare-bones amplifier stage + AMPLIFIER envelopes.
Apply after filters.

Amplifier:
- amplifier(samples, gain=0.75)  # clamps to 0.75 max

Amplifier envelopes (ADSR only):
- aenv_piano / aenv_string / aenv_drums
"""

from typing import List
from src.synth.oscillators import sine_wave, write_wav, play_file
from src.synth.envelopes import aenv_piano, aenv_string, aenv_drums

def amplifier(samples: List[int], gain: float = 0.75) -> List[int]:
    """Clamp amplitude at <= 0.75."""
    g = min(gain, 0.75)
    return [int(s * g) for s in samples]

# ===== DEMO: (filters were already applied); here we show amp envelopes =====
if __name__ == "__main__":
    print("Demo: oscillator → amp-envelope → amplifier → wav")

    # Start from a raw oscillator for this demo (in full chain, you'd filter first)
    raw = sine_wave()

    # Try different amp envelopes (no fade here by design)
    piano_stage = aenv_piano(raw, attack=0.01, decay=0.20, sustain=0.30, release=0.20)
    piano_out = amplifier(piano_stage)
    p1 = write_wav("sine_ampenv_piano.wav", piano_out)
    play_file(p1)

    string_stage = aenv_string(raw, attack=0.08, decay=0.25, sustain=0.60, release=0.30)
    string_out = amplifier(string_stage)
    p2 = write_wav("sine_ampenv_string.wav", string_out)
    play_file(p2)

    drum_stage = aenv_drums(raw, attack=0.005, decay=0.12, sustain=0.0, release=0.05)
    drum_out = amplifier(drum_stage)
    p3 = write_wav("sine_ampenv_drums.wav", drum_out)
    play_file(p3)

    print("Done. Files saved in ./output/")

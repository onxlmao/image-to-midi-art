# 🎨 Image to MIDI Art Converter

Convert any image into a playable MIDI music file! Each pixel becomes a musical note — creating unique sonic landscapes from your photos.

## How It Works

| Pixel Property | Musical Parameter |
|---|---|
| **Vertical position (Y)** | → Pitch (which note plays) |
| **Horizontal position (X)** | → Timing (when the note plays) |
| **Brightness** | → Velocity (how loud) |
| **Hue (colour)** | → Channel / Instrument |

## Installation

```bash
cd image-to-midi-art
pip install -r requirements.txt
```

## Quick Start

### Gradio Web UI (Recommended)

```bash
# Launch the interactive web demo
python gradio_demo.py
# Open http://localhost:7860 in your browser
```

The web UI features:
- Drag & drop image upload
- Real-time parameter controls with sliders and dropdowns
- Piano roll visualization of the generated notes
- Note distribution histogram
- Processed image preview
- 4 quick presets: Ambient Pad, 8-Bit Retro, Gentle Melody, Dense Chaos
- Direct MIDI file download

### Command Line

```bash
# Basic conversion
python main.py photo.jpg -o music.mid

# Pentatonic scale with slower tempo
python main.py photo.jpg -o music.mid --scale pentatonic --tempo 80

# Grayscale filter with spiral scan
python main.py photo.jpg -o music.mid --filter grayscale --scan spiral_inward

# Use specific instruments
python main.py photo.jpg -o music.mid --instruments marimba vibraphone flute music_box
```

## Python API

```python
from image_to_midi import ImageToMidi

# Create converter with custom settings
converter = ImageToMidi(
    "photo.jpg",
    max_width=64,
    max_height=64,
    scale="pentatonic",
    tempo=100,
    duration=0.3,
)

# Convert and save
output_path = converter.convert("output.mid", tempo=100)
print(f"Saved to: {output_path}")

# Get info about the conversion
print(converter.info())
```

## CLI Options

### Image Processing
| Option | Default | Description |
|---|---|---|
| `--max-size` | 128 | Max width/height after resize |
| `--resize-mode` | fit | Resize strategy: fit, stretch, crop |
| `--filter` | none | Colour filter: none, grayscale, sepia, invert, posterize, threshold |
| `--filter-levels` | 4 | Quantisation levels for posterize/threshold |

### Musical Mapping
| Option | Default | Description |
|---|---|---|
| `--scan` | left_to_right | Scan direction |
| `--pitch-mode` | inverted | Pitch mapping mode |
| `--velocity-mode` | bright | Velocity mapping mode |
| `--note-low` | 36 | Lowest MIDI note (C2) |
| `--note-high` | 96 | Highest MIDI note (C7) |
| `--scale` | chromatic | Musical scale |
| `--base-note` | 0 | Root note (0=C, 2=D, etc.) |

### Available Scales
`chromatic`, `major`, `natural_minor`, `harmonic_minor`, `melodic_minor`, `pentatonic`, `blues`, `dorian`, `mixolydian`, `phrygian`, `whole_tone`

### Scan Directions
`left_to_right`, `right_to_left`, `top_to_bottom`, `bottom_to_top`, `diagonal_tl_br`, `diagonal_bl_tr`, `spiral_inward`, `spiral_outward`

### Timing & Rhythm
| Option | Default | Description |
|---|---|---|
| `--tempo` | 120 | BPM |
| `--time-step` | 0.15 | Beats between notes |
| `--duration` | 0.25 | Note duration in beats |
| `--time-sig` | 4/4 | Time signature |

### Performance
| Option | Default | Description |
|---|---|---|
| `--step` | 1 | Pixel skip factor (higher = faster) |
| `--num-channels` | 4 | Number of MIDI channels |
| `--brightness-threshold` | 0.05 | Min brightness to trigger a note |
| `--instruments` | piano set | Instrument names per channel |

### Available Instruments
`acoustic_grand_piano`, `electric_piano_1`, `vibraphone`, `marimba`, `music_box`, `flute`, `violin`, `cello`, `trumpet`, `synth_pad_choir`, and 40+ more.

## Project Structure

```
image-to-midi-art/
├── gradio_demo.py             # Gradio web UI demo
├── main.py                    # CLI entry point
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
├── image_to_midi/
│   ├── __init__.py            # Package init
│   ├── __main__.py            # python -m support
│   ├── converter.py           # Core orchestrator
│   ├── image_processor.py     # Image loading & processing
│   ├── mapping.py             # Pixel → MIDI note mapping
│   ├── midi_generator.py      # MIDI file generation
│   └── cli.py                 # Command-line interface
```

## Tips for Best Results

- **Landscape photos** work great — sky becomes high notes, ground becomes bass
- **Higher contrast** images produce more dynamic music
- Use `--scale pentatonic` or `--scale blues` for more pleasant-sounding results
- Use `--step 2` or `--step 3` for less dense (more spacious) output
- Try `--filter posterize` for a more rhythmic, quantised sound
- Use `--scan spiral_inward` for a unique progressive feel

## License

MIT

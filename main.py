"""
Image to MIDI Art Converter — executable entry point.

Usage:
    python main.py input.jpg -o output.mid [options]
"""

from image_to_midi.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())

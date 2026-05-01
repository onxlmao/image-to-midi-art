"""
Image to MIDI Art Converter
============================
A Python library that converts images into MIDI music files by mapping
pixel properties (position, color, brightness) to musical parameters
(notes, velocity, timing, instruments).

Usage:
    from image_to_midi import ImageToMidi

    converter = ImageToMidi("photo.jpg")
    converter.convert("output.mid")
"""

__version__ = "1.0.0"
__author__ = "ImageToMIDI"

from image_to_midi.converter import ImageToMidi  # noqa: F401

__all__ = ["ImageToMidi"]

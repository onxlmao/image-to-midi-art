"""
Color and brightness to MIDI note mapping strategies.

Each strategy provides a different way to interpret pixel data as musical
parameters, resulting in different sonic characteristics.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


# ── MIDI note constants ────────────────────────────────────────────────
MIDI_NOTE_MIN = 0
MIDI_NOTE_MAX = 127
MIDI_VELOCITY_MIN = 1
MIDI_VELOCITY_MAX = 127

# Common scale intervals (semitones from root)
SCALE_INTERVALS = {
    "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "pentatonic": [0, 2, 4, 7, 9],
    "blues": [0, 3, 5, 6, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
}

# Note name lookup for display purposes
NOTE_NAMES = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
]


class ScanDirection(str, Enum):
    """Direction in which the image is scanned to generate MIDI events."""
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"
    DIAGONAL_TL_BR = "diagonal_tl_br"    # top-left → bottom-right
    DIAGONAL_BL_TR = "diagonal_bl_tr"    # bottom-left → top-right
    SPIRAL_INWARD = "spiral_inward"
    SPIRAL_OUTWARD = "spiral_outward"


class PitchMode(str, Enum):
    """How pixel vertical position maps to MIDI pitch."""
    LINEAR = "linear"          # direct linear mapping
    INVERTED = "inverted"      # top = high notes, bottom = low
    MIRROR = "mirror"          # mirror around middle row


class VelocityMode(str, Enum):
    """How pixel brightness maps to MIDI velocity."""
    BRIGHT = "bright"          # brighter → louder
    DARK = "dark"              # darker → louder
    HUE_BASED = "hue_based"   # saturation → velocity


@dataclass
class NoteMapping:
    """Result of mapping a single pixel to a MIDI note."""
    note: int                  # MIDI note number (0-127)
    velocity: int              # MIDI velocity (1-127)
    time_offset: float         # Time position in beats
    duration: float            # Note duration in beats
    channel: int               # MIDI channel (0-15)

    def __post_init__(self):
        """Clamp values to valid MIDI ranges."""
        self.note = max(MIDI_NOTE_MIN, min(MIDI_NOTE_MAX, self.note))
        self.velocity = max(MIDI_VELOCITY_MIN, min(MIDI_VELOCITY_MAX, self.velocity))
        self.channel = max(0, min(15, self.channel))


def brightness_to_velocity(
    brightness: float,
    mode: VelocityMode = VelocityMode.BRIGHT,
    min_vel: int = MIDI_VELOCITY_MIN,
    max_vel: int = MIDI_VELOCITY_MAX,
) -> int:
    """
    Convert a brightness value (0.0–1.0) to a MIDI velocity.

    Args:
        brightness: Pixel brightness, 0.0 (black) to 1.0 (white).
        mode: Mapping mode (bright=louder for brighter, dark=inverse).
        min_vel: Minimum output velocity.
        max_vel: Maximum output velocity.

    Returns:
        MIDI velocity (1–127).
    """
    if mode == VelocityMode.DARK:
        brightness = 1.0 - brightness

    velocity = int(min_vel + brightness * (max_vel - min_vel))
    return max(MIDI_VELOCITY_MIN, min(MIDI_VELOCITY_MAX, velocity))


def y_position_to_pitch(
    y: int,
    height: int,
    mode: PitchMode = PitchMode.INVERTED,
    note_low: int = 36,
    note_high: int = 96,
    scale: str = "chromatic",
    base_note: int = 0,
) -> int:
    """
    Convert a vertical pixel position to a MIDI note.

    Args:
        y: Vertical pixel position (0 = top of image).
        height: Total image height in pixels.
        mode: Pitch mapping mode.
        note_low: Lowest MIDI note in range.
        note_high: Highest MIDI note in range.
        scale: Musical scale name (e.g. "major", "pentatonic").
        base_note: Root note offset (0=C, 2=D, etc.).

    Returns:
        MIDI note number (0–127).
    """
    # Normalise y position
    normalised = y / max(height - 1, 1)

    if mode == PitchMode.INVERTED:
        normalised = 1.0 - normalised
    elif mode == PitchMode.MIRROR:
        # Mirror around the center
        center = 0.5
        normalised = 1.0 - abs(normalised - center) * 2.0

    # Map to continuous pitch range
    continuous_pitch = note_low + normalised * (note_high - note_low)

    if scale == "chromatic":
        note = int(round(continuous_pitch))
    else:
        # Quantise to the chosen scale
        intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["chromatic"])
        octave = int(continuous_pitch) // 12
        degree_in_octave = int(continuous_pitch) % 12
        # Find nearest scale degree
        nearest = min(intervals, key=lambda d: abs(d - degree_in_octave))
        note = (octave * 12) + nearest + base_note

    return max(MIDI_NOTE_MIN, min(MIDI_NOTE_MAX, note))


def hue_to_channel(
    r: int, g: int, b: int,
    channels: int = 4,
) -> int:
    """
    Map a pixel's hue to a MIDI channel for timbral variety.

    Args:
        r, g, b: RGB colour components (0–255).
        channels: Number of MIDI channels to use (max 16).

    Returns:
        MIDI channel number (0–15).
    """
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    h, _, _ = colorsys.rgb_to_hsv(r_n, g_n, b_n)
    channel = int(h * channels)
    return max(0, min(15, channel))


def generate_scan_order(
    width: int,
    height: int,
    direction: ScanDirection = ScanDirection.LEFT_TO_RIGHT,
) -> List[Tuple[int, int]]:
    """
    Generate the pixel-scan order based on the chosen direction.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        direction: Scan direction strategy.

    Returns:
        List of (x, y) coordinate tuples in scan order.
    """
    coords: List[Tuple[int, int]] = []

    if direction == ScanDirection.LEFT_TO_RIGHT:
        for y in range(height):
            for x in range(width):
                coords.append((x, y))

    elif direction == ScanDirection.RIGHT_TO_LEFT:
        for y in range(height):
            for x in range(width - 1, -1, -1):
                coords.append((x, y))

    elif direction == ScanDirection.TOP_TO_BOTTOM:
        for x in range(width):
            for y in range(height):
                coords.append((x, y))

    elif direction == ScanDirection.BOTTOM_TO_TOP:
        for x in range(width):
            for y in range(height - 1, -1, -1):
                coords.append((x, y))

    elif direction == ScanDirection.DIAGONAL_TL_BR:
        for s in range(width + height - 1):
            if s < width:
                x_start = s
                y_start = 0
            else:
                x_start = width - 1
                y_start = s - width + 1
            x, y = x_start, y_start
            while x >= 0 and y < height:
                coords.append((x, y))
                x -= 1
                y += 1

    elif direction == ScanDirection.DIAGONAL_BL_TR:
        for s in range(width + height - 1):
            if s < width:
                x_start = s
                y_start = height - 1
            else:
                x_start = width - 1
                y_start = height - 1 - (s - width + 1)
            x, y = x_start, y_start
            while x >= 0 and y >= 0:
                coords.append((x, y))
                x -= 1
                y -= 1

    elif direction == ScanDirection.SPIRAL_INWARD:
        top, bottom, left, right = 0, height - 1, 0, width - 1
        while top <= bottom and left <= right:
            for x in range(left, right + 1):
                coords.append((x, top))
            top += 1
            for y in range(top, bottom + 1):
                coords.append((right, y))
            right -= 1
            if top <= bottom:
                for x in range(right, left - 1, -1):
                    coords.append((x, bottom))
                bottom -= 1
            if left <= right:
                for y in range(bottom, top - 1, -1):
                    coords.append((left, y))
                left += 1

    elif direction == ScanDirection.SPIRAL_OUTWARD:
        inner = []
        top, bottom, left, right = 0, height - 1, 0, width - 1
        while top <= bottom and left <= right:
            layer = []
            for x in range(left, right + 1):
                layer.append((x, top))
            top += 1
            for y in range(top, bottom + 1):
                layer.append((right, y))
            right -= 1
            if top <= bottom:
                for x in range(right, left - 1, -1):
                    layer.append((x, bottom))
                bottom -= 1
            if left <= right:
                for y in range(bottom, top - 1, -1):
                    layer.append((left, y))
                left += 1
            inner.append(layer)
        # Reverse the layer order to spiral outward
        for layer in reversed(inner):
            coords.extend(layer)

    return coords


def pixel_to_note(
    x: int,
    y: int,
    r: int,
    g: int,
    b: int,
    a: int,
    width: int,
    height: int,
    step: int,
    time_step: float,
    note_low: int = 36,
    note_high: int = 96,
    pitch_mode: PitchMode = PitchMode.INVERTED,
    velocity_mode: VelocityMode = VelocityMode.BRIGHT,
    scale: str = "chromatic",
    base_note: int = 0,
    num_channels: int = 4,
    duration: float = 0.25,
    brightness_threshold: float = 0.05,
) -> NoteMapping | None:
    """
    Convert a single pixel into a MIDI note mapping.

    If the pixel's brightness is below the threshold, returns None
    (the pixel is treated as silence).

    Args:
        x, y: Pixel coordinates.
        r, g, b, a: RGBA colour components.
        width, height: Image dimensions.
        step: Pixel sampling step (skip factor).
        time_step: Time between consecutive notes (in beats).
        note_low, note_high: Pitch range.
        pitch_mode: Pitch mapping mode.
        velocity_mode: Velocity mapping mode.
        scale: Musical scale name.
        base_note: Root note offset for scale.
        num_channels: Number of MIDI channels.
        duration: Note duration in beats.
        brightness_threshold: Minimum brightness to produce a note.

    Returns:
        NoteMapping or None if pixel is too dark.
    """
    # Calculate brightness from RGBA
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    _, _, brightness = colorsys.rgb_to_hsv(r_n, g_n, b_n)

    # Apply alpha as a multiplier
    brightness *= a / 255.0

    # Skip very dark pixels
    if brightness < brightness_threshold:
        return None

    # Map to pitch
    note = y_position_to_pitch(
        y, height,
        mode=pitch_mode,
        note_low=note_low,
        note_high=note_high,
        scale=scale,
        base_note=base_note,
    )

    # Map to velocity
    velocity = brightness_to_velocity(brightness, mode=velocity_mode)

    # Map hue to channel
    channel = hue_to_channel(r, g, b, channels=num_channels)

    # Time offset based on position
    time_offset = (y * width + x) / step * time_step

    return NoteMapping(
        note=note,
        velocity=velocity,
        time_offset=time_offset,
        duration=duration,
        channel=channel,
    )

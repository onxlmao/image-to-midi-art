"""
Core converter — orchestrates the full image-to-MIDI pipeline.

This is the main high-level interface for the library.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from image_to_midi.image_processor import (
    ColourFilter,
    ProcessedImage,
    ResizeMode,
    process_image,
)
from image_to_midi.mapping import (
    NoteMapping,
    PitchMode,
    ScanDirection,
    VelocityMode,
    generate_scan_order,
    pixel_to_note,
)
from image_to_midi.midi_generator import INSTRUMENTS, generate_midi


class ImageToMidi:
    """
    High-level converter that turns an image into a MIDI art file.

    Example:
        converter = ImageToMidi("photo.jpg", max_width=64, max_height=64)
        converter.convert("output.mid", tempo=140)

    The converter reads pixel data from the image and maps it to musical
    parameters:

    - **Vertical position (Y)** → pitch (which note plays)
    - **Horizontal position (X)** → time (when the note plays)
    - **Brightness** → velocity (how loud the note is)
    - **Hue** → channel/instrument (timbral variety)
    """

    def __init__(
        self,
        image_path: str,
        *,
        max_width: int = 128,
        max_height: int = 128,
        resize_mode: ResizeMode = ResizeMode.FIT,
        colour_filter: ColourFilter = ColourFilter.NONE,
        filter_levels: int = 4,
        scan_direction: ScanDirection = ScanDirection.LEFT_TO_RIGHT,
        pitch_mode: PitchMode = PitchMode.INVERTED,
        velocity_mode: VelocityMode = VelocityMode.BRIGHT,
        note_low: int = 36,
        note_high: int = 96,
        scale: str = "chromatic",
        base_note: int = 0,
        step: int = 1,
        time_step: float = 0.15,
        duration: float = 0.25,
        num_channels: int = 4,
        brightness_threshold: float = 0.05,
    ) -> None:
        """
        Initialize the ImageToMidi converter.

        Args:
            image_path: Path to the source image file.
            max_width: Maximum image width after resize.
            max_height: Maximum image height after resize.
            resize_mode: Strategy for resizing (fit, stretch, crop).
            colour_filter: Colour filter to apply (none, grayscale, sepia, etc.).
            filter_levels: Quantisation levels for posterize/threshold filters.
            scan_direction: Order in which pixels are scanned.
            pitch_mode: How Y position maps to pitch.
            velocity_mode: How brightness maps to velocity.
            note_low: Lowest MIDI note (36 = C2).
            note_high: Highest MIDI note (96 = C7).
            scale: Musical scale for pitch quantisation.
            base_note: Root note offset (0=C, 2=D, etc.).
            step: Pixel sampling step (higher = fewer notes, faster).
            time_step: Time between consecutive notes in beats.
            duration: Duration of each note in beats.
            num_channels: Number of MIDI channels (1–16).
            brightness_threshold: Minimum brightness to trigger a note.
        """
        self.image_path = Path(image_path)
        self.config = {
            "max_width": max_width,
            "max_height": max_height,
            "resize_mode": resize_mode,
            "colour_filter": colour_filter,
            "filter_levels": filter_levels,
            "scan_direction": scan_direction,
            "pitch_mode": pitch_mode,
            "velocity_mode": velocity_mode,
            "note_low": note_low,
            "note_high": note_high,
            "scale": scale,
            "base_note": base_note,
            "step": step,
            "time_step": time_step,
            "duration": duration,
            "num_channels": num_channels,
            "brightness_threshold": brightness_threshold,
        }
        self._processed: Optional[ProcessedImage] = None
        self._notes: Optional[List[NoteMapping]] = None

    def _ensure_loaded(self) -> ProcessedImage:
        """Lazily load and process the image."""
        if self._processed is None:
            self._processed = process_image(
                str(self.image_path),
                max_width=self.config["max_width"],
                max_height=self.config["max_height"],
                resize_mode=self.config["resize_mode"],
                colour_filter=self.config["colour_filter"],
                filter_levels=self.config["filter_levels"],
            )
        return self._processed

    def process(self) -> List[NoteMapping]:
        """
        Process the image and generate note mappings.

        Returns:
            List of NoteMapping objects.
        """
        img = self._ensure_loaded()
        cfg = self.config

        # Generate scan order
        scan_coords = generate_scan_order(
            img.width, img.height,
            direction=cfg["scan_direction"],
        )

        notes: List[NoteMapping] = []
        pixels = img.pixels

        for idx, (x, y) in enumerate(scan_coords):
            # Skip pixels based on step
            if idx % cfg["step"] != 0:
                continue

            r, g, b, a = pixels[y, x]
            r_i, g_i, b_i, a_i = int(r * 255), int(g * 255), int(b * 255), int(a * 255)

            note = pixel_to_note(
                x=x,
                y=y,
                r=r_i,
                g=g_i,
                b=b_i,
                a=a_i,
                width=img.width,
                height=img.height,
                step=cfg["step"],
                time_step=cfg["time_step"],
                note_low=cfg["note_low"],
                note_high=cfg["note_high"],
                pitch_mode=cfg["pitch_mode"],
                velocity_mode=cfg["velocity_mode"],
                scale=cfg["scale"],
                base_note=cfg["base_note"],
                num_channels=cfg["num_channels"],
                duration=cfg["duration"],
                brightness_threshold=cfg["brightness_threshold"],
            )

            if note is not None:
                notes.append(note)

        self._notes = notes
        return notes

    def convert(
        self,
        output_path: str,
        *,
        tempo: int = 120,
        instruments: Optional[List[int]] = None,
        time_signature: Tuple[int, int] = (4, 4),
    ) -> str:
        """
        Full pipeline: process image, generate MIDI, and save to file.

        Args:
            output_path: Destination file path (.mid).
            tempo: Playback tempo in BPM.
            instruments: List of MIDI program numbers per channel.
            time_signature: Musical time signature (numerator, denominator).

        Returns:
            Absolute path to the generated MIDI file.
        """
        notes = self.process()

        if not notes:
            raise ValueError(
                "No notes were generated. The image may be too dark or too small. "
                "Try lowering the brightness_threshold or using a brighter image."
            )

        path = generate_midi(
            notes=notes,
            output_path=output_path,
            tempo=tempo,
            num_tracks=self.config["num_channels"],
            instruments=instruments,
            time_signature=time_signature,
        )

        return path

    def info(self) -> dict:
        """
        Get information about the source image and converter settings.

        Returns:
            Dictionary with image info and configuration.
        """
        img = self._ensure_loaded()
        return {
            "source": str(self.image_path.resolve()),
            "original_size": f"{img.original_width}x{img.original_height}",
            "processed_size": f"{img.width}x{img.height}",
            "config": {
                k: str(v) if isinstance(v, (ScanDirection, PitchMode, VelocityMode, ResizeMode, ColourFilter))
                else v
                for k, v in self.config.items()
            },
            "num_notes": len(self._notes) if self._notes else "not yet processed",
        }

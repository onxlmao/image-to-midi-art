"""
Command-line interface for the image-to-MIDI art converter.

Usage:
    python -m image_to_midi.cli input.jpg -o output.mid [options]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from image_to_midi.converter import ImageToMidi
from image_to_midi.image_processor import ColourFilter, ResizeMode
from image_to_midi.mapping import PitchMode, ScanDirection, VelocityMode
from image_to_midi.midi_generator import INSTRUMENTS


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all available options."""
    parser = argparse.ArgumentParser(
        prog="image-to-midi",
        description="Convert images into MIDI art files. "
                    "Pixel position maps to pitch and timing, "
                    "brightness maps to velocity, and hue maps to instrument.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion with defaults
  python -m image_to_midi.cli photo.jpg -o music.mid

  # Pentatonic scale, slower tempo, grayscale filter
  python -m image_to_midi.cli photo.jpg -o music.mid --scale pentatonic --tempo 80 --filter grayscale

  # High-pitched output with spiral scan and marimba
  python -m image_to_midi.cli photo.jpg -o music.mid --scan spiral_inward --note-high 108 --instruments marimba

  # Quick preview (low resolution, high step)
  python -m image_to_midi.cli photo.jpg -o music.mid --max-size 32 --step 2

Available instruments: %s
""" % ", ".join(sorted(INSTRUMENTS.keys())),
    )

    # ── Required arguments ──────────────────────────────────────────────
    parser.add_argument(
        "input",
        help="Path to the source image file (PNG, JPG, BMP, GIF, etc.).",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output path for the MIDI file (.mid). Required unless --info is used.",
    )

    # ── Image processing ────────────────────────────────────────────────
    img_group = parser.add_argument_group("Image Processing")
    img_group.add_argument(
        "--max-size",
        type=int,
        default=128,
        metavar="N",
        help="Maximum width and height after resize (default: 128).",
    )
    img_group.add_argument(
        "--resize-mode",
        choices=[m.value for m in ResizeMode],
        default="fit",
        help="Resize strategy: fit (preserve ratio), stretch, or crop (default: fit).",
    )
    img_group.add_argument(
        "--filter",
        choices=[f.value for f in ColourFilter],
        default="none",
        help="Colour filter to apply before conversion (default: none).",
    )
    img_group.add_argument(
        "--filter-levels",
        type=int,
        default=4,
        metavar="N",
        help="Quantisation levels for posterize/threshold filters (default: 4).",
    )

    # ── Musical mapping ─────────────────────────────────────────────────
    music_group = parser.add_argument_group("Musical Mapping")
    music_group.add_argument(
        "--scan",
        choices=[d.value for d in ScanDirection],
        default="left_to_right",
        help="Pixel scan direction / order (default: left_to_right).",
    )
    music_group.add_argument(
        "--pitch-mode",
        choices=[p.value for p in PitchMode],
        default="inverted",
        help="How Y position maps to pitch (default: inverted).",
    )
    music_group.add_argument(
        "--velocity-mode",
        choices=[v.value for v in VelocityMode],
        default="bright",
        help="How brightness maps to velocity (default: bright).",
    )
    music_group.add_argument(
        "--note-low",
        type=int,
        default=36,
        metavar="N",
        help="Lowest MIDI note (0-127, default: 36 = C2).",
    )
    music_group.add_argument(
        "--note-high",
        type=int,
        default=96,
        metavar="N",
        help="Highest MIDI note (0-127, default: 96 = C7).",
    )
    music_group.add_argument(
        "--scale",
        default="chromatic",
        choices=[
            "chromatic", "major", "natural_minor", "harmonic_minor",
            "melodic_minor", "pentatonic", "blues", "dorian",
            "mixolydian", "phrygian", "whole_tone",
        ],
        help="Musical scale for pitch quantisation (default: chromatic).",
    )
    music_group.add_argument(
        "--base-note",
        type=int,
        default=0,
        metavar="N",
        help="Root note offset (0=C, 2=D, 4=E, ..., 11=B; default: 0).",
    )

    # ── Timing ──────────────────────────────────────────────────────────
    time_group = parser.add_argument_group("Timing & Rhythm")
    time_group.add_argument(
        "--tempo",
        type=int,
        default=120,
        metavar="BPM",
        help="Playback tempo in BPM (default: 120).",
    )
    time_group.add_argument(
        "--time-step",
        type=float,
        default=0.15,
        metavar="BEATS",
        help="Time between consecutive notes in beats (default: 0.15).",
    )
    time_group.add_argument(
        "--duration",
        type=float,
        default=0.25,
        metavar="BEATS",
        help="Duration of each note in beats (default: 0.25).",
    )
    time_group.add_argument(
        "--time-sig",
        type=str,
        default="4/4",
        help="Time signature as N/D (default: 4/4).",
    )

    # ── Performance ─────────────────────────────────────────────────────
    perf_group = parser.add_argument_group("Performance")
    perf_group.add_argument(
        "--step",
        type=int,
        default=1,
        metavar="N",
        help="Pixel sampling step: 1 = every pixel, 2 = every other, etc. (default: 1).",
    )
    perf_group.add_argument(
        "--num-channels",
        type=int,
        default=4,
        metavar="N",
        help="Number of MIDI channels / instruments (1-16, default: 4).",
    )
    perf_group.add_argument(
        "--brightness-threshold",
        type=float,
        default=0.05,
        metavar="T",
        help="Minimum brightness to trigger a note (0.0-1.0, default: 0.05).",
    )
    perf_group.add_argument(
        "--instruments",
        type=str,
        nargs="+",
        default=None,
        help="Instrument names for each channel. "
             "Available: %s" % ", ".join(sorted(INSTRUMENTS.keys())),
    )

    # ── Utility ─────────────────────────────────────────────────────────
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print image and settings info without generating MIDI.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information.",
    )

    return parser


def parse_time_signature(sig_str: str) -> tuple[int, int]:
    """Parse a time signature string like '4/4' or '6/8'."""
    parts = sig_str.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid time signature: {sig_str}. Expected format: N/D")
    return int(parts[0]), int(parts[1])


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate inputs
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    if args.note_low < 0 or args.note_low > 127:
        print("Error: --note-low must be between 0 and 127", file=sys.stderr)
        return 1

    if args.note_high < 0 or args.note_high > 127:
        print("Error: --note-high must be between 0 and 127", file=sys.stderr)
        return 1

    if args.note_low >= args.note_high:
        print("Error: --note-low must be less than --note-high", file=sys.stderr)
        return 1

    # Parse instruments
    instrument_numbers = None
    if args.instruments:
        instrument_numbers = []
        for name in args.instruments:
            if name in INSTRUMENTS:
                instrument_numbers.append(INSTRUMENTS[name])
            elif name.isdigit():
                instrument_numbers.append(int(name))
            else:
                print(f"Warning: Unknown instrument '{name}', using piano (0)", file=sys.stderr)
                instrument_numbers.append(0)

    # Parse time signature
    try:
        time_sig = parse_time_signature(args.time_sig)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Create converter
    try:
        converter = ImageToMidi(
            args.input,
            max_width=args.max_size,
            max_height=args.max_size,
            resize_mode=ResizeMode(args.resize_mode),
            colour_filter=ColourFilter(args.filter),
            filter_levels=args.filter_levels,
            scan_direction=ScanDirection(args.scan),
            pitch_mode=PitchMode(args.pitch_mode),
            velocity_mode=VelocityMode(args.velocity_mode),
            note_low=args.note_low,
            note_high=args.note_high,
            scale=args.scale,
            base_note=args.base_note,
            step=args.step,
            time_step=args.time_step,
            duration=args.duration,
            num_channels=args.num_channels,
            brightness_threshold=args.brightness_threshold,
        )
    except Exception as e:
        print(f"Error loading image: {e}", file=sys.stderr)
        return 1

    # Info mode
    if args.info:
        info = converter.info()
        print("=== Image to MIDI Converter ===")
        print(f"  Source:          {info['source']}")
        print(f"  Original size:   {info['original_size']}")
        print(f"  Processed size:  {info['processed_size']}")
        print()
        print("Configuration:")
        for key, val in info["config"].items():
            print(f"  {key}: {val}")
        print()
        print(f"  Notes generated: {info['num_notes']}")
        return 0

    # Convert
    if args.verbose:
        print(f"Loading image: {args.input}")
        print(f"Settings: scale={args.scale}, tempo={args.tempo} BPM, "
              f"scan={args.scan}, filter={args.filter}")

    try:
        output_path = converter.convert(
            args.output,
            tempo=args.tempo,
            instruments=instrument_numbers,
            time_signature=time_sig,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error generating MIDI: {e}", file=sys.stderr)
        return 1

    info = converter.info()
    if args.verbose:
        print(f"Processed image: {info['processed_size']}")
        print(f"Notes generated: {info['num_notes']}")

    print(f"MIDI file saved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

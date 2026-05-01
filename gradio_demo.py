"""
Gradio Web Demo — Image to MIDI Art Converter

Run with:
    python gradio_demo.py

Then open the local URL shown in the terminal (usually http://127.0.0.1:7860).
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import gradio as gr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from PIL import Image

# Ensure the package root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from image_to_midi.converter import ImageToMidi
from image_to_midi.image_processor import (
    ColourFilter,
    ProcessedImage,
    ResizeMode,
    apply_filter,
    load_image,
    resize_image,
)
from image_to_midi.mapping import (
    NOTE_NAMES,
    NoteMapping,
    PitchMode,
    ScanDirection,
    VelocityMode,
)
from image_to_midi.midi_generator import INSTRUMENTS

# ── Matplotlib font setup ───────────────────────────────────────────
plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ── Constants ───────────────────────────────────────────────────────
OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="img2midi_"))
INSTRUMENT_NAMES = sorted(INSTRUMENTS.keys())
INSTRUMENT_PROGRAMS = sorted(set(INSTRUMENTS.values()))

SCALE_CHOICES = [
    "chromatic", "major", "natural_minor", "harmonic_minor",
    "melodic_minor", "pentatonic", "blues", "dorian",
    "mixolydian", "phrygian", "whole_tone",
]

SCAN_CHOICES = [d.value for d in ScanDirection]
FILTER_CHOICES = [f.value for f in ColourFilter]
RESIZE_CHOICES = [r.value for r in ResizeMode]
PITCH_CHOICES = [p.value for p in PitchMode]
VELOCITY_CHOICES = [v.value for v in VelocityMode]
BASE_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# ── Helper functions ────────────────────────────────────────────────

def _get_instrument_ids(names: list[str]) -> list[int]:
    """Convert instrument names to MIDI program numbers."""
    programs = []
    for name in names:
        if name in INSTRUMENTS:
            programs.append(INSTRUMENTS[name])
        else:
            programs.append(0)
    return programs


def generate_piano_roll(notes: list[NoteMapping], img_size: tuple[int, int]) -> np.ndarray:
    """Generate a piano roll visualization image."""
    if not notes:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No notes generated", ha="center", va="center",
                fontsize=16, color="gray")
        ax.set_axis_off()
        fig.tight_layout()
        fig.canvas.draw()
        arr = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        arr = arr.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        plt.close(fig)
        return arr

    notes_pitch = [n.note for n in notes]
    notes_time = [n.time_offset for n in notes]
    notes_vel = [n.velocity / 127.0 for n in notes]
    notes_dur = [n.duration for n in notes]
    notes_ch = [n.channel for n in notes]

    pitch_min = min(notes_pitch) - 2
    pitch_max = max(notes_pitch) + 2
    time_max = max(notes_time) + 1.0

    channel_colors = [
        "#6366f1", "#f43f5e", "#10b981", "#f59e0b",
        "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16",
        "#ef4444", "#14b8a6", "#a855f7", "#eab308",
        "#3b82f6", "#22c55e", "#d946ef", "#f97316",
    ]

    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    for i in range(len(notes)):
        color = channel_colors[notes_ch[i] % len(channel_colors)]
        alpha = 0.3 + 0.7 * notes_vel[i]
        rect = mpatches.Rectangle(
            (notes_time[i], notes_pitch[i] - 0.4),
            notes_dur[i] * 0.8, 0.8,
            linewidth=0, facecolor=color, alpha=alpha,
        )
        ax.add_patch(rect)

    ax.set_xlim(0, time_max)
    ax.set_ylim(pitch_min, pitch_max)
    ax.set_xlabel("Time (beats)", color="white", fontsize=11)
    ax.set_ylabel("MIDI Note", color="white", fontsize=11)
    ax.set_title("Piano Roll  —  Generated MIDI Notes", color="white",
                 fontsize=14, fontweight="bold", pad=12)
    ax.tick_params(colors="white", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#333")

    unique_channels = sorted(set(notes_ch))
    handles = [
        mpatches.Patch(color=channel_colors[ch % len(channel_colors)],
                        label=f"Ch {ch + 1}")
        for ch in unique_channels[:8]
    ]
    if handles:
        ax.legend(handles=handles, loc="upper right", fontsize=8,
                  facecolor="#1a1a2e", edgecolor="#444", labelcolor="white")

    fig.tight_layout()
    fig.canvas.draw()
    arr = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    arr = arr.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    plt.close(fig)
    return arr


def generate_note_histogram(notes: list[NoteMapping]) -> np.ndarray:
    """Generate a histogram of note pitch distribution."""
    if not notes:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "No notes generated", ha="center", va="center",
                fontsize=16, color="gray")
        ax.set_axis_off()
        fig.tight_layout()
        fig.canvas.draw()
        arr = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        arr = arr.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        plt.close(fig)
        return arr

    pitches = [n.note for n in notes]
    note_name_labels = [
        "C", "C#", "D", "D#", "E", "F",
        "F#", "G", "G#", "A", "A#", "B",
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), dpi=100)
    fig.patch.set_facecolor("#1a1a2e")

    ax1.set_facecolor("#16213e")
    ax1.hist(pitches, bins=range(min(pitches), max(pitches) + 2),
             color="#6366f1", alpha=0.8, edgecolor="#818cf8", linewidth=0.5)
    ax1.set_title("Pitch Distribution", color="white", fontsize=12, fontweight="bold")
    ax1.set_xlabel("MIDI Note", color="white", fontsize=10)
    ax1.set_ylabel("Count", color="white", fontsize=10)
    ax1.tick_params(colors="white", labelsize=8)
    for spine in ax1.spines.values():
        spine.set_color("#333")

    ax2.set_facecolor("#16213e")
    note_in_scale = [n % 12 for n in pitches]
    counts = [note_in_scale.count(i) for i in range(12)]
    ax2.bar(note_name_labels, counts, color="#f43f5e", alpha=0.8,
            edgecolor="#fb7185", linewidth=0.5)
    ax2.set_title("Note Class Distribution", color="white", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Note Name", color="white", fontsize=10)
    ax2.set_ylabel("Count", color="white", fontsize=10)
    ax2.tick_params(colors="white", labelsize=8)
    for spine in ax2.spines.values():
        spine.set_color("#333")

    fig.tight_layout()
    fig.canvas.draw()
    arr = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    arr = arr.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    plt.close(fig)
    return arr


# ── Main conversion function ────────────────────────────────────────

def convert_image_to_midi(
    image,
    max_size: int,
    resize_mode: str,
    colour_filter: str,
    filter_levels: int,
    scan_direction: str,
    pitch_mode: str,
    velocity_mode: str,
    note_low: int,
    note_high: int,
    scale: str,
    base_note: str,
    tempo: int,
    time_step: float,
    duration: float,
    step: int,
    num_channels: int,
    brightness_threshold: float,
    instrument_ch1: str,
    instrument_ch2: str,
    instrument_ch3: str,
    instrument_ch4: str,
):
    """
    Main conversion function called by Gradio.

    Returns:
        (preview_image, piano_roll_image, histogram_image, midi_file_path, stats_text)
    """
    if image is None:
        return None, None, None, None, "Please upload an image first."

    # Save uploaded image to temp file
    input_path = OUTPUT_DIR / f"input_{int(time.time() * 1000)}.png"
    output_path = OUTPUT_DIR / f"output_{int(time.time() * 1000)}.mid"

    img = Image.fromarray(image)
    img.save(str(input_path))

    try:
        converter = ImageToMidi(
            str(input_path),
            max_width=max_size,
            max_height=max_size,
            resize_mode=ResizeMode(resize_mode),
            colour_filter=ColourFilter(colour_filter),
            filter_levels=filter_levels,
            scan_direction=ScanDirection(scan_direction),
            pitch_mode=PitchMode(pitch_mode),
            velocity_mode=VelocityMode(velocity_mode),
            note_low=note_low,
            note_high=note_high,
            scale=scale,
            base_note=BASE_NOTE_NAMES.index(base_note) if base_note in BASE_NOTE_NAMES else 0,
            step=step,
            time_step=time_step,
            duration=duration,
            num_channels=num_channels,
            brightness_threshold=brightness_threshold,
        )

        notes = converter.process()

        if not notes:
            return None, None, None, None, (
                "No notes generated! The image may be too dark or too small.\n\n"
                "Try:\n"
                "  - Lowering the brightness threshold\n"
                "  - Using a brighter/higher-contrast image\n"
                "  - Increasing the max resolution"
            )

        # Generate processed image preview (numpy for Gradio)
        processed = converter._processed
        preview_arr = (processed.pixels[:, :, :3] * 255).astype(np.uint8)

        # Generate visualizations
        piano_roll_arr = generate_piano_roll(notes, (processed.width, processed.height))
        histogram_arr = generate_note_histogram(notes)

        # Generate MIDI file
        instruments = _get_instrument_ids([
            instrument_ch1, instrument_ch2, instrument_ch3, instrument_ch4,
        ])
        midi_path = converter.convert(str(output_path), tempo=tempo, instruments=instruments)

        # Compute stats
        pitches = [n.note for n in notes]
        velocities = [n.velocity for n in notes]
        times = [n.time_offset for n in notes]
        channels_used = sorted(set(n.channel for n in notes))

        note_min_name = NOTE_NAMES[min(pitches) % 12]
        note_max_name = NOTE_NAMES[max(pitches) % 12]

        stats = (
            f"### Conversion Complete\n\n"
            f"| Property | Value |\n"
            f"|---|---|\n"
            f"| **Original size** | {processed.original_width} x {processed.original_height} |\n"
            f"| **Processed size** | {processed.width} x {processed.height} |\n"
            f"| **Total notes** | {len(notes)} |\n"
            f"| **Pitch range** | {min(pitches)} ({note_min_name}) — {max(pitches)} ({note_max_name}) |\n"
            f"| **Velocity range** | {min(velocities)} — {max(velocities)} |\n"
            f"| **Avg velocity** | {sum(velocities) / len(velocities):.1f} |\n"
            f"| **Duration** | {max(times):.1f} beats |\n"
            f"| **Channels used** | {', '.join(str(c + 1) for c in channels_used)} |\n"
            f"| **Scale** | {scale} |\n"
            f"| **Tempo** | {tempo} BPM |\n"
            f"| **MIDI file** | `{Path(midi_path).stat().st_size / 1024:.1f} KB` |\n"
        )

        return preview_arr, piano_roll_arr, histogram_arr, midi_path, stats

    except Exception as e:
        return None, None, None, None, f"Error: {str(e)}"


def update_filter_levels_visibility(filter_name: str):
    """Show/hide filter levels slider based on filter type."""
    if filter_name in ("posterize", "threshold"):
        return gr.Slider(visible=True)
    return gr.Slider(visible=False)


# ── Build Gradio UI ─────────────────────────────────────────────────

def build_demo() -> gr.Blocks:
    """Build and return the Gradio Blocks interface."""

    with gr.Blocks(
        title="Image to MIDI Art Converter",
    ) as demo:

        # ── Header ──────────────────────────────────────────────────
        gr.HTML("""
            <div style="text-align: center; margin-bottom: 16px;">
                <h1 style="font-size: 2.2rem;
                           background: linear-gradient(135deg, #6366f1, #f43f5e, #10b981);
                           -webkit-background-clip: text;
                           -webkit-text-fill-color: transparent;
                           margin-bottom: 4px;">
                    Image to MIDI Art Converter
                </h1>
                <p style="color: #6b7280; font-size: 1rem;">
                    Turn any image into music — upload a photo, tweak the settings, and download your MIDI file.
                </p>
            </div>
        """)

        with gr.Row():
            # ── LEFT COLUMN: Settings ────────────────────────────────
            with gr.Column(scale=1):

                # Image Upload
                with gr.Group():
                    gr.Markdown("**Upload Image**")
                    input_image = gr.Image(
                        label="Source Image",
                        type="numpy",
                        sources=["upload", "clipboard"],
                        height=220,
                    )

                # Image Processing
                with gr.Group():
                    gr.Markdown("**Image Processing**")
                    with gr.Row():
                        max_size = gr.Slider(
                            minimum=16, maximum=256, value=64, step=8,
                            label="Max Resolution",
                            info="Pixels per axis (higher = more detail but slower)",
                        )
                        resize_mode = gr.Dropdown(
                            RESIZE_CHOICES, value="fit",
                            label="Resize Mode",
                        )
                    colour_filter = gr.Dropdown(
                        FILTER_CHOICES, value="none",
                        label="Colour Filter",
                        info="Apply a filter before converting",
                    )
                    filter_levels = gr.Slider(
                        minimum=2, maximum=16, value=4, step=1,
                        label="Filter Levels",
                        info="Quantisation levels (for posterize/threshold)",
                        visible=False,
                    )
                    colour_filter.change(
                        fn=update_filter_levels_visibility,
                        inputs=[colour_filter],
                        outputs=[filter_levels],
                    )

                # Musical Mapping
                with gr.Group():
                    gr.Markdown("**Musical Mapping**")
                    scan_direction = gr.Dropdown(
                        SCAN_CHOICES, value="left_to_right",
                        label="Scan Direction",
                        info="Order pixels are read to create notes",
                    )
                    with gr.Row():
                        scale = gr.Dropdown(
                            SCALE_CHOICES, value="pentatonic",
                            label="Scale",
                            info="Musical scale for pitch quantisation",
                        )
                        base_note = gr.Dropdown(
                            BASE_NOTE_NAMES, value="C",
                            label="Root Note",
                        )
                    with gr.Row():
                        note_low = gr.Slider(
                            minimum=0, maximum=108, value=36, step=1,
                            label="Lowest Note",
                            info="36 = C2",
                        )
                        note_high = gr.Slider(
                            minimum=12, maximum=127, value=96, step=1,
                            label="Highest Note",
                            info="96 = C7",
                        )
                    with gr.Row():
                        pitch_mode = gr.Dropdown(
                            PITCH_CHOICES, value="inverted",
                            label="Pitch Mode",
                        )
                        velocity_mode = gr.Dropdown(
                            VELOCITY_CHOICES, value="bright",
                            label="Velocity Mode",
                        )

                # Timing & Rhythm
                with gr.Group():
                    gr.Markdown("**Timing & Rhythm**")
                    with gr.Row():
                        tempo = gr.Slider(
                            minimum=30, maximum=300, value=120, step=5,
                            label="Tempo (BPM)",
                        )
                        time_step = gr.Slider(
                            minimum=0.05, maximum=1.0, value=0.15, step=0.05,
                            label="Time Step (beats)",
                            info="Gap between consecutive notes",
                        )
                    with gr.Row():
                        duration = gr.Slider(
                            minimum=0.05, maximum=2.0, value=0.25, step=0.05,
                            label="Note Duration (beats)",
                        )
                        step = gr.Slider(
                            minimum=1, maximum=5, value=1, step=1,
                            label="Pixel Step",
                            info="1=every pixel, 2=every other, etc.",
                        )

                # Instruments
                with gr.Group():
                    gr.Markdown("**Instruments**")
                    with gr.Row():
                        instrument_ch1 = gr.Dropdown(
                            INSTRUMENT_NAMES, value="acoustic_grand_piano",
                            label="Channel 1",
                        )
                        instrument_ch2 = gr.Dropdown(
                            INSTRUMENT_NAMES, value="vibraphone",
                            label="Channel 2",
                        )
                    with gr.Row():
                        instrument_ch3 = gr.Dropdown(
                            INSTRUMENT_NAMES, value="music_box",
                            label="Channel 3",
                        )
                        instrument_ch4 = gr.Dropdown(
                            INSTRUMENT_NAMES, value="flute",
                            label="Channel 4",
                        )

                # Performance
                with gr.Group():
                    gr.Markdown("**Performance**")
                    with gr.Row():
                        num_channels = gr.Slider(
                            minimum=1, maximum=16, value=4, step=1,
                            label="Channels",
                        )
                        brightness_threshold = gr.Slider(
                            minimum=0.0, maximum=0.5, value=0.05, step=0.01,
                            label="Brightness Threshold",
                            info="Min brightness to trigger a note",
                        )

                # Convert Button
                convert_btn = gr.Button(
                    "Convert to MIDI",
                    variant="primary",
                    elem_id="convert-btn",
                    size="lg",
                )

            # ── RIGHT COLUMN: Outputs ────────────────────────────────
            with gr.Column(scale=1):

                # MIDI download
                with gr.Group():
                    gr.Markdown("**MIDI Output**")
                    midi_output = gr.File(
                        label="Download MIDI File",
                        file_types=[".mid"],
                        interactive=False,
                    )

                # Stats
                with gr.Group():
                    gr.Markdown("**Statistics**")
                    stats_output = gr.Markdown(
                        value="*Upload an image and click **Convert to MIDI** to see results.*"
                    )

                # Piano Roll
                with gr.Group():
                    gr.Markdown("**Piano Roll Visualization**")
                    piano_roll_output = gr.Image(
                        label="Piano Roll",
                        type="numpy",
                        height=320,
                        show_label=False,
                    )

                # Processed Image Preview
                with gr.Group():
                    gr.Markdown("**Processed Image Preview**")
                    preview_output = gr.Image(
                        label="Preview",
                        type="numpy",
                        height=220,
                        show_label=False,
                    )

                # Histogram
                with gr.Group():
                    gr.Markdown("**Note Distribution**")
                    histogram_output = gr.Image(
                        label="Histogram",
                        type="numpy",
                        height=220,
                        show_label=False,
                    )

        # ── Preset Buttons ──────────────────────────────────────────
        gr.Markdown("---")
        gr.Markdown("**Quick Presets**")
        with gr.Row():
            preset_ambient = gr.Button("Ambient Pad", size="sm")
            preset_8bit = gr.Button("8-Bit Retro", size="sm")
            preset_gentle = gr.Button("Gentle Melody", size="sm")
            preset_dense = gr.Button("Dense Chaos", size="sm")

        # ── Wire up events ──────────────────────────────────────────

        # Main conversion
        convert_btn.click(
            fn=convert_image_to_midi,
            inputs=[
                input_image, max_size, resize_mode, colour_filter, filter_levels,
                scan_direction, pitch_mode, velocity_mode,
                note_low, note_high, scale, base_note,
                tempo, time_step, duration, step, num_channels,
                brightness_threshold,
                instrument_ch1, instrument_ch2, instrument_ch3, instrument_ch4,
            ],
            outputs=[
                preview_output, piano_roll_output, histogram_output,
                midi_output, stats_output,
            ],
        )

        # ── Preset handlers ─────────────────────────────────────────
        # Each returns gr.update() for every input component
        preset_targets = [
            max_size, resize_mode, colour_filter, filter_levels,
            scan_direction, pitch_mode, velocity_mode,
            note_low, note_high, scale, base_note,
            tempo, time_step, duration, step, num_channels,
            brightness_threshold,
            instrument_ch1, instrument_ch2, instrument_ch3, instrument_ch4,
        ]

        def apply_ambient():
            return [
                gr.Slider(value=64), gr.Dropdown(value="fit"), gr.Dropdown(value="sepia"),
                gr.Slider(value=3, visible=False), gr.Dropdown(value="spiral_inward"),
                gr.Dropdown(value="inverted"), gr.Dropdown(value="bright"),
                gr.Slider(value=36), gr.Slider(value=84), gr.Dropdown(value="major"),
                gr.Dropdown(value="C"), gr.Slider(value=60), gr.Slider(value=0.2),
                gr.Slider(value=0.6), gr.Slider(value=1), gr.Slider(value=4),
                gr.Slider(value=0.03),
                gr.Dropdown(value="synth_pad_warm"), gr.Dropdown(value="synth_pad_new_age"),
                gr.Dropdown(value="synth_pad_choir"), gr.Dropdown(value="celesta"),
            ]

        def apply_8bit():
            return [
                gr.Slider(value=48), gr.Dropdown(value="fit"), gr.Dropdown(value="posterize"),
                gr.Slider(value=3, visible=True), gr.Dropdown(value="left_to_right"),
                gr.Dropdown(value="inverted"), gr.Dropdown(value="bright"),
                gr.Slider(value=48), gr.Slider(value=84), gr.Dropdown(value="major"),
                gr.Dropdown(value="C"), gr.Slider(value=140), gr.Slider(value=0.1),
                gr.Slider(value=0.15), gr.Slider(value=2), gr.Slider(value=2),
                gr.Slider(value=0.05),
                gr.Dropdown(value="synth_lead_square"), gr.Dropdown(value="synth_lead_saw"),
                gr.Dropdown(value="music_box"), gr.Dropdown(value="electric_piano_1"),
            ]

        def apply_gentle():
            return [
                gr.Slider(value=64), gr.Dropdown(value="fit"), gr.Dropdown(value="none"),
                gr.Slider(value=4, visible=False), gr.Dropdown(value="left_to_right"),
                gr.Dropdown(value="inverted"), gr.Dropdown(value="bright"),
                gr.Slider(value=48), gr.Slider(value=72), gr.Dropdown(value="pentatonic"),
                gr.Dropdown(value="G"), gr.Slider(value=80), gr.Slider(value=0.25),
                gr.Slider(value=0.5), gr.Slider(value=1), gr.Slider(value=2),
                gr.Slider(value=0.05),
                gr.Dropdown(value="acoustic_grand_piano"), gr.Dropdown(value="electric_piano_1"),
                gr.Dropdown(value="music_box"), gr.Dropdown(value="vibraphone"),
            ]

        def apply_dense():
            return [
                gr.Slider(value=128), gr.Dropdown(value="fit"), gr.Dropdown(value="none"),
                gr.Slider(value=4, visible=False), gr.Dropdown(value="diagonal_tl_br"),
                gr.Dropdown(value="mirror"), gr.Dropdown(value="bright"),
                gr.Slider(value=24), gr.Slider(value=108), gr.Dropdown(value="chromatic"),
                gr.Dropdown(value="C"), gr.Slider(value=160), gr.Slider(value=0.05),
                gr.Slider(value=0.1), gr.Slider(value=1), gr.Slider(value=8),
                gr.Slider(value=0.02),
                gr.Dropdown(value="harpsichord"), gr.Dropdown(value="celesta"),
                gr.Dropdown(value="glockenspiel"), gr.Dropdown(value="xylophone"),
            ]

        preset_ambient.click(fn=apply_ambient, outputs=preset_targets)
        preset_8bit.click(fn=apply_8bit, outputs=preset_targets)
        preset_gentle.click(fn=apply_gentle, outputs=preset_targets)
        preset_dense.click(fn=apply_dense, outputs=preset_targets)

    return demo


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Image to MIDI Art Converter  —  Gradio Demo")
    print("=" * 50)
    demo = build_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
        ),
        css="""
            #convert-btn {
                background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
                border: none !important;
                font-size: 1.1rem !important;
                padding: 12px 32px !important;
            }
            #convert-btn:hover {
                background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
            }
        """,
    )

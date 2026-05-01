"""
MIDI file generation from note mappings.

Creates structured MIDI files with proper headers, tracks,
tempo, and program change messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from midiutil import MIDIFile

from image_to_midi.mapping import NoteMapping


# General MIDI instrument programs (subset of the most useful ones)
INSTRUMENTS = {
    "acoustic_grand_piano": 0,
    "bright_acoustic_piano": 1,
    "electric_grand_piano": 2,
    "honkytonk_piano": 3,
    "electric_piano_1": 4,
    "electric_piano_2": 5,
    "harpsichord": 6,
    "clavinet": 7,
    "celesta": 8,
    "glockenspiel": 9,
    "music_box": 10,
    "vibraphone": 11,
    "marimba": 12,
    "xylophone": 13,
    "tubular_bells": 14,
    "dulcimer": 15,
    "drawbar_organ": 16,
    "percussive_organ": 17,
    "rock_organ": 18,
    "church_organ": 19,
    "accordion": 21,
    "acoustic_guitar_nylon": 24,
    "acoustic_guitar_steel": 25,
    "electric_guitar_jazz": 26,
    "electric_guitar_clean": 27,
    "electric_guitar_muted": 28,
    "overdriven_guitar": 29,
    "distortion_guitar": 30,
    "violin": 40,
    "viola": 41,
    "cello": 42,
    "contrabass": 43,
    "trumpet": 56,
    "trombone": 57,
    "flute": 73,
    "recorder": 74,
    "pan_flute": 75,
    "sitar": 104,
    "banjo": 105,
    "synth_lead_square": 80,
    "synth_lead_saw": 81,
    "synth_lead_calliope": 82,
    "synth_pad_new_age": 88,
    "synth_pad_warm": 89,
    "synth_pad_choir": 92,
    "synth_pad_bowed": 93,
}


def generate_midi(
    notes: List[NoteMapping],
    output_path: str,
    tempo: int = 120,
    num_tracks: int = 4,
    instruments: Optional[List[int]] = None,
    time_signature: Tuple[int, int] = (4, 4),
) -> str:
    """
    Generate a MIDI file from a list of note mappings.

    The notes are distributed across multiple tracks based on their channel
    value, with each track assigned its own instrument.

    Args:
        notes: List of NoteMapping objects representing the MIDI events.
        output_path: File path for the output .mid file.
        tempo: Tempo in BPM.
        num_tracks: Number of MIDI tracks to create.
        instruments: List of MIDI program numbers for each track.
            If None, a default piano-based set is used.
        time_signature: Time signature as (numerator, denominator).

    Returns:
        Absolute path to the generated MIDI file.
    """
    # Default instruments (piano, electric piano, vibraphone, music box)
    if instruments is None:
        instruments = [0, 4, 11, 10]
    # Pad or trim instruments list
    while len(instruments) < num_tracks:
        instruments.append(0)
    instruments = instruments[:num_tracks]

    # Create MIDI file with one track (we'll use channels within it for simplicity)
    # midiutil's track 0 is special, so we use track 0 with multiple channels
    midi = MIDIFile(numTracks=1)

    # Set tempo and time signature
    midi.addTempo(0, 0, tempo)
    midi.addTimeSignature(0, 0, time_signature[0], time_signature[1], clocks_per_tick=24)

    # Set instrument for each channel
    for ch_idx in range(min(num_tracks, 16)):
        track = 0
        midi.addProgramChange(track, ch_idx, 0, instruments[ch_idx])

    # Group notes by channel for proper ordering
    channel_notes: dict[int, List[NoteMapping]] = {}
    for note in notes:
        ch = note.channel % min(num_tracks, 16)
        if ch not in channel_notes:
            channel_notes[ch] = []
        channel_notes[ch].append(note)

    # Add notes to MIDI file
    for ch, ch_notes in channel_notes.items():
        track = 0
        for n in ch_notes:
            midi.addNote(
                track=track,
                channel=ch,
                pitch=n.note,
                time=n.time_offset,
                duration=n.duration,
                volume=n.velocity,
            )

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "wb") as f:
        midi.writeFile(f)

    return str(output.resolve())

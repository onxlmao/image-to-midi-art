"""
Image loading, preprocessing, and pixel extraction.

Handles resizing, colour space conversion, and pixel sampling
to prepare image data for MIDI conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

import numpy as np
from PIL import Image


class ResizeMode(str, Enum):
    """Strategy for resizing the source image."""
    FIT = "fit"             # Fit within max dimensions, preserving aspect ratio
    STRETCH = "stretch"     # Stretch to exact dimensions
    CROP = "crop"           # Center-crop to exact dimensions


class ColourFilter(str, Enum):
    """Colour filter to apply before processing."""
    NONE = "none"
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    INVERT = "invert"
    POSTERIZE = "posterize"
    THRESHOLD = "threshold"


@dataclass
class ProcessedImage:
    """Processed image ready for MIDI conversion."""
    width: int
    height: int
    pixels: np.ndarray          # Shape: (height, width, 4) — RGBA float 0-1
    original_width: int
    original_height: int


def load_image(path: str) -> Image.Image:
    """
    Load an image from disk and convert to RGBA.

    Args:
        path: File path to the image.

    Returns:
        PIL Image in RGBA mode.

    Raises:
        FileNotFoundError: If the image file does not exist.
        PIL.UnidentifiedImageError: If the file is not a valid image.
    """
    img = Image.open(path).convert("RGBA")
    return img


def resize_image(
    img: Image.Image,
    max_width: int = 128,
    max_height: int = 128,
    mode: ResizeMode = ResizeMode.FIT,
) -> Image.Image:
    """
    Resize the image to manageable dimensions for MIDI conversion.

    Args:
        img: Source PIL image.
        max_width: Maximum target width.
        max_height: Maximum target height.
        mode: Resize strategy.

    Returns:
        Resized PIL image.
    """
    orig_w, orig_h = img.size

    if mode == ResizeMode.STRETCH:
        return img.resize((max_width, max_height), Image.LANCZOS)

    if mode == ResizeMode.CROP:
        aspect = orig_w / orig_h
        target_aspect = max_width / max_height

        if aspect > target_aspect:
            new_w = int(orig_h * target_aspect)
            left = (orig_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, orig_h))
        else:
            new_h = int(orig_w / target_aspect)
            top = (orig_h - new_h) // 2
            img = img.crop((0, top, orig_w, top + new_h))

        return img.resize((max_width, max_height), Image.LANCZOS)

    # FIT (default) — preserve aspect ratio
    img.thumbnail((max_width, max_height), Image.LANCZOS)
    return img


def apply_filter(
    img: Image.Image,
    filter_type: ColourFilter = ColourFilter.NONE,
    levels: int = 4,
) -> Image.Image:
    """
    Apply a colour filter to the image.

    Args:
        img: Source PIL image (RGBA).
        filter_type: Type of filter to apply.
        levels: Number of levels for posterization/threshold.

    Returns:
        Filtered PIL image.
    """
    if filter_type == ColourFilter.NONE:
        return img

    if filter_type == ColourFilter.GRAYSCALE:
        gray = img.convert("L")
        return gray.convert("RGBA")

    if filter_type == ColourFilter.INVERT:
        arr = np.array(img)
        arr[:, :, :3] = 255 - arr[:, :, :3]
        return Image.fromarray(arr, "RGBA")

    if filter_type == ColourFilter.SEPIA:
        arr = np.array(img, dtype=np.float64)
        sepia_matrix = np.array([
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131],
        ])
        rgb = arr[:, :, :3]
        sepia = rgb @ sepia_matrix.T
        sepia = np.clip(sepia, 0, 255).astype(np.uint8)
        arr[:, :, :3] = sepia
        return Image.fromarray(arr, "RGBA")

    if filter_type == ColourFilter.POSTERIZE:
        arr = np.array(img)
        step = 256 // levels
        arr[:, :, :3] = (arr[:, :, :3] // step) * step
        return Image.fromarray(arr, "RGBA")

    if filter_type == ColourFilter.THRESHOLD:
        arr = np.array(img.convert("L"))
        threshold = 256 // (levels + 1)
        arr = np.where(arr > threshold, 255, 0).astype(np.uint8)
        return Image.fromarray(arr, "L").convert("RGBA")

    return img


def extract_pixels(img: Image.Image) -> np.ndarray:
    """
    Extract pixel data as a normalised RGBA numpy array.

    Args:
        img: PIL image in RGBA mode.

    Returns:
        Numpy array of shape (height, width, 4) with float values 0.0–1.0.
    """
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr


def sample_pixels(
    pixels: np.ndarray,
    step: int = 1,
) -> List[Tuple[int, int, float, float, float, float]]:
    """
    Sample pixels from the image at regular intervals.

    Args:
        pixels: RGBA pixel array (height, width, 4).
        step: Sampling step (1 = every pixel, 2 = every other pixel, etc.).

    Returns:
        List of (x, y, r, g, b, a) tuples with values 0.0–1.0.
    """
    height, width = pixels.shape[:2]
    samples = []

    for y in range(0, height, step):
        for x in range(0, width, step):
            r, g, b, a = pixels[y, x]
            samples.append((x, y, float(r), float(g), float(b), float(a)))

    return samples


def process_image(
    path: str,
    max_width: int = 128,
    max_height: int = 128,
    resize_mode: ResizeMode = ResizeMode.FIT,
    colour_filter: ColourFilter = ColourFilter.NONE,
    filter_levels: int = 4,
) -> ProcessedImage:
    """
    Full image processing pipeline: load, resize, filter, and extract pixels.

    Args:
        path: Path to the source image.
        max_width: Maximum width after resize.
        max_height: Maximum height after resize.
        resize_mode: Resize strategy.
        colour_filter: Colour filter to apply.
        filter_levels: Levels for posterize/threshold filters.

    Returns:
        ProcessedImage with pixel data ready for conversion.
    """
    img = load_image(path)
    original_width, original_height = img.size

    img = resize_image(img, max_width, max_height, resize_mode)
    img = apply_filter(img, colour_filter, filter_levels)
    pixels = extract_pixels(img)

    return ProcessedImage(
        width=img.size[0],
        height=img.size[1],
        pixels=pixels,
        original_width=original_width,
        original_height=original_height,
    )

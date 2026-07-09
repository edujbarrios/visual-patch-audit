"""Feature extraction helpers for image patch auditing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def is_supported_image(path: str | Path) -> bool:
    """Return True when a path has a supported image extension."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def inspect_patch(image_path: str | Path) -> dict[str, Any]:
    """Inspect one image patch and return JSON-serializable visual features.

    Raises:
        ValueError: If the path is not a supported, readable image file.
    """
    path = Path(image_path)
    if not path.is_file():
        raise ValueError(f"Image path does not exist or is not a file: {path}")
    if not is_supported_image(path):
        raise ValueError(f"Unsupported image type: {path}")

    try:
        with Image.open(path) as image:
            original_mode = image.mode
            rgb = image.convert("RGB")
            width, height = rgb.size
            rgb_array = np.asarray(rgb, dtype=np.float32) / 255.0
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"Could not read image: {path}") from exc

    gray = (
        0.299 * rgb_array[:, :, 0]
        + 0.587 * rgb_array[:, :, 1]
        + 0.114 * rgb_array[:, :, 2]
    )
    gradient = _gradient_magnitude(gray)
    gray_histogram = _normalized_histogram(gray, bins=32, value_range=(0.0, 1.0))
    color_histogram = _color_histogram(rgb_array)

    return {
        "path": str(path),
        "width": int(width),
        "height": int(height),
        "mode": original_mode,
        "brightness": round(float(np.mean(gray)), 6),
        "contrast": round(float(np.std(gray)), 6),
        "edge_density": round(float(np.mean(gradient > 0.15)), 6),
        "entropy": round(_entropy(gray_histogram), 6),
        "sharpness": round(float(np.var(gradient) * 10000.0), 6),
        "aspect_ratio": round(float(width / height), 6) if height else 0.0,
        "color_histogram": color_histogram,
        "grayscale_histogram": gray_histogram,
        "texture_score": round(float(np.mean(gradient)), 6),
    }


def _normalized_histogram(
    values: np.ndarray,
    *,
    bins: int,
    value_range: tuple[float, float],
) -> list[float]:
    counts, _ = np.histogram(values, bins=bins, range=value_range)
    total = float(np.sum(counts))
    if total == 0.0:
        return [0.0] * bins
    return [round(float(value / total), 8) for value in counts]


def _color_histogram(rgb_array: np.ndarray) -> list[float]:
    channels = [
        _normalized_histogram(rgb_array[:, :, channel], bins=16, value_range=(0.0, 1.0))
        for channel in range(3)
    ]
    return [round(value / 3.0, 8) for channel in channels for value in channel]


def _entropy(histogram: list[float]) -> float:
    probabilities = np.asarray(histogram, dtype=np.float64)
    probabilities = probabilities[probabilities > 0]
    if probabilities.size == 0:
        return 0.0
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _gradient_magnitude(gray: np.ndarray) -> np.ndarray:
    if gray.size == 0:
        return np.zeros_like(gray)
    grad_y, grad_x = np.gradient(gray)
    return np.sqrt((grad_x * grad_x) + (grad_y * grad_y))

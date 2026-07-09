"""Deterministic similarity metrics for visual patch features."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

WEIGHTS = {
    "histogram_similarity": 0.35,
    "brightness_similarity": 0.15,
    "contrast_similarity": 0.15,
    "edge_density_similarity": 0.15,
    "texture_similarity": 0.10,
    "size_similarity": 0.05,
    "aspect_ratio_similarity": 0.05,
}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Clamp a number to an inclusive range."""
    return max(lower, min(upper, value))


def histogram_similarity(
    first_histogram: Sequence[float],
    second_histogram: Sequence[float],
) -> float:
    """Return histogram intersection similarity between 0 and 1."""
    if len(first_histogram) != len(second_histogram) or not first_histogram:
        return 0.0
    return round(clamp(sum(min(a, b) for a, b in zip(first_histogram, second_histogram))), 6)


def scalar_similarity(first_value: float, second_value: float, scale: float = 1.0) -> float:
    """Return 1 minus normalized absolute difference, clamped to 0..1."""
    if scale <= 0:
        scale = 1.0
    return round(clamp(1.0 - (abs(first_value - second_value) / scale)), 6)


def size_similarity(
    first_width: int,
    first_height: int,
    second_width: int,
    second_height: int,
) -> float:
    """Return area similarity between two patch sizes."""
    first_area = max(first_width * first_height, 1)
    second_area = max(second_width * second_height, 1)
    return round(min(first_area, second_area) / max(first_area, second_area), 6)


def compare_features(
    reference_features: Mapping[str, Any],
    candidate_features: Mapping[str, Any],
) -> dict[str, float]:
    """Compare two inspected patches and return interpretable similarity metrics."""
    color_similarity = histogram_similarity(
        reference_features["color_histogram"],
        candidate_features["color_histogram"],
    )
    gray_similarity = histogram_similarity(
        reference_features["grayscale_histogram"],
        candidate_features["grayscale_histogram"],
    )
    metrics = {
        "histogram_similarity": round((color_similarity + gray_similarity) / 2.0, 6),
        "brightness_similarity": scalar_similarity(
            float(reference_features["brightness"]),
            float(candidate_features["brightness"]),
        ),
        "contrast_similarity": scalar_similarity(
            float(reference_features["contrast"]),
            float(candidate_features["contrast"]),
        ),
        "edge_density_similarity": scalar_similarity(
            float(reference_features["edge_density"]),
            float(candidate_features["edge_density"]),
        ),
        "texture_similarity": scalar_similarity(
            float(reference_features["texture_score"]),
            float(candidate_features["texture_score"]),
        ),
        "size_similarity": size_similarity(
            int(reference_features["width"]),
            int(reference_features["height"]),
            int(candidate_features["width"]),
            int(candidate_features["height"]),
        ),
        "aspect_ratio_similarity": scalar_similarity(
            float(reference_features["aspect_ratio"]),
            float(candidate_features["aspect_ratio"]),
            scale=max(float(reference_features["aspect_ratio"]), 1.0),
        ),
    }
    metrics["overall_similarity"] = overall_similarity(metrics)
    return metrics


def overall_similarity(metrics: Mapping[str, float]) -> float:
    """Return weighted overall similarity from component metrics."""
    score = sum(metrics[name] * weight for name, weight in WEIGHTS.items())
    return round(clamp(score), 6)

"""Public orchestration functions for visual patch auditing."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .features import inspect_patch, is_supported_image
from .metrics import compare_features


def compare_patch(
    reference_patch: str | Path,
    candidate_patch: str | Path,
) -> dict[str, Any]:
    """Compare one reference patch with one candidate patch."""
    reference_features = inspect_patch(reference_patch)
    candidate_features = inspect_patch(candidate_patch)
    similarity = compare_features(reference_features, candidate_features)
    issues = _issues_for_comparison(
        str(candidate_features["path"]),
        similarity,
        threshold=0.65,
        reference_features=reference_features,
        candidate_features=candidate_features,
    )
    return {
        "reference": str(reference_features["path"]),
        "candidate": str(candidate_features["path"]),
        "similarity": similarity,
        "overall_similarity": similarity["overall_similarity"],
        "issues": issues,
    }


def compare_patches(
    reference_patches: str | Path | list[str | Path],
    candidate_patches: str | Path | list[str | Path],
    *,
    threshold: float = 0.65,
) -> dict[str, Any]:
    """Compare candidate patches against a reference set using best matches."""
    references, reference_issues = _load_features(reference_patches, role="reference")
    candidates, candidate_issues = _load_features(candidate_patches, role="candidate")
    issues = reference_issues + candidate_issues

    if not references:
        issues.append(_issue(None, "empty_input", "high", "No readable reference patches were found."))
    if not candidates:
        issues.append(_issue(None, "empty_input", "high", "No readable candidate patches were found."))

    candidate_reports: list[dict[str, Any]] = []
    for candidate in candidates:
        comparisons = [
            (reference, compare_features(reference, candidate))
            for reference in references
        ]
        if not comparisons:
            continue
        best_reference, best_similarity = max(
            comparisons,
            key=lambda item: item[1]["overall_similarity"],
        )
        candidate_issues = _issues_for_comparison(
            str(candidate["path"]),
            best_similarity,
            threshold=threshold,
            reference_features=best_reference,
            candidate_features=candidate,
        )
        issues.extend(candidate_issues)
        candidate_reports.append(
            {
                "patch": str(candidate["path"]),
                "best_reference": str(best_reference["path"]),
                "overall_similarity": best_similarity["overall_similarity"],
                "similarity": best_similarity,
                "issues": candidate_issues,
            }
        )

    summary = _summarize_similarity(candidate_reports)
    return {
        "reference_count": len(references),
        "candidate_count": len(candidates),
        "score": _score(summary.get("mean_overall_similarity", 0.0), issues),
        "similarity": summary,
        "candidates": candidate_reports,
        "issues": issues,
    }


def find_outlier_patches(
    patches: str | Path | list[str | Path],
    *,
    threshold: float = 0.65,
) -> list[dict[str, Any]]:
    """Find visually unusual patches by average pairwise similarity."""
    features, _ = _load_features(patches, role="patch")
    if len(features) < 2:
        return []

    outliers: list[dict[str, Any]] = []
    for index, feature in enumerate(features):
        similarities = [
            compare_features(feature, other)["overall_similarity"]
            for other_index, other in enumerate(features)
            if other_index != index
        ]
        average_similarity = round(sum(similarities) / len(similarities), 6)
        if average_similarity < threshold:
            outliers.append(
                {
                    "patch": str(feature["path"]),
                    "average_similarity": average_similarity,
                    "type": "low_similarity",
                    "severity": "medium" if average_similarity >= threshold * 0.75 else "high",
                    "message": "Patch is visually different from the rest of the set.",
                }
            )
    return outliers


def _resolve_image_paths(paths: str | Path | list[str | Path]) -> tuple[list[Path], list[Path]]:
    if isinstance(paths, (str, Path)):
        input_path = Path(paths)
        if input_path.is_dir():
            files = sorted(path for path in input_path.iterdir() if path.is_file())
            return [path for path in files if is_supported_image(path)], [
                path for path in files if not is_supported_image(path)
            ]
        return ([input_path], []) if is_supported_image(input_path) else ([], [input_path])

    supported: list[Path] = []
    unsupported: list[Path] = []
    for item in paths:
        path = Path(item)
        if is_supported_image(path):
            supported.append(path)
        else:
            unsupported.append(path)
    return supported, unsupported


def _load_features(
    paths: str | Path | list[str | Path],
    *,
    role: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    image_paths, unsupported_paths = _resolve_image_paths(paths)
    features: list[dict[str, Any]] = []
    issues = [
        _issue(str(path), "unsupported_image", "low", f"Unsupported {role} file was ignored.")
        for path in unsupported_paths
    ]

    for path in image_paths:
        try:
            features.append(inspect_patch(path))
        except ValueError:
            issues.append(
                _issue(str(path), "corrupt_image", "medium", f"Unreadable {role} image was ignored.")
            )
    return features, issues


def _summarize_similarity(candidate_reports: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    reports = list(candidate_reports)
    if not reports:
        return {
            "mean_histogram_similarity": 0.0,
            "mean_brightness_similarity": 0.0,
            "mean_contrast_similarity": 0.0,
            "mean_edge_density_similarity": 0.0,
            "mean_texture_similarity": 0.0,
            "mean_size_similarity": 0.0,
            "mean_aspect_ratio_similarity": 0.0,
            "mean_overall_similarity": 0.0,
        }

    def mean(metric_name: str) -> float:
        return round(
            sum(float(report["similarity"][metric_name]) for report in reports) / len(reports),
            6,
        )

    return {
        "mean_histogram_similarity": mean("histogram_similarity"),
        "mean_brightness_similarity": mean("brightness_similarity"),
        "mean_contrast_similarity": mean("contrast_similarity"),
        "mean_edge_density_similarity": mean("edge_density_similarity"),
        "mean_texture_similarity": mean("texture_similarity"),
        "mean_size_similarity": mean("size_similarity"),
        "mean_aspect_ratio_similarity": mean("aspect_ratio_similarity"),
        "mean_overall_similarity": mean("overall_similarity"),
    }


def _issues_for_comparison(
    patch: str,
    similarity: Mapping[str, float],
    *,
    threshold: float,
    reference_features: Mapping[str, Any],
    candidate_features: Mapping[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    overall = float(similarity["overall_similarity"])
    if overall < threshold:
        severity = "medium" if overall >= threshold * 0.75 else "high"
        issues.append(
            _issue(
                patch,
                "low_similarity",
                severity,
                "Patch is visually different from the reference set.",
            )
        )

    checks = [
        ("size_similarity", "size_mismatch", "Patch size differs from the reference patch."),
        (
            "aspect_ratio_similarity",
            "aspect_ratio_mismatch",
            "Patch aspect ratio differs from the reference patch.",
        ),
        ("brightness_similarity", "brightness_shift", "Patch brightness differs from the reference patch."),
        ("contrast_similarity", "contrast_shift", "Patch contrast differs from the reference patch."),
        (
            "edge_density_similarity",
            "edge_density_shift",
            "Patch edge density differs from the reference patch.",
        ),
        ("texture_similarity", "texture_shift", "Patch texture score differs from the reference patch."),
    ]
    for metric_name, issue_type, message in checks:
        if float(similarity[metric_name]) < 0.75:
            issues.append(_issue(patch, issue_type, "low", message))

    if (
        int(reference_features["width"]) != int(candidate_features["width"])
        or int(reference_features["height"]) != int(candidate_features["height"])
    ) and not any(issue["type"] == "size_mismatch" for issue in issues):
        issues.append(_issue(patch, "size_mismatch", "low", "Patch size differs from the reference patch."))

    return issues


def _score(mean_similarity: float, issues: Iterable[Mapping[str, Any]]) -> int:
    score = int(round(mean_similarity * 100))
    for issue in issues:
        if issue["severity"] == "medium":
            score -= 5
        elif issue["severity"] == "high":
            score -= 15
    return max(0, min(100, score))


def _issue(
    patch: str | None,
    issue_type: str,
    severity: str,
    message: str,
) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "type": issue_type,
        "severity": severity,
        "message": message,
    }
    if patch is not None:
        issue["patch"] = patch
    return issue

from pathlib import Path

import pytest
from PIL import Image

from visual_patch_audit import compare_patch, compare_patches, find_outlier_patches, inspect_patch


def make_image(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (32, 32)) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def test_compare_identical_patches_gives_high_similarity(tmp_path: Path) -> None:
    patch = make_image(tmp_path / "patch.png", (80, 120, 160))

    result = compare_patch(patch, patch)

    assert result["overall_similarity"] > 0.99
    assert result["issues"] == []


def test_compare_different_patches_gives_lower_similarity(tmp_path: Path) -> None:
    reference = make_image(tmp_path / "reference.png", (0, 0, 0))
    candidate = make_image(tmp_path / "candidate.png", (255, 255, 255))

    result = compare_patch(reference, candidate)

    assert result["overall_similarity"] < 0.8
    assert "similarity" in result
    assert result["issues"]


def test_compare_patch_returns_similarity_and_issues(tmp_path: Path) -> None:
    reference = make_image(tmp_path / "reference.png", (80, 80, 80))
    candidate = make_image(tmp_path / "candidate.png", (90, 90, 90))

    result = compare_patch(reference, candidate)

    assert "similarity" in result
    assert "issues" in result
    assert "overall_similarity" in result


def test_compare_patches_works_with_folders(tmp_path: Path) -> None:
    references = tmp_path / "references"
    candidates = tmp_path / "candidates"
    references.mkdir()
    candidates.mkdir()
    make_image(references / "ref.png", (50, 50, 50))
    make_image(candidates / "candidate.png", (52, 52, 52))

    report = compare_patches(references, candidates)

    assert report["reference_count"] == 1
    assert report["candidate_count"] == 1
    assert {"score", "similarity", "issues"} <= set(report)


def test_compare_patches_works_with_lists(tmp_path: Path) -> None:
    reference = make_image(tmp_path / "ref.png", (10, 20, 30))
    candidate = make_image(tmp_path / "candidate.png", (12, 20, 28))

    report = compare_patches([reference], [candidate])

    assert report["reference_count"] == 1
    assert report["candidate_count"] == 1
    assert report["candidates"][0]["best_reference"] == str(reference)


def test_unsupported_files_are_ignored_in_batch_mode(tmp_path: Path) -> None:
    reference = make_image(tmp_path / "ref.png", (10, 10, 10))
    candidate = make_image(tmp_path / "candidate.png", (10, 10, 10))
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("not an image", encoding="utf-8")

    report = compare_patches([reference, unsupported], [candidate])

    assert report["reference_count"] == 1
    assert any(issue["type"] == "unsupported_image" for issue in report["issues"])


def test_corrupt_images_are_handled_in_batch_mode(tmp_path: Path) -> None:
    reference = make_image(tmp_path / "ref.png", (10, 10, 10))
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_text("not image bytes", encoding="utf-8")

    report = compare_patches([reference], [corrupt])

    assert report["candidate_count"] == 0
    assert any(issue["type"] == "corrupt_image" for issue in report["issues"])


def test_invalid_single_image_raises_value_error(tmp_path: Path) -> None:
    reference = make_image(tmp_path / "ref.png", (10, 10, 10))
    invalid = tmp_path / "invalid.txt"
    invalid.write_text("not supported", encoding="utf-8")

    with pytest.raises(ValueError):
        compare_patch(reference, invalid)


def test_find_outlier_patches_detects_different_patch(tmp_path: Path) -> None:
    make_image(tmp_path / "a.png", (100, 100, 100))
    make_image(tmp_path / "b.png", (102, 102, 102))
    make_image(tmp_path / "c.png", (98, 98, 98))
    outlier = make_image(tmp_path / "outlier.png", (255, 255, 255))

    outliers = find_outlier_patches(tmp_path, threshold=0.92)

    assert any(item["patch"] == str(outlier) for item in outliers)


def test_inspect_patch_is_imported_from_public_api(tmp_path: Path) -> None:
    image_path = make_image(tmp_path / "patch.bmp", (1, 2, 3))

    assert inspect_patch(image_path)["width"] == 32

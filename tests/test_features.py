from pathlib import Path

from PIL import Image

from visual_patch_audit import inspect_patch


def make_image(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (32, 32)) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def test_inspect_patch_returns_expected_keys(tmp_path: Path) -> None:
    image_path = make_image(tmp_path / "patch.png", (120, 80, 40))

    features = inspect_patch(image_path)

    expected = {
        "path",
        "width",
        "height",
        "mode",
        "brightness",
        "contrast",
        "edge_density",
        "entropy",
        "sharpness",
        "aspect_ratio",
        "color_histogram",
        "grayscale_histogram",
        "texture_score",
    }
    assert expected <= set(features)


def test_scalar_features_are_normalized(tmp_path: Path) -> None:
    image_path = make_image(tmp_path / "patch.jpg", (255, 255, 255))

    features = inspect_patch(image_path)

    assert 0 <= features["brightness"] <= 1
    assert 0 <= features["contrast"] <= 1
    assert 0 <= features["edge_density"] <= 1
    assert 0 <= features["texture_score"] <= 1


def test_histograms_are_normalized(tmp_path: Path) -> None:
    image_path = make_image(tmp_path / "patch.webp", (10, 100, 200))

    features = inspect_patch(image_path)

    assert abs(sum(features["grayscale_histogram"]) - 1.0) < 1e-6
    assert abs(sum(features["color_histogram"]) - 1.0) < 1e-6

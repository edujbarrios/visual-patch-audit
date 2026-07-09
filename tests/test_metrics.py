from visual_patch_audit.metrics import histogram_similarity, scalar_similarity, size_similarity


def test_histogram_similarity_uses_intersection() -> None:
    assert histogram_similarity([0.5, 0.5], [0.5, 0.5]) == 1.0
    assert histogram_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_scalar_similarity_is_clamped() -> None:
    assert scalar_similarity(0.5, 0.5) == 1.0
    assert scalar_similarity(0.0, 2.0) == 0.0


def test_size_similarity_compares_area() -> None:
    assert size_similarity(10, 10, 10, 10) == 1.0
    assert size_similarity(10, 10, 20, 20) == 0.25

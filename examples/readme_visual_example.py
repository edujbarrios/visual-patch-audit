"""Generate the visual README landscape example assets.

Run from the repository root:

    python examples/readme_visual_example.py
"""

from __future__ import annotations

from pathlib import Path
from pprint import pprint

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from visual_patch_audit import compare_patch

ASSET_DIR = Path("assets/readme")
PATCH_BOX = (128, 82, 304, 218)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    reference_image = _make_landscape(seed=4, season="summer")
    candidate_image = _make_landscape(seed=4, season="autumn")

    reference_patch = reference_image.crop(PATCH_BOX)
    candidate_patch = candidate_image.crop(PATCH_BOX)

    _draw_selection(reference_image, PATCH_BOX, "reference patch")
    _draw_selection(candidate_image, PATCH_BOX, "candidate patch")

    reference_image.save(ASSET_DIR / "reference_image.png")
    candidate_image.save(ASSET_DIR / "candidate_image.png")
    reference_patch.save(ASSET_DIR / "reference_patch.png")
    candidate_patch.save(ASSET_DIR / "candidate_patch.png")
    _make_comparison_panel(reference_image, reference_patch, candidate_image, candidate_patch)

    report = compare_patch(
        ASSET_DIR / "reference_patch.png",
        ASSET_DIR / "candidate_patch.png",
    )
    pprint(report)


def _make_landscape(*, seed: int, season: str) -> Image.Image:
    random.seed(seed)
    width, height = 432, 300
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    for y in range(height):
        t = y / height
        sky = _mix((113, 173, 220), (232, 238, 216), min(t * 1.5, 1.0))
        draw.line((0, y, width, y), fill=sky)

    draw.ellipse((42, 32, 104, 94), fill=(247, 219, 118))
    draw.ellipse((44, 34, 102, 92), outline=(255, 236, 156), width=3)

    far_mountains = [(0, 176), (74, 90), (142, 160), (216, 74), (308, 168), (376, 100), (432, 166), (432, 300), (0, 300)]
    near_mountains = [(0, 206), (92, 122), (170, 204), (260, 112), (344, 206), (432, 138), (432, 300), (0, 300)]
    draw.polygon(far_mountains, fill=(100, 124, 143))
    draw.polygon(near_mountains, fill=(79, 105, 119))

    draw.polygon([(74, 90), (110, 132), (46, 132)], fill=(232, 232, 220))
    draw.polygon([(216, 74), (252, 126), (186, 126)], fill=(234, 236, 226))
    draw.polygon([(376, 100), (406, 140), (346, 140)], fill=(228, 229, 218))

    lake_top = 184
    for y in range(lake_top, height):
        t = (y - lake_top) / (height - lake_top)
        color = _mix((65, 128, 160), (34, 76, 106), t)
        draw.line((0, y, width, y), fill=color)

    forest_color = (50, 111, 72) if season == "summer" else (129, 105, 50)
    forest_shadow = (34, 79, 53) if season == "summer" else (91, 74, 42)
    for x in range(-12, width + 18, 14):
        height_offset = 28 + int(10 * math.sin(x / 19))
        base_y = 202 + int(5 * math.sin(x / 13))
        draw.polygon(
            [(x, base_y), (x + 9, base_y - height_offset), (x + 20, base_y)],
            fill=forest_shadow,
        )
        draw.polygon(
            [(x + 3, base_y - 4), (x + 10, base_y - height_offset - 4), (x + 18, base_y - 4)],
            fill=forest_color,
        )

    meadow = (88, 143, 72) if season == "summer" else (167, 128, 58)
    draw.polygon([(0, 230), (116, 212), (246, 228), (432, 208), (432, 300), (0, 300)], fill=meadow)

    for index in range(110):
        x = random.randint(0, width - 1)
        y = random.randint(222, height - 1)
        if season == "summer":
            color = random.choice([(57, 119, 64), (76, 139, 70), (104, 151, 78)])
        else:
            color = random.choice([(138, 94, 44), (178, 124, 51), (108, 89, 50)])
        draw.line((x, y, x + random.randint(2, 5), y - random.randint(1, 4)), fill=color)

    image = image.filter(ImageFilter.SMOOTH_MORE)
    _add_subtle_texture(image, seed=seed + (20 if season == "autumn" else 0))
    return image


def _mix(first: tuple[int, int, int], second: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(int(a + (b - a) * amount) for a, b in zip(first, second))


def _add_subtle_texture(image: Image.Image, *, seed: int) -> None:
    random.seed(seed)
    pixels = image.load()
    width, height = image.size
    for _ in range(2600):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        r, g, b = pixels[x, y]
        delta = random.randint(-7, 7)
        pixels[x, y] = (
            max(0, min(255, r + delta)),
            max(0, min(255, g + delta)),
            max(0, min(255, b + delta)),
        )


def _draw_selection(image: Image.Image, box: tuple[int, int, int, int], label: str) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle(box, outline=(226, 58, 58), width=4)
    draw.rectangle((box[0], box[1] - 22, box[0] + 132, box[1] - 2), fill=(226, 58, 58))
    draw.text((box[0] + 6, box[1] - 20), label, fill=(255, 255, 255))


def _make_comparison_panel(
    reference_image: Image.Image,
    reference_patch: Image.Image,
    candidate_image: Image.Image,
    candidate_patch: Image.Image,
) -> None:
    panel = Image.new("RGB", (920, 420), (250, 250, 248))
    draw = ImageDraw.Draw(panel)
    panel.paste(reference_image, (24, 52))
    panel.paste(candidate_image, (464, 52))
    panel.paste(reference_patch.resize((160, 160)), (156, 238))
    panel.paste(candidate_patch.resize((160, 160)), (596, 238))

    draw.text((24, 24), "Reference landscape and selected patch", fill=(30, 35, 34))
    draw.text((464, 24), "Candidate landscape and selected patch", fill=(30, 35, 34))
    draw.text((156, 398), "reference_patch.png", fill=(30, 35, 34))
    draw.text((596, 398), "candidate_patch.png", fill=(30, 35, 34))
    draw.line((432, 52, 432, 398), fill=(210, 210, 205), width=2)
    panel.save(ASSET_DIR / "visual_patch_comparison.png")


if __name__ == "__main__":
    main()

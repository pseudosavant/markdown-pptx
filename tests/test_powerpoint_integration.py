from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PIL import Image

from markdown_slides.parser import parse_deck
from markdown_slides.powerpoint_export import export_powerpoint_images
from markdown_slides.renderer import render_pptx

pytestmark = [
    pytest.mark.powerpoint,
    pytest.mark.skipif(
        sys.platform != "win32" or os.environ.get("MARKDOWN_PPTX_TEST_POWERPOINT") != "1",
        reason="requires Windows desktop PowerPoint and MARKDOWN_PPTX_TEST_POWERPOINT=1",
    ),
]


@pytest.mark.parametrize(("image_format", "expected_format"), [("png", "PNG"), ("jpeg", "JPEG")])
def test_real_powerpoint_exports_selected_slides(tmp_path: Path, image_format: str, expected_format: str) -> None:
    deck = parse_deck(
        """# First slide

First body.

# Second slide

Second body.
""",
        input_path=tmp_path / "deck.md",
        source_name="deck.md",
    )
    pptx = tmp_path / "deck.pptx"
    render_pptx(deck, output_path=pptx, template_path=None, force=False, base_dir=tmp_path)

    result = export_powerpoint_images(
        pptx,
        output_dir=tmp_path / f"{image_format}-images",
        image_format=image_format,
        slide_numbers=[2],
        slide_count=2,
        width=640,
    )

    assert result["width"] == 640
    assert result["height"] == 360
    assert [item["slide"] for item in result["slides"]] == [2]
    image_path = Path(result["slides"][0]["path"])
    with Image.open(image_path) as image:
        assert image.format == expected_format
        assert image.size == (640, 360)

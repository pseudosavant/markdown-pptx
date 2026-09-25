"""Rendering behavior that depends on the fork's public API boundary."""

from pathlib import Path

from pptx import Presentation
from pptx.enum.dml import MSO_THEME_COLOR

from markdown_slides.assets import default_template_path
from markdown_slides.parser import parse_deck
from markdown_slides.renderer import render_pptx


def test_explicit_theme_background_replaces_template_brightness(tmp_path: Path) -> None:
    presentation = Presentation(default_template_path())
    fill = presentation.slide_master.background.fill
    fill.solid()
    fill.fore_color.theme_color = MSO_THEME_COLOR.ACCENT_1
    fill.fore_color.brightness = 0.5
    template = tmp_path / "template.pptx"
    presentation.save(template)
    deck = parse_deck(
        '---\nbackground: "var(--accent-2)"\n---\n# Title\n\nBody\n',
        input_path=tmp_path / "deck.md",
        source_name="deck.md",
    )
    output = tmp_path / "deck.pptx"
    render_pptx(deck, output_path=output, template_path=template, force=False, base_dir=tmp_path)
    color = Presentation(output).slide_master.background.fill.fore_color
    assert color.theme_color == MSO_THEME_COLOR.ACCENT_2
    assert color.brightness == 0

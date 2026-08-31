from __future__ import annotations

from pathlib import Path

import pytest

from markdown_slides.errors import ParseError, UnsupportedContentError
from markdown_slides.parser import parse_deck


def test_parse_document_and_slide_front_matter() -> None:
    deck = parse_deck(
        """---
aspect_ratio: "4:3"
fonts:
  body: Aptos
  headings: Aptos Display
title_color: "var(--light-1)"
body_color: "rgb(68, 85, 102)"
color_scheme:
  preset: Office
background: "var(--accent-1)"
---

# Intro
---
layout: Title Slide
title_color: "var(--accent-2)"
notes: |
  Speaker notes.
---

Subtitle text
""",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.aspect_ratio == "4:3"
    assert deck.fonts.body == "Aptos"
    assert deck.text_colors is not None
    assert deck.text_colors.title == "var(--light-1)"
    assert deck.text_colors.body == "#445566"
    assert deck.background is not None
    assert deck.background.value == "var(--accent-1)"
    assert deck.fonts_override is True
    assert deck.color_scheme.name == "Office"
    assert deck.slides[0].layout == "Title Slide"
    assert deck.slides[0].master is None
    assert deck.slides[0].text_colors is not None
    assert deck.slides[0].text_colors.title == "var(--accent-2)"
    assert deck.slides[0].text_colors.body is None
    assert deck.slides[0].notes == "Speaker notes."


def test_parse_defaults_do_not_force_theme_overrides() -> None:
    deck = parse_deck(
        "# Slide\n\nBody\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.fonts.body == "Aptos"
    assert deck.fonts.headings == "Aptos Display"
    assert deck.fonts_override is False
    assert deck.color_scheme is None


def test_color_scheme_preset_accepts_partial_bespoke_overrides() -> None:
    deck = parse_deck(
        """---
color_scheme:
  preset: Office
  accent_1: "#123456"
---

# Slide

Body
""",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.color_scheme is not None
    assert deck.color_scheme.name == "Office"
    assert deck.color_scheme.colors["accent_1"] == "#123456"
    assert len(deck.color_scheme.colors) == 12


def test_dashed_text_color_keys_are_rejected() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            """---
title_color: "#112233"
title-color: "#445566"
---

# Slide

Body
""",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "unknown_front_matter_keys"


def test_slide_front_matter_must_be_immediately_after_h1() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            "# Slide\n\n---\nlayout: Title Only\n---\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "setext_headings_unsupported"


def test_setext_headings_are_rejected() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            "# Slide\n\nSubtitle\n--------\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "setext_headings_unsupported"


def test_blank_slide_defaults_when_empty_title_and_body() -> None:
    deck = parse_deck(
        "# \n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.slides[0].layout == "Blank"


def test_empty_title_with_body_defaults_to_title_and_content() -> None:
    deck = parse_deck(
        "# \n\nBody\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.slides[0].layout == "Title and Content"


def test_title_only_rejects_body() -> None:
    with pytest.raises(UnsupportedContentError):
        parse_deck(
            "# Slide\n---\nlayout: Title Only\n---\n\nBody\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )


def test_title_and_content_rejects_mixed_text_and_image() -> None:
    with pytest.raises(UnsupportedContentError):
        parse_deck(
            "# Slide\n\nParagraph.\n\n![alt](./image.png)\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )


def test_h1_inside_fence_does_not_start_slide() -> None:
    deck = parse_deck(
        "# Slide\n\n```python\n# not a slide\n```\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert len(deck.slides) == 1
    assert deck.slides[0].body.paragraphs[0].kind == "code"


def test_h1_inside_tilde_fence_does_not_start_slide() -> None:
    deck = parse_deck(
        "# Slide\n\n~~~markdown\n# not a slide\n~~~\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert len(deck.slides) == 1
    assert deck.slides[0].body.paragraphs[0].kind == "code"


def test_shorter_backtick_run_does_not_close_longer_fence() -> None:
    deck = parse_deck(
        "# First\n\n````markdown\n# not a slide\n```\n# still not a slide\n````\n\n# Second\n\nBody\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert len(deck.slides) == 2
    assert deck.slides[1].title == "Second"


@pytest.mark.parametrize(
    "body",
    [
        "Text with <span>raw HTML</span>.",
        "- [ ] unfinished task",
        "A footnote reference[^1].\n\n[^1]: Footnote text.",
    ],
)
def test_unrepresentable_markdown_is_rejected(body: str) -> None:
    with pytest.raises(UnsupportedContentError) as excinfo:
        parse_deck(
            f"# Slide\n\n{body}\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "unsupported_content"


def test_footnote_syntax_inside_inline_code_is_allowed() -> None:
    deck = parse_deck(
        "# Slide\n\n`[^1]` is literal code.\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.slides[0].body.paragraphs[0].fragments[0].kind == "code"


def test_hide_background_graphics_requires_a_boolean() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            '# Slide\n---\nhide_background_graphics: "false"\n---\n\nBody\n',
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_hide_background_graphics"


@pytest.mark.parametrize("selector", ["2", "Executive Theme"])
def test_parse_slide_master_selector(selector: str) -> None:
    deck = parse_deck(
        f"# Slide\n---\nmaster: {selector!r}\n---\n\nBody\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.slides[0].master == selector


@pytest.mark.parametrize("selector", ["0", "-1", "true", "1.5", "''"])
def test_slide_master_selector_rejects_invalid_values(selector: str) -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            f"# Slide\n---\nmaster: {selector}\n---\n\nBody\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_master_selector"


def test_table_options_default_to_existing_powerpoint_style_flags() -> None:
    deck = parse_deck(
        "# Table\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    options = deck.slides[0].table_options
    assert options.header_row is True
    assert options.total_row is False
    assert options.first_column is False
    assert options.last_column is False
    assert options.banded_rows is True
    assert options.banded_columns is False


def test_parse_slide_table_options() -> None:
    deck = parse_deck(
        """# Table
---
table:
  header_row: false
  total_row: true
  first_column: true
  last_column: true
  banded_rows: false
  banded_columns: true
---

| A | B |
| --- | --- |
| 1 | 2 |
""",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    options = deck.slides[0].table_options
    assert options.header_row is False
    assert options.total_row is True
    assert options.first_column is True
    assert options.last_column is True
    assert options.banded_rows is False
    assert options.banded_columns is True


@pytest.mark.parametrize("value", ["null", "true", "[]", "'header_row'"])
def test_table_options_require_a_mapping(value: str) -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            f"# Table\n---\ntable: {value}\n---\n\n| A |\n| --- |\n| 1 |\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_table_options"


def test_table_options_reject_unknown_keys() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            "# Table\n---\ntable:\n  header_column: true\n---\n\n| A |\n| --- |\n| 1 |\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "unknown_table_option_keys"


def test_table_options_require_boolean_values() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            '# Table\n---\ntable:\n  header_row: "true"\n---\n\n| A |\n| --- |\n| 1 |\n',
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_table_options"


def test_table_options_require_string_keys() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            "# Table\n---\ntable:\n  true: false\n---\n\n| A |\n| --- |\n| 1 |\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_table_options"


def test_table_options_require_exactly_one_table_body() -> None:
    with pytest.raises(UnsupportedContentError) as excinfo:
        parse_deck(
            "# Not a table\n---\ntable:\n  banded_rows: false\n---\n\nParagraph.\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "unsupported_content"

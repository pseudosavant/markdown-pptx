from pathlib import Path

import pytest

from markdown_slides.errors import ParseError
from markdown_slides.parser import parse_deck


def test_effects_merge_per_property_at_all_scopes_and_keep_categories_separate() -> None:
    deck = parse_deck(
        "<!-- markdown-pptx:deck\nlayout: Two Content\nmedia_effects:\n  border_radius: 8pt\n"
        '  shadow: "1pt 1pt 3pt"\n  reflection: 4pt 30%\ntable_effects:\n  shadow: "3pt 3pt 4pt"\n-->\n'
        "# Scoped\n<!-- markdown-pptx:slide\nmedia_effects:\n  border_radius: 12pt\n"
        "table_effects:\n  reflection: 2pt 20%\n-->\n\n![Image](photo.png)\n\n"
        "<!-- markdown-pptx:media_effects\nshadow: none\n-->\n\n***\n\n| A |\n| --- |\n| B |\n\n"
        '<!-- markdown-pptx:table_effects\nreflection: none\nborder: "2pt solid var(--accent-2)"\n-->\n'
        "# Inherited\n\n[Play](demo.mp4)\n\n***\n\n| A |\n| --- |\n| B |\n",
        input_path=None,
        source_name="scoped.md",
    )
    image = deck.slides[0].body.images[0].effects
    assert image.border_radius_pt == 12
    assert image.shadow is None
    assert image.reflection.amount == 0.3
    table = deck.slides[0].secondary_body.tables[0].effects
    assert table.border_radius_pt == 0
    assert table.shadow.offset_x_pt == 3
    assert table.reflection is None
    assert table.border.width_pt == 2
    video = deck.slides[1].body.videos[0].effects
    assert video.border_radius_pt == 8
    assert video.shadow.offset_x_pt == 1
    assert video.reflection.amount == 0.3
    inherited_table = deck.slides[1].secondary_body.tables[0].effects
    assert inherited_table.shadow.offset_x_pt == 3
    assert inherited_table.border is inherited_table.reflection is None


@pytest.mark.parametrize("scope", ["deck", "slide", "element"])
def test_tables_reject_border_radius_at_every_scope(scope) -> None:
    settings = "table_effects:\n  border_radius: 0"
    table = "| A |\n| --- |\n| B |\n"
    if scope == "deck":
        source = f"<!-- markdown-pptx:deck\n{settings}\n-->\n\n# Table\n\n{table}"
    elif scope == "slide":
        source = f"# Table\n<!-- markdown-pptx:slide\n{settings}\n-->\n\n{table}"
    else:
        source = f"# Table\n\n{table}\n<!-- markdown-pptx:table_effects\nborder_radius: 0\n-->\n"
    with pytest.raises(ParseError, match="only supported in media_effects") as excinfo:
        parse_deck(source, input_path=None, source_name="table.md")
    assert excinfo.value.context.code == "invalid_effect_settings"
    assert excinfo.value.context.input_path == "table.md"
    assert excinfo.value.context.line is not None


@pytest.mark.parametrize("gap", ["\n", "\n\n"])
@pytest.mark.parametrize("effects_first", [False, True])
@pytest.mark.parametrize(
    "link",
    ["[Play](demo.mp4)", "[![Poster](poster.png)](demo.mp4)", "[Watch](https://www.youtube.com/watch?v=aqz-KE-bpKQ)"],
)
def test_video_effects_and_playback_comments_can_follow_in_either_order(gap, effects_first, link) -> None:
    playback = "<!-- markdown-pptx:video\nwidth: 75%\n-->"
    effects = "<!-- markdown-pptx:media_effects\nborder_radius: 8pt\n-->"
    comments = gap.join([effects, playback] if effects_first else [playback, effects])
    deck = parse_deck(f"# Video\n\n{link}\n\n{comments}\n", input_path=None, source_name="video.md")
    video = deck.slides[0].body.videos[0]
    assert video.width == "75%"
    assert video.effects.border_radius_pt == 8


@pytest.mark.parametrize(
    "body",
    [
        "![Image](photo.png)\n\n<!-- markdown-pptx:table_effects\nshadow: none\n-->",
        "| A |\n| --- |\n| B |\n\n<!-- markdown-pptx:media_effects\nshadow: none\n-->",
        "[Play](demo.mp4)\n\n<!-- markdown-pptx:table_effects\nshadow: none\n-->",
        "<!-- markdown-pptx:table_effects\nshadow: none\n-->\n\n| A |\n| --- |\n| B |",
        "Text\n\n<!-- markdown-pptx:table_effects\nshadow: none\n-->",
        "| A |\n| --- |\n| <!-- markdown-pptx:table_effects shadow: none --> |",
        "[Play](demo.mp4)\n\n<!-- markdown-pptx:media_effects\nshadow: none\n-->\n"
        "<!-- markdown-pptx:media_effects\nreflection: none\n-->",
        "![Image](photo.png)\n\n<!-- markdown-pptx:image\nshadow: none\n-->",
        "![Image](photo.png)\n\n<!-- markdown-pptx:effects\nshadow: none\n-->",
    ],
)
def test_effect_comments_reject_wrong_targets_orphans_duplicates_and_removed_syntax(body) -> None:
    with pytest.raises(ParseError):
        parse_deck(f"# Slide\n\n{body}\n", input_path=None, source_name="deck.md")


@pytest.mark.parametrize("category", ["media_effects", "table_effects"])
@pytest.mark.parametrize("value", ["null", "none", "[]", "true", "{unknown: 1pt}", "{shadow: true}"])
@pytest.mark.parametrize("scope", ["deck", "slide"])
def test_invalid_effect_defaults_fail_at_deck_and_slide_levels(category, value, scope) -> None:
    setting = f"{category}: {value}"
    source = (
        f"<!-- markdown-pptx:deck\n{setting}\n-->\n\n# Slide\n\nText\n"
        if scope == "deck"
        else (f"# Slide\n<!-- markdown-pptx:slide\n{setting}\n-->\n\nText\n")
    )
    with pytest.raises(ParseError) as excinfo:
        parse_deck(source, input_path=None, source_name="deck.md")
    assert excinfo.value.context.code == "invalid_effect_settings"


@pytest.mark.parametrize("scope", ["deck", "slide"])
def test_effect_defaults_reject_unquoted_hex_and_duplicate_properties(scope) -> None:
    for settings in ["media_effects:\n  shadow: 1pt 1pt #123456", "media_effects:\n  shadow: none\n  shadow: none"]:
        metadata = f"<!-- markdown-pptx:{scope}\n{settings}\n-->"
        source = f"{metadata}\n\n# Slide\n\nText" if scope == "deck" else f"# Slide\n{metadata}\n\nText"
        with pytest.raises(ParseError):
            parse_deck(source, input_path=None, source_name="deck.md")


def test_table_color_scopes_and_flag_inheritance_keep_existing_defaults() -> None:
    deck = parse_deck(
        '<!-- markdown-pptx:deck\ntable:\n  header_fill: "#123"\n  row_fill: var(--light-1)\n'
        "  banded_row_fill: rgb(1, 2, 3)\n-->\n\n# Default\n\n| A |\n| --- |\n| Total |\n"
        '# Override\n<!-- markdown-pptx:slide\ntable:\n  banded_row_fill: "#ABCDEF"\n'
        "  total_row: true\n-->\n\n| A |\n| --- |\n| Total |\n",
        input_path=None,
        source_name="table.md",
    )
    assert deck.table_options.header_fill == "#112233"
    assert deck.table_options.row_fill == "var(--light-1)"
    assert deck.table_options.banded_row_fill == "#010203"
    assert deck.slides[0].table_options.header_fill is None
    assert deck.slides[0].table_options.header_row
    assert deck.slides[0].table_options.banded_rows
    assert not deck.slides[0].table_options.total_row
    assert deck.slides[1].table_options.total_row
    assert deck.slides[1].table_options.banded_row_fill == "#ABCDEF"


@pytest.mark.parametrize("scope", ["deck", "slide"])
@pytest.mark.parametrize("key", ["header_fill", "row_fill", "banded_row_fill"])
@pytest.mark.parametrize("value", ["null", "true", "5", "[]", "not-a-color", "#123456"])
def test_invalid_table_colors_fail_at_both_scopes(scope, key, value) -> None:
    metadata = f"<!-- markdown-pptx:{scope}\ntable:\n  {key}: {value}\n-->"
    table = "| A |\n| --- |\n| B |"
    source = f"{metadata}\n\n# Table\n\n{table}" if scope == "deck" else f"# Table\n{metadata}\n\n{table}"
    with pytest.raises(ParseError):
        parse_deck(source, input_path=Path("table.md"), source_name="table.md")

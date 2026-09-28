from __future__ import annotations

from pathlib import Path

import pytest

from markdown_slides.errors import ParseError, UnsupportedContentError
from markdown_slides.parser import parse_deck


def test_video_links_parse_local_and_youtube_settings() -> None:
    deck = parse_deck(
        "# Local\n\n[![Play demo](media/poster.png)](media/demo.mp4)\n\n"
        "<!-- markdown-pptx:video\nwidth: 6in\naspect_ratio: '4:3'\n"
        "align: right\nvalign: bottom\nstart: automatic\n"
        "fullscreen: true\nloop: true\nmute: true\n-->\n\n"
        "# Online\n\n[Watch video](https://youtu.be/aqz-KE-bpKQ)\n\n"
        "<!-- markdown-pptx:video\nwidth: 80%\n-->\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )
    local = deck.slides[0].body.videos[0]
    online = deck.slides[1].body.videos[0]
    assert (local.kind, local.width, local.aspect_ratio, local.align, local.valign) == (
        "local_mp4",
        "6in",
        4 / 3,
        "right",
        "bottom",
    )
    assert (local.poster, local.start, local.fullscreen, local.loop, local.mute) == (
        "media/poster.png",
        "automatic",
        True,
        True,
        True,
    )
    assert online.source == "https://www.youtube.com/embed/aqz-KE-bpKQ"
    assert online.width == "80%"
    assert online.aspect_ratio is None


@pytest.mark.parametrize(
    "settings",
    [
        "unknown: true",
        "source: other.mp4",
        "poster: still.png",
        "start: after-video",
        "mute: yes",
        "aspect_ratio: '0:9'",
        "width: 0%",
        "loop: true\nloop: false",
    ],
)
def test_video_comment_rejects_invalid_settings(settings: str) -> None:
    with pytest.raises(ParseError):
        parse_deck(
            f"# Slide\n\n[Play demo](demo.mp4)\n\n<!-- markdown-pptx:video\n{settings}\n-->\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )


def test_two_content_accepts_text_beside_video() -> None:
    deck = parse_deck(
        "# Slide\n<!-- markdown-pptx:slide\nlayout: Two Content\n-->\n\nText\n\n***\n\n[Play demo](demo.mp4)\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )
    assert deck.slides[0].body.paragraphs
    assert deck.slides[0].secondary_body.videos[0].source == "demo.mp4"


def test_video_source_accepts_host_absolute_path(tmp_path: Path) -> None:
    source = tmp_path / "demo.mp4"
    deck = parse_deck(
        f"# Slide\n\n[Play demo](<{source.as_posix()}>)\n", input_path=tmp_path / "deck.md", source_name="deck.md"
    )
    assert deck.slides[0].body.videos[0].kind == "local_mp4"


def test_video_link_decodes_local_paths_with_spaces() -> None:
    deck = parse_deck(
        "# Slide\n\n[![Play](<poster image.png>)](<demo clip.mp4>)\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )
    video = deck.slides[0].body.videos[0]
    assert (video.source, video.poster) == ("demo clip.mp4", "poster image.png")


def test_video_cannot_mix_with_text_and_inline_links_stay_links() -> None:
    with pytest.raises(UnsupportedContentError):
        parse_deck("# Slide\n\nText\n\n[Play demo](demo.mp4)\n", input_path=Path("deck.md"), source_name="deck.md")
    deck = parse_deck(
        "# Slide\n\nSee [the demo](demo.mp4) for details.\n", input_path=Path("deck.md"), source_name="deck.md"
    )
    assert not deck.slides[0].body.videos
    assert deck.slides[0].body.paragraphs


def test_legacy_video_fence_is_rejected() -> None:
    with pytest.raises(ParseError):
        parse_deck("# Slide\n\n```video\nsource: demo.mp4\n```\n", input_path=Path("deck.md"), source_name="deck.md")


def test_video_link_defaults_and_youtube_linked_image_behavior() -> None:
    deck = parse_deck(
        "# MP4\n\n[Play demo](https://example.com/demo.mp4?download=1)\n\n"
        "# YouTube\n\n[Play online](https://www.youtube.com/watch?v=aqz-KE-bpKQ)\n\n"
        "# YouTube thumbnail\n\n[![Open YouTube](thumb.png)](https://youtu.be/aqz-KE-bpKQ)\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )
    mp4 = deck.slides[0].body.videos[0]
    assert (mp4.kind, mp4.poster, mp4.start) == ("remote_mp4", None, "click")
    assert deck.slides[1].body.videos[0].kind == "youtube"
    assert not deck.slides[2].body.videos
    assert deck.slides[2].body.images[0].href == "https://youtu.be/aqz-KE-bpKQ"


@pytest.mark.parametrize(
    "source",
    [
        "# Slide\n\n<!-- markdown-pptx:video\nwidth: 75%\n-->\n",
        "# Slide\n\n[Play](demo.mp4)\n\nText\n\n<!-- markdown-pptx:video\nwidth: 75%\n-->\n",
        "# Slide\n\n[Play](https://youtu.be/aqz-KE-bpKQ)\n\n<!-- markdown-pptx:video\nstart: click\n-->\n",
        "# Slide\n\n[![Play](https://example.com/poster.png)](demo.mp4)\n",
        "# Slide\n\n[![Watch](thumb.png)](https://youtu.be/aqz-KE-bpKQ)\n\n<!-- markdown-pptx:video\nwidth: 75%\n-->\n",
        "# Slide\n\n[Play](demo.mp4)\n\n<!-- markdown-pptx:video\nwidth: 75% -->\n",
    ],
)
def test_invalid_video_comment_and_poster_placement(source: str) -> None:
    with pytest.raises(ParseError):
        parse_deck(source, input_path=Path("deck.md"), source_name="deck.md")


def test_parse_deck_and_slide_metadata_comments() -> None:
    deck = parse_deck(
        """<!-- markdown-pptx:deck
aspect_ratio: "4:3"
fonts:
  body: Aptos
  headings: Aptos Display
title_color: "var(--light-1)"
body_color: "rgb(68, 85, 102)"
color_scheme:
  preset: Office
background: "var(--accent-1)"
-->

# Intro
<!-- markdown-pptx:slide
layout: Title Slide
title_color: "var(--accent-2)"
notes: |
  Speaker notes.
-->

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
        """<!-- markdown-pptx:deck
color_scheme:
  preset: Office
  accent_1: "#123456"
-->

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
            """<!-- markdown-pptx:deck
title_color: "#112233"
title-color: "#445566"
-->

# Slide

Body
""",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "unknown_metadata_keys"


def test_slide_metadata_must_be_immediately_after_h1() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            "# Slide\n\n<!-- markdown-pptx:slide\nlayout: Title Only\n-->\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "metadata_comment_placement"


def test_metadata_comments_are_hidden_and_preserve_theme_references() -> None:
    from markdown_slides.markdown_body import MD

    source = (
        '<!-- markdown-pptx:deck\ntitle_color: "var(--accent-1)"\n-->\n\n'
        "# Slide\n<!-- markdown-pptx:slide\nnotes: |\n  Private speaker note.\n-->\n\nVisible body.\n"
    )
    deck = parse_deck(source, input_path=None, source_name="deck.md")
    rendered = MD.render(source)

    assert deck.text_colors.title == "var(--accent-1)"
    assert deck.slides[0].notes == "Private speaker note."
    assert deck.slides[0].body.paragraphs[0].fragments[0].text == "Visible body."
    assert "Private speaker note." in rendered
    assert "<!-- markdown-pptx:deck" in rendered
    assert "<!-- markdown-pptx:slide" in rendered
    assert "<p>Private speaker note." not in rendered


def test_legacy_yaml_front_matter_is_rejected() -> None:
    with pytest.raises(ParseError):
        parse_deck("---\naspect_ratio: '4:3'\n---\n\n# Slide\n", input_path=None, source_name="deck.md")
    with pytest.raises(ParseError):
        parse_deck("# Slide\n---\nlayout: Title Only\n---\n", input_path=None, source_name="deck.md")


def test_duplicate_and_unterminated_metadata_comments_are_rejected() -> None:
    with pytest.raises(ParseError) as duplicate:
        parse_deck(
            "<!-- markdown-pptx:deck\n-->\n<!-- markdown-pptx:deck\n-->\n# Slide\n",
            input_path=None,
            source_name="deck.md",
        )
    assert duplicate.value.context.code == "metadata_comment_placement"
    with pytest.raises(ParseError) as unterminated:
        parse_deck("# Slide\n<!-- markdown-pptx:slide\nlayout: Title Only\n", input_path=None, source_name="deck.md")
    assert unterminated.value.context.code == "unterminated_metadata_comment"
    with pytest.raises(ParseError) as inline_close:
        parse_deck(
            "# Slide\n<!-- markdown-pptx:slide\nnotes: Contains --> text\n-->\n",
            input_path=None,
            source_name="deck.md",
        )
    assert inline_close.value.context.code == "invalid_metadata_comment"


def test_setext_h1_starts_slides_and_setext_h2_stays_in_body() -> None:
    deck = parse_deck(
        "First **title**\n=============\n\nSubtitle\n--------\n\nSecond title\n============\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )
    assert [slide.title for slide in deck.slides] == ["First title", "Second title"]
    assert deck.slides[0].body.paragraphs[0].heading_level == 2
    assert deck.slides[0].title_fragments[1].kind == "strong"


def test_setext_h1_with_metadata_keeps_body_error_line() -> None:
    source = (
        "Title\n=====\n<!-- markdown-pptx:slide\nlayout: Title and Content\n-->\n\nInline ![alt](image.png) image.\n"
    )
    with pytest.raises(UnsupportedContentError) as excinfo:
        parse_deck(source, input_path=None, source_name="deck.md")
    assert excinfo.value.context.line == 7


def test_atx_title_closing_marks_indentation_and_inline_formatting() -> None:
    deck = parse_deck("  # **Bold** *Title* ###\n", input_path=None, source_name="deck.md")
    assert deck.slides[0].title == "Bold Title"
    assert [fragment.kind for fragment in deck.slides[0].title_fragments if fragment.children] == [
        "strong",
        "emphasis",
    ]


def test_h1_inside_html_comment_does_not_start_slide() -> None:
    deck = parse_deck("# Slide\n\n<!--\n# ignored\n-->\n\nText\n", input_path=None, source_name="deck.md")
    assert len(deck.slides) == 1
    assert deck.slides[0].body.paragraphs[0].fragments[0].text == "Text"


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
            "# Slide\n<!-- markdown-pptx:slide\nlayout: Title Only\n-->\n\nBody\n",
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
        "A footnote reference[^1].\n\n[^1]: Footnote text.",
        "Inline ![alt](image.png) image.",
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


def test_breaks_lists_quotes_and_inline_extensions_preserve_structure() -> None:
    deck = parse_deck(
        "# Slide\n\nsoft\nwrap and hard  \nbreak\n\n1. First\n\n   More first\n\n2.\n"
        "\n> - Quoted\n\n>\n\nH~2~O x^2^ ~~old~~ **bold *italic***\n",
        input_path=None,
        source_name="deck.md",
    )
    paragraphs = deck.slides[0].body.paragraphs
    assert [fragment.kind for fragment in paragraphs[0].fragments] == [
        "text",
        "text",
        "text",
        "break",
        "text",
    ]
    assert [paragraph.kind for paragraph in paragraphs[1:4]] == [
        "list_item",
        "list_continuation",
        "list_item",
    ]
    assert [paragraph.ordered_index for paragraph in paragraphs[1:4]] == [1, 1, 2]
    assert paragraphs[3].fragments == []
    assert paragraphs[4].kind == "list_item" and paragraphs[4].quote_depth == 1
    assert paragraphs[5].kind == "blockquote" and paragraphs[5].quote_depth == 1
    assert [fragment.kind for fragment in paragraphs[6].fragments if fragment.children] == [
        "subscript",
        "superscript",
        "strike",
        "strong",
    ]


def test_empty_bullet_tasks_html_and_linked_image() -> None:
    deck = parse_deck(
        "# Text\n\n- one\n-\n- [ ] open\n- [x] done\n\nBefore<!-- note --><b>after</b>\n"
        '\n# Picture\n\n[![**Chart**](chart.png "Revenue")](https://example.com)\n',
        input_path=None,
        source_name="deck.md",
    )
    paragraphs = deck.slides[0].body.paragraphs
    assert paragraphs[1].kind == "list_item" and paragraphs[1].fragments == []
    assert [paragraph.task_checked for paragraph in paragraphs[2:4]] == [False, True]
    assert [fragment.text for fragment in paragraphs[4].fragments] == ["Before", "after"]
    image = deck.slides[1].body.images[0]
    assert (image.alt, image.title, image.href) == ("Chart", "Revenue", "https://example.com")


def test_hide_background_graphics_requires_a_boolean() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            '# Slide\n<!-- markdown-pptx:slide\nhide_background_graphics: "false"\n-->\n\nBody\n',
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_hide_background_graphics"


@pytest.mark.parametrize("selector", ["2", "Executive Theme"])
def test_parse_slide_master_selector(selector: str) -> None:
    deck = parse_deck(
        f"# Slide\n<!-- markdown-pptx:slide\nmaster: {selector!r}\n-->\n\nBody\n",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    assert deck.slides[0].master == selector


@pytest.mark.parametrize("selector", ["0", "-1", "true", "1.5", "''"])
def test_slide_master_selector_rejects_invalid_values(selector: str) -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            f"# Slide\n<!-- markdown-pptx:slide\nmaster: {selector}\n-->\n\nBody\n",
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
<!-- markdown-pptx:slide
table:
  header_row: false
  total_row: true
  first_column: true
  last_column: true
  banded_rows: false
  banded_columns: true
-->

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
            f"# Table\n<!-- markdown-pptx:slide\ntable: {value}\n-->\n\n| A |\n| --- |\n| 1 |\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_table_options"


def test_table_options_reject_unknown_keys() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            "# Table\n<!-- markdown-pptx:slide\ntable:\n  header_column: true\n-->\n\n| A |\n| --- |\n| 1 |\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "unknown_table_option_keys"


def test_table_options_require_boolean_values() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            '# Table\n<!-- markdown-pptx:slide\ntable:\n  header_row: "true"\n-->\n\n| A |\n| --- |\n| 1 |\n',
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_table_options"


def test_table_options_require_string_keys() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_deck(
            "# Table\n<!-- markdown-pptx:slide\ntable:\n  true: false\n-->\n\n| A |\n| --- |\n| 1 |\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "invalid_table_options"


def test_table_options_require_exactly_one_table_body() -> None:
    with pytest.raises(UnsupportedContentError) as excinfo:
        parse_deck(
            "# Not a table\n<!-- markdown-pptx:slide\ntable:\n  banded_rows: false\n-->\n\nParagraph.\n",
            input_path=Path("deck.md"),
            source_name="deck.md",
        )

    assert excinfo.value.context.code == "unsupported_content"

import pytest

from markdown_slides.errors import ParseError
from markdown_slides.parser import parse_deck

DIRECTIVES = ["media_effects", "table_effects", "media_layout", "table_layout", "video", "unknown", "image", "effects"]


@pytest.mark.parametrize("category", DIRECTIVES)
@pytest.mark.parametrize("container", ["list", "quote", "cell", "h1", "h2", "inline"])
def test_reserved_directives_cannot_be_silently_ignored(category, container):
    comment = f"<!-- markdown-pptx:{category}\nwidth: 50%\n-->"
    inline = f"<!-- markdown-pptx:{category} width: 50% -->"
    body = {
        "list": "- Content\n\n  " + comment.replace("\n", "\n  "),
        "quote": "> " + comment.replace("\n", "\n> "),
        "cell": f"| A |\n| --- |\n| {inline} |",
        "h1": f"# Title {inline}",
        "h2": f"## Subtitle {inline}",
        "inline": f"Content {inline}",
    }[container]
    source = body if container == "h1" else f"# Slide\n\n{body}\n"
    with pytest.raises(ParseError) as exc:
        parse_deck(source, input_path=None, source_name="directives.md")
    assert exc.value.context.input_path == "directives.md"
    assert exc.value.context.slide_index == 1
    assert exc.value.context.line is not None


@pytest.mark.parametrize("category", DIRECTIVES)
def test_unknown_or_orphan_top_level_directives_are_errors(category):
    source = f"# Slide\n\n<!-- markdown-pptx:{category}\nwidth: 50%\n-->\n"
    with pytest.raises(ParseError):
        parse_deck(source, input_path=None, source_name="directives.md")


def test_authoring_comments_and_literal_code_examples_remain_supported():
    source = (
        "# Examples\n\n- Content\n\n  <!-- Ordinary authoring note -->\n\n"
        "```markdown\n<!-- markdown-pptx:unknown\nwidth: 50%\n-->\n```\n\n"
        "    <!-- markdown-pptx:media_effects -->\n\n"
        "Use `<!-- markdown-pptx:table_layout -->` as literal code.\n"
    )
    slide = parse_deck(source, input_path=None, source_name="literal.md").slides[0]
    assert slide.layout == "Title and Content"
    assert [p.kind for p in slide.body.paragraphs].count("code") == 2


@pytest.mark.parametrize("category", DIRECTIVES)
@pytest.mark.parametrize("deck_metadata", ["", "<!-- markdown-pptx:deck\nlayout: Title and Content\n-->\n\n"])
@pytest.mark.parametrize("heading", ["# Title\n", "Title\n=====\n", ""])
def test_preamble_rejects_reserved_directives_with_source_context(category, deck_metadata, heading):
    preamble = "<!-- Authoring note -->\n\n[guide]: https://example.com\n\n"
    prefix = deck_metadata + preamble
    source = prefix + f"<!-- markdown-pptx:{category}\nshadow: none\n-->\n\n" + heading
    with pytest.raises(ParseError) as exc:
        parse_deck(source, input_path=None, source_name="preamble.md")
    assert exc.value.context.input_path == "preamble.md"
    assert exc.value.context.line == len(prefix.splitlines()) + 1
    assert exc.value.context.slide_index is None
    if category in {"media_effects", "table_effects", "media_layout", "table_layout", "video"}:
        assert "before the first H1" in str(exc.value)
    else:
        assert "Unknown or misplaced" in str(exc.value)


@pytest.mark.parametrize("deck_metadata", ["", "<!-- markdown-pptx:deck\nlayout: Title and Content\n-->\n\n"])
def test_preamble_keeps_ordinary_comments_and_reference_definitions(deck_metadata):
    source = (
        deck_metadata + '<!-- Authoring note -->\n\n[guide]: https://example.com "Guide"\n\n'
        "# [Title][guide]\n\n[Read the guide][guide].\n"
    )
    slide = parse_deck(source, input_path=None, source_name="preamble.md").slides[0]
    assert slide.title == "Title"
    assert slide.title_fragments[0].href == "https://example.com"
    assert slide.body.paragraphs[0].fragments[0].href == "https://example.com"


@pytest.mark.parametrize("deck_metadata", ["", "<!-- markdown-pptx:deck\nlayout: Title and Content\n-->\n\n"])
def test_literal_directives_before_first_slide_remain_visible_content(deck_metadata):
    source = deck_metadata + "```markdown\n<!-- markdown-pptx:unknown -->\n```\n\n# Title\n"
    with pytest.raises(ParseError) as exc:
        parse_deck(source, input_path=None, source_name="preamble.md")
    assert exc.value.context.code == "content_before_first_slide"
    assert exc.value.context.line == len(deck_metadata.splitlines()) + 1

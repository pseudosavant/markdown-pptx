from pathlib import Path

import pytest

from markdown_slides.errors import ParseError
from markdown_slides.parser import parse_deck


def parse_image(settings: str):
    deck = parse_deck(
        f'# Picture\n\n![Description](photo.png "Title")\n\n<!-- markdown-pptx:media_effects\n{settings}\n-->\n',
        input_path=Path("deck.md"),
        source_name="deck.md",
    )
    return deck.slides[0].body.images[0]


@pytest.mark.parametrize("quote", ["", "'", '"'])
def test_image_effects_accept_quoted_and_unquoted_css_values(quote: str) -> None:
    image = parse_image(
        f"border: {quote}1pt solid var(--accent-1){quote}\n"
        f"border_radius: {quote}8pt{quote}\n"
        f"shadow: {quote}-2pt 3pt 6pt rgba(0, 0, 0, 0.25){quote}\n"
        f"reflection: {quote}4pt 30%{quote}"
    )
    effects = image.effects
    assert (image.alt, image.title) == ("Description", "Title")
    assert (effects.border.width_pt, effects.border.style, effects.border.color.value) == (
        1,
        "solid",
        "var(--accent-1)",
    )
    assert effects.border_radius_pt == 8
    assert (effects.shadow.offset_x_pt, effects.shadow.offset_y_pt, effects.shadow.blur_pt) == (-2, 3, 6)
    assert (effects.shadow.color.value, effects.shadow.color.opacity) == ("#000000", 0.25)
    assert (effects.reflection.distance_pt, effects.reflection.amount) == (4, 0.3)


def test_image_effects_defaults_units_and_hex_alpha() -> None:
    effects = parse_image('border: "2px dotted #1234"\nborder_radius: 0.1in\nshadow: 0 2pt\nreflection: 4pt').effects
    assert effects.border.width_pt == 1.5
    assert effects.border.color.value == "#112233"
    assert effects.border.color.opacity == pytest.approx(0x44 / 255)
    assert effects.border_radius_pt == pytest.approx(7.2)
    assert effects.shadow.blur_pt == 0
    assert effects.shadow.color.opacity == 0.25
    assert effects.reflection.amount == 0.3
    assert parse_image('shadow: "1pt 1pt #00000040"').effects.shadow.color.opacity == pytest.approx(0x40 / 255)


def test_image_effects_can_be_disabled() -> None:
    effects = parse_image("border: none\nborder_radius: 0\nshadow: none\nreflection: none").effects
    assert effects.border is effects.shadow is effects.reflection is None
    assert effects.border_radius_pt == 0


def test_linked_reference_image_keeps_effects_and_hyperlink_metadata() -> None:
    deck = parse_deck(
        '# Picture\n\n[![Description][photo]](https://example.com "ScreenTip")\n\n'
        '<!-- markdown-pptx:media_effects\nborder_radius: 8pt\n-->\n\n[photo]: photo.png "Title"\n',
        input_path=None,
        source_name="deck.md",
    )
    image = deck.slides[0].body.images[0]
    assert (image.href, image.link_title, image.title) == ("https://example.com", "ScreenTip", "Title")
    assert image.effects.border_radius_pt == 8


@pytest.mark.parametrize(
    "settings",
    [
        "unknown: 1pt",
        "border-radius: 2pt",
        "border: true",
        "shadow: {}",
        "reflection: null",
        "border_radius: -1pt",
        "border_radius: 5",
        "border_radius: 5%",
        "border_radius: 1em",
        "border: 1pt double rgb(0, 0, 0)",
        "border: 1pt solid",
        "border: 1pt solid #000000",
        "shadow: 1pt 1pt 3pt #000000",
        "shadow: 1pt",
        "shadow: 1pt 1pt -3pt",
        "shadow: inset 1pt 1pt",
        "shadow: 1pt 1pt 2pt 3pt rgb(0, 0, 0)",
        "shadow: 1pt 1pt rgba(256, 0, 0, 0.25)",
        "shadow: 1pt 1pt rgba(0, 0, 0, 1.1)",
        "shadow: 1pt 1pt rgba(0, 0, 0, 0.25",
        "reflection: below 4pt 30%",
        "reflection: -1pt",
        "reflection: 4pt 0%",
        "reflection: 4pt 101%",
        "reflection: 4pt 0.3",
        "border_radius: 1pt\nborder_radius: 2pt",
        "[border, shadow]",
        "[]: 1pt",
    ],
)
def test_invalid_effect_settings_fail_with_source_context(settings: str) -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_image(settings)
    assert excinfo.value.context.code == "invalid_effect_settings"
    assert excinfo.value.context.input_path == "deck.md"
    assert excinfo.value.context.slide_index == 1
    assert excinfo.value.context.line == 5


@pytest.mark.parametrize(
    "body",
    [
        "<!-- markdown-pptx:media_effects\nborder_radius: 8pt\n-->\n\n![Image](photo.png)",
        "Text\n\n<!-- markdown-pptx:media_effects\nborder_radius: 8pt\n-->",
        "![Image](photo.png) <!-- markdown-pptx:media_effects border_radius: 8pt -->",
        "![Image](photo.png)\n\nText\n\n<!-- markdown-pptx:media_effects\nborder_radius: 8pt\n-->",
        "![Image](photo.png)\n\n<!-- markdown-pptx:media_effects\nborder_radius: 8pt\n-->\n\n"
        "<!-- markdown-pptx:media_effects\nshadow: none\n-->",
        "![Image](photo.png)\n\n<!-- markdown-pptx:media_effects\nborder_radius: 8pt",
    ],
)
def test_image_comments_must_be_adjacent_complete_and_unique(body: str) -> None:
    with pytest.raises(ParseError):
        parse_deck(f"# Slide\n\n{body}\n", input_path=None, source_name="deck.md")


def test_image_effects_are_independent_in_two_content() -> None:
    deck = parse_deck(
        "<!-- markdown-pptx:deck\nlayout: Two Content\n-->\n\n# Pictures\n\n"
        "![Left](left.png)\n\n<!-- markdown-pptx:media_effects\nborder_radius: 8pt\n-->\n\n***\n\n"
        "![Right](right.png)\n\n<!-- markdown-pptx:media_effects\nreflection: 4pt 30%\n-->\n",
        input_path=None,
        source_name="deck.md",
    )
    left, right = (region.images[0].effects for region in deck.slides[0].content_regions)
    assert left.border_radius_pt == 8
    assert left.reflection is None
    assert right.border_radius_pt == 0
    assert right.reflection.amount == 0.3

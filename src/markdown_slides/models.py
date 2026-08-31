from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

CANONICAL_LAYOUTS = {
    "title-slide": "Title Slide",
    "titleandcontent": "Title and Content",
    "title-and-content": "Title and Content",
    "section-header": "Section Header",
    "title-only": "Title Only",
    "blank": "Blank",
}


def normalize_layout_name(value: str) -> str:
    key = "".join(ch for ch in value.lower() if ch.isalnum() or ch == "-")
    if key in CANONICAL_LAYOUTS:
        return CANONICAL_LAYOUTS[key]
    key = key.replace("-", "")
    if key in CANONICAL_LAYOUTS:
        return CANONICAL_LAYOUTS[key]
    return value


@dataclass(slots=True)
class InlineText:
    kind: str
    text: str | None = None
    href: str | None = None
    children: list[InlineText] = field(default_factory=list)


@dataclass(slots=True)
class Paragraph:
    kind: str
    fragments: list[InlineText]
    level: int = 0
    ordered_index: int | None = None
    heading_level: int | None = None


@dataclass(slots=True)
class ImageBlock:
    src: str
    alt: str


@dataclass(slots=True)
class TableBlock:
    headers: list[list[InlineText]]
    rows: list[list[list[InlineText]]]


@dataclass(slots=True)
class TableOptions:
    header_row: bool = True
    total_row: bool = False
    first_column: bool = False
    last_column: bool = False
    banded_rows: bool = True
    banded_columns: bool = False


@dataclass(slots=True)
class BodyContent:
    paragraphs: list[Paragraph] = field(default_factory=list)
    images: list[ImageBlock] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.paragraphs and not self.images and not self.tables

    @property
    def has_text_flow(self) -> bool:
        return bool(self.paragraphs)

    @property
    def has_non_text(self) -> bool:
        return bool(self.images or self.tables)


@dataclass(slots=True)
class GradientStop:
    color: str
    position: float


@dataclass(slots=True)
class Background:
    kind: str
    value: str | None = None
    url: str | None = None
    gradient_kind: str | None = None
    angle: float | None = None
    stops: list[GradientStop] = field(default_factory=list)


@dataclass(slots=True)
class Fonts:
    body: str = "Aptos"
    headings: str = "Aptos Display"


@dataclass(slots=True)
class TextColors:
    title: str | None = None
    body: str | None = None


@dataclass(slots=True)
class ColorScheme:
    name: str
    colors: dict[str, str]


@dataclass(slots=True)
class Slide:
    index: int
    title: str
    layout: str | None
    master: int | str | None
    background: Background | None
    text_colors: TextColors | None
    hide_background_graphics: bool
    notes: str | None
    table_options: TableOptions
    body_markdown: str
    body: BodyContent
    line_number: int


@dataclass(slots=True)
class Deck:
    input_path: Path | None
    source_name: str
    aspect_ratio: str
    fonts: Fonts
    fonts_override: bool
    text_colors: TextColors | None
    color_scheme: ColorScheme | None
    background: Background | None
    slides: list[Slide]

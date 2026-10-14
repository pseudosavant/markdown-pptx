from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

CANONICAL_LAYOUTS = {
    "title-slide": "Title Slide",
    "titleandcontent": "Title and Content",
    "title-and-content": "Title and Content",
    "twocontent": "Two Content",
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
    title: str | None = None


@dataclass(slots=True)
class ListContext:
    level: int
    ordered_index: int | None
    task_checked: bool | None = None


@dataclass(slots=True)
class Paragraph:
    kind: str
    fragments: list[InlineText]
    level: int = 0
    ordered_index: int | None = None
    heading_level: int | None = None
    quote_depth: int = 0
    task_checked: bool | None = None
    code_language: str | None = None
    list_context: ListContext | None = None


@dataclass(slots=True)
class EffectColor:
    value: str
    opacity: float = 1.0


@dataclass(slots=True)
class EffectBorder:
    width_pt: float
    style: str
    color: EffectColor


@dataclass(slots=True)
class EffectShadow:
    offset_x_pt: float
    offset_y_pt: float
    blur_pt: float = 0.0
    color: EffectColor = field(default_factory=lambda: EffectColor("#000000", 0.25))


@dataclass(slots=True)
class EffectReflection:
    distance_pt: float
    amount: float = 0.3


@dataclass(slots=True)
class Effects:
    border: EffectBorder | None = None
    border_radius_pt: float = 0.0
    shadow: EffectShadow | None = None
    reflection: EffectReflection | None = None
    specified: set[str] = field(default_factory=set)


@dataclass(slots=True)
class ObjectLayout:
    width: str = "auto"
    align: str = "center"
    valign: str = "top"
    specified: set[str] = field(default_factory=set)


@dataclass(slots=True)
class ImageBlock:
    src: str
    alt: str
    title: str | None = None
    href: str | None = None
    link_title: str | None = None
    effects: Effects | None = None
    layout: ObjectLayout | None = None


@dataclass(slots=True)
class VideoBlock:
    source: str
    kind: str
    width: str = "auto"
    aspect_ratio: float | None = None
    align: str = "center"
    valign: str = "top"
    poster: str | None = None
    start: str = "click"
    fullscreen: bool = False
    loop: bool = False
    mute: bool = False
    effects: Effects | None = None
    layout: ObjectLayout | None = None


@dataclass(slots=True)
class TableBlock:
    headers: list[list[InlineText]]
    rows: list[list[list[InlineText]]]
    alignments: list[str] = field(default_factory=list)
    effects: Effects | None = None
    layout: ObjectLayout | None = None


@dataclass(slots=True)
class TableOptions:
    header_row: bool = True
    total_row: bool = False
    first_column: bool = False
    last_column: bool = False
    banded_rows: bool = True
    banded_columns: bool = False
    header_fill: str | None = None
    row_fill: str | None = None
    banded_row_fill: str | None = None


@dataclass(slots=True)
class BodyContent:
    paragraphs: list[Paragraph] = field(default_factory=list)
    images: list[ImageBlock] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)
    videos: list[VideoBlock] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.paragraphs and not self.images and not self.tables and not self.videos

    @property
    def has_text_flow(self) -> bool:
        return bool(self.paragraphs)

    @property
    def has_non_text(self) -> bool:
        return bool(self.images or self.tables or self.videos)


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
    title_fragments: list[InlineText] = field(default_factory=list)
    secondary_body: BodyContent | None = None
    code_highlighting: str | None = None
    hidden: bool = False
    media_effects: Effects | None = None
    table_effects: Effects | None = None
    media_layout: ObjectLayout | None = None
    table_layout: ObjectLayout | None = None

    @property
    def content_regions(self) -> list[BodyContent]:
        return [self.body] if self.secondary_body is None else [self.body, self.secondary_body]


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
    code_highlighting: str = "default"
    layout: str = "Title and Content"
    media_effects: Effects | None = None
    table_effects: Effects | None = None
    table_options: TableOptions = field(default_factory=TableOptions)
    media_layout: ObjectLayout | None = None
    table_layout: ObjectLayout | None = None

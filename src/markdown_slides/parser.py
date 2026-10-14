from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from markdown_slides.assets import load_color_schemes
from markdown_slides.effect_settings import TABLE_COLOR_KEYS, load_settings_yaml, merge_effects, parse_effect_values
from markdown_slides.errors import ParseError, UnsupportedContentError
from markdown_slides.layout_settings import merge_layouts, parse_layout_values
from markdown_slides.markdown_body import (
    MD,
    _html_text,
    _validate_metadata_comments,
    parse_body_regions,
    parse_inline_children,
)
from markdown_slides.models import (
    Background,
    BodyContent,
    ColorScheme,
    Deck,
    Fonts,
    GradientStop,
    InlineText,
    Slide,
    TableOptions,
    TextColors,
    VideoBlock,
    normalize_layout_name,
)

DOCUMENT_KEYS = {
    "media_layout",
    "table_layout",
    "media_effects",
    "table_effects",
    "table",
    "layout",
    "aspect_ratio",
    "fonts",
    "color_scheme",
    "background",
    "title_color",
    "body_color",
    "code_highlighting",
}
SLIDE_KEYS = {
    "media_layout",
    "table_layout",
    "media_effects",
    "table_effects",
    "hidden",
    "master",
    "layout",
    "background",
    "title_color",
    "body_color",
    "hide_background_graphics",
    "notes",
    "table",
    "code_highlighting",
}
TABLE_OPTION_DEFAULTS = {
    "header_row": True,
    "total_row": False,
    "first_column": False,
    "last_column": False,
    "banded_rows": True,
    "banded_columns": False,
}
COLOR_KEYS = {
    "dark_1",
    "light_1",
    "dark_2",
    "light_2",
    "accent_1",
    "accent_2",
    "accent_3",
    "accent_4",
    "accent_5",
    "accent_6",
    "hyperlink",
    "followed_hyperlink",
}
SUPPORTED_LAYOUTS = {
    "Title Slide",
    "Title and Content",
    "Two Content",
    "Section Header",
    "Title Only",
    "Blank",
}
HEX_COLOR_RE = re.compile(r"^#(?P<hex>[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
RGB_RE = re.compile(r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$", re.IGNORECASE)
HSL_RE = re.compile(
    r"^hsl\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)%\s*,\s*(\d+(?:\.\d+)?)%\s*\)$",
    re.IGNORECASE,
)
URL_RE = re.compile(r"^url\((?P<value>.+)\)$", re.IGNORECASE)
LINEAR_RE = re.compile(r"^linear-gradient\((?P<args>.+)\)$", re.IGNORECASE)
RADIAL_RE = re.compile(r"^radial-gradient\((?P<args>.+)\)$", re.IGNORECASE)
THEME_VAR_RE = re.compile(r"^var\(\s*--(?P<name>[a-z0-9-]+)\s*\)$", re.IGNORECASE)
SETEXT_H1_RE = re.compile(r"^[ ]{0,3}=+[ \t]*$")
ATX_H1_RE = re.compile(r"^[ ]{0,3}#(?:[ \t]+.*|[ \t]*)$")
FENCE_OPEN_RE = re.compile(r"^[ ]{0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
METADATA_OPEN_RE = re.compile(r"^[ ]{0,3}<!-- markdown-pptx:(?P<scope>deck|slide)[ \t]*$")
METADATA_PREFIX_RE = re.compile(r"^[ ]{0,3}<!-- markdown-pptx:(?:deck|slide)\b")
THEME_COLOR_VARS = {
    "dark-1": "dark_1",
    "light-1": "light_1",
    "dark-2": "dark_2",
    "light-2": "light_2",
    "accent-1": "accent_1",
    "accent-2": "accent_2",
    "accent-3": "accent_3",
    "accent-4": "accent_4",
    "accent-5": "accent_5",
    "accent-6": "accent_6",
    "hyperlink": "hyperlink",
    "followed-hyperlink": "followed_hyperlink",
}


@dataclass(slots=True)
class RawSlide:
    title: str
    title_fragments: list[InlineText]
    line_number: int
    body_line_number: int
    config: dict[str, object]
    body_markdown: str
    title_source: str


@dataclass(frozen=True, slots=True)
class FenceState:
    character: str
    length: int


def parse_deck(text: str, *, input_path: Path | None, source_name: str) -> Deck:
    lines = text.splitlines()
    document_config, slides, references = _split_source(lines, source_name=source_name)
    if not slides:
        raise ParseError("missing_slides", "The document must contain at least one '# H1' slide.")

    aspect_ratio = _parse_aspect_ratio(document_config)
    fonts, fonts_override = _parse_fonts(document_config)
    document_text_colors = _parse_text_colors(document_config, line=1)
    color_scheme = _parse_color_scheme(document_config)
    document_background = _parse_background(document_config.get("background"), line=1)
    code_highlighting = _parse_code_highlighting(document_config, source_name=source_name, line=1) or "default"
    document_layout = _parse_layout(document_config.get("layout"), source_name=source_name, line=1, document=True)
    document_media_effects = _parse_effect_defaults(document_config, "media_effects", source_name, 1)
    document_table_effects = _parse_effect_defaults(document_config, "table_effects", source_name, 1)
    document_media_layout = _parse_object_layout(document_config, "media_layout", source_name, 1)
    document_table_layout = _parse_object_layout(document_config, "table_layout", source_name, 1)
    document_table_options = _parse_table_options(
        document_config.get("table"),
        configured="table" in document_config,
        line=1,
        slide_index=None,
        source_name=source_name,
    )

    parsed_slides: list[Slide] = []
    for slide_index, raw_slide in enumerate(slides, start=1):
        raw_slide.title, raw_slide.title_fragments = _heading_payload(raw_slide.title_source, references=references)
        master = _parse_master_selector(
            raw_slide.config.get("master"),
            line=raw_slide.line_number,
            slide_index=slide_index,
            source_name=source_name,
        )
        media_effects = _parse_effect_defaults(
            raw_slide.config, "media_effects", source_name, raw_slide.line_number, slide_index
        )
        table_effects = _parse_effect_defaults(
            raw_slide.config, "table_effects", source_name, raw_slide.line_number, slide_index
        )
        media_layout = _parse_object_layout(
            raw_slide.config, "media_layout", source_name, raw_slide.line_number, slide_index
        )
        table_layout = _parse_object_layout(
            raw_slide.config, "table_layout", source_name, raw_slide.line_number, slide_index
        )
        slide_layout = _parse_layout(
            raw_slide.config.get("layout"),
            source_name=source_name,
            line=raw_slide.line_number,
            slide_index=slide_index,
        )
        hidden = raw_slide.config.get("hidden", False)
        if not isinstance(hidden, bool):
            raise ParseError(
                "invalid_hidden",
                "hidden must be true or false.",
                line=raw_slide.line_number,
                slide_index=slide_index,
                input_path=source_name,
            )
        hide_background_graphics = raw_slide.config.get("hide_background_graphics", False)
        if not isinstance(hide_background_graphics, bool):
            raise ParseError(
                "invalid_hide_background_graphics",
                "hide_background_graphics must be true or false.",
                line=raw_slide.line_number,
                slide_index=slide_index,
                input_path=source_name,
            )
        notes = raw_slide.config.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise ParseError(
                "invalid_notes",
                "Slide notes must be a string.",
                line=raw_slide.line_number,
                slide_index=slide_index,
                input_path=source_name,
            )
        table_options = _parse_table_options(
            raw_slide.config.get("table"),
            configured="table" in raw_slide.config,
            line=raw_slide.line_number,
            slide_index=slide_index,
            source_name=source_name,
            defaults=document_table_options,
        )
        slide_background = _parse_background(
            raw_slide.config.get("background"),
            line=raw_slide.line_number,
        )
        slide_text_colors = _parse_text_colors(raw_slide.config, line=raw_slide.line_number)
        regions = parse_body_regions(
            raw_slide.body_markdown,
            two_content=slide_layout == "Two Content",
            source_name=source_name,
            slide_index=slide_index,
            base_line=raw_slide.body_line_number,
            references=references,
            infer_two_content=slide_layout is None,
        )
        body = regions[0]
        heading_only = _is_heading_slide_body(body)
        if slide_layout is not None:
            normalized_layout = slide_layout
        elif len(regions) == 2:
            normalized_layout = "Two Content"
        elif raw_slide.title and heading_only:
            normalized_layout = "Title Slide" if slide_index == 1 else "Section Header"
        else:
            normalized_layout = document_layout or (
                "Blank" if not raw_slide.title and body.is_empty else "Title and Content"
            )
        if normalized_layout == "Two Content" and len(regions) != 2:
            raise UnsupportedContentError(
                "Two Content slides require exactly one top-level horizontal rule separating the two content areas.",
                slide_index=slide_index,
                line=raw_slide.body_line_number,
                input_path=source_name,
            )
        if normalized_layout in {"Title Slide", "Section Header"} and heading_only and body.paragraphs:
            body.paragraphs[0] = replace(body.paragraphs[0], kind="subtitle", heading_level=None)
        for region in regions:
            for item in [*region.images, *region.videos]:
                item.effects = merge_effects(document_media_effects, media_effects, item.effects)
                item.layout = merge_layouts(document_media_layout, media_layout, item.layout)
                if isinstance(item, VideoBlock) and item.layout is not None:
                    item.width, item.align, item.valign = item.layout.width, item.layout.align, item.layout.valign
            for table in region.tables:
                table.effects = merge_effects(document_table_effects, table_effects, table.effects)
                table.layout = merge_layouts(document_table_layout, table_layout, table.layout)
        for region in regions:
            _validate_layout_content(
                layout=normalized_layout,
                title=raw_slide.title,
                body=region,
                slide_index=slide_index,
                source_name=source_name,
                line=raw_slide.line_number,
            )
        if "table" in raw_slide.config and not any(region.tables for region in regions):
            raise UnsupportedContentError(
                "Slide table options require at least one table on the slide.",
                slide_index=slide_index,
                line=raw_slide.line_number,
                input_path=source_name,
            )
        parsed_slides.append(
            Slide(
                index=slide_index,
                title=raw_slide.title,
                layout=normalized_layout,
                master=master,
                background=slide_background,
                text_colors=slide_text_colors,
                hide_background_graphics=hide_background_graphics,
                notes=notes,
                table_options=table_options,
                body_markdown=raw_slide.body_markdown,
                body=body,
                line_number=raw_slide.line_number,
                title_fragments=raw_slide.title_fragments,
                secondary_body=regions[1] if len(regions) == 2 else None,
                hidden=hidden,
                media_effects=media_effects,
                table_effects=table_effects,
                media_layout=media_layout,
                table_layout=table_layout,
                code_highlighting=_parse_code_highlighting(
                    raw_slide.config, source_name=source_name, line=raw_slide.line_number, slide_index=slide_index
                ),
            )
        )

    return Deck(
        input_path=input_path,
        source_name=source_name,
        aspect_ratio=aspect_ratio,
        fonts=fonts,
        fonts_override=fonts_override,
        text_colors=document_text_colors,
        color_scheme=color_scheme,
        background=document_background,
        slides=parsed_slides,
        code_highlighting=code_highlighting,
        layout=document_layout or "Title and Content",
        media_effects=document_media_effects,
        table_effects=document_table_effects,
        table_options=document_table_options,
        media_layout=document_media_layout,
        table_layout=document_table_layout,
    )


def _is_heading_slide_body(body: BodyContent) -> bool:
    if body.is_empty:
        return True
    if body.has_non_text or len(body.paragraphs) != 1:
        return False
    paragraph = body.paragraphs[0]
    return (
        paragraph.kind == "heading"
        and paragraph.heading_level == 2
        and paragraph.quote_depth == 0
        and paragraph.list_context is None
    )


def _parse_layout(
    value: object, *, source_name: str, line: int, slide_index: int | None = None, document: bool = False
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ParseError(
            "invalid_document_layout" if document else "invalid_slide_layout",
            "Deck layout must be a string." if document else "Slide layout must be a string.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    layout = normalize_layout_name(value)
    if layout not in SUPPORTED_LAYOUTS:
        raise ParseError(
            "unsupported_layout",
            f"Unsupported layout '{value}'.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    return layout


def _parse_code_highlighting(
    config: dict, *, source_name: str, line: int, slide_index: int | None = None
) -> str | None:
    if "code_highlighting" not in config:
        return None
    value = config["code_highlighting"]
    if not isinstance(value, str) or value not in {"default", "theme-dark", "theme-light"}:
        raise ParseError(
            "invalid_code_highlighting",
            "code_highlighting must be default, theme-dark, or theme-light.",
            input_path=source_name,
            line=line,
            slide_index=slide_index,
        )
    return value


def _parse_effect_defaults(config, category, source_name, line, slide_index=None):
    if category not in config:
        return None
    return parse_effect_values(
        config[category], category=category, source_name=source_name, line=line, slide_index=slide_index
    )


def _parse_object_layout(config, category, source_name, line, slide_index=None):
    if category not in config:
        return None
    return parse_layout_values(
        config[category], category=category, source_name=source_name, line=line, slide_index=slide_index
    )


def _parse_table_options(
    value: object,
    *,
    configured: bool,
    line: int,
    slide_index: int | None,
    source_name: str,
    defaults: TableOptions | None = None,
) -> TableOptions:
    inherited = {key: getattr(defaults, key) for key in TABLE_OPTION_DEFAULTS} if defaults else TABLE_OPTION_DEFAULTS
    if not configured:
        return TableOptions(**inherited)
    if not isinstance(value, dict):
        raise ParseError(
            "invalid_table_options",
            "table must be a mapping of PowerPoint table-style options.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    if any(not isinstance(key, str) for key in value):
        raise ParseError(
            "invalid_table_options",
            "table option keys must be strings.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    unknown = sorted(set(value) - (set(TABLE_OPTION_DEFAULTS) | TABLE_COLOR_KEYS))
    if unknown:
        raise ParseError(
            "unknown_table_option_keys",
            f"Unknown table option key(s): {', '.join(unknown)}.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    options = inherited | value
    invalid = [key for key, option in value.items() if key in TABLE_OPTION_DEFAULTS and not isinstance(option, bool)]
    if invalid:
        raise ParseError(
            "invalid_table_options",
            f"Table option(s) must be true or false: {', '.join(sorted(invalid))}.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    for key in TABLE_COLOR_KEYS & value.keys():
        if not isinstance(value[key], str):
            raise ParseError(
                "invalid_table_color",
                f"{key} must be a color string.",
                line=line,
                slide_index=slide_index,
                input_path=source_name,
            )
        try:
            options[key] = _parse_color_expression(value[key])
        except ParseError as exc:
            raise ParseError(
                "invalid_table_color",
                f"Invalid {key}: {exc}",
                line=line,
                slide_index=slide_index,
                input_path=source_name,
            ) from exc
    return TableOptions(**options)


def _parse_master_selector(
    value: object,
    *,
    line: int,
    slide_index: int,
    source_name: str,
) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        valid = False
    elif isinstance(value, int):
        valid = value > 0
    elif isinstance(value, str):
        value = value.strip()
        valid = bool(value)
    else:
        valid = False
    if not valid:
        raise ParseError(
            "invalid_master_selector",
            "Slide master must be a positive 1-based integer or a non-empty master/theme name.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    return value


def _split_source(lines: list[str], *, source_name: str) -> tuple[dict[str, object], list[RawSlide], dict]:
    index = 0
    document_config: dict[str, object] = {}
    _reject_legacy_front_matter(lines, index, DOCUMENT_KEYS, source_name=source_name)
    if lines and _metadata_scope(lines[0]) == "deck":
        document_config, index = _parse_metadata_comment(lines, 0, DOCUMENT_KEYS, source_name=source_name)
    preamble_line = index + 1

    slides: list[RawSlide] = []
    current_title: str | None = None
    current_title_source = ""
    reference_env: dict = {}
    current_title_fragments: list[InlineText] = []
    current_line: int | None = None
    current_body_line: int | None = None
    current_config: dict[str, object] = {}
    current_body: list[str] = []
    fence: FenceState | None = None

    while index < len(lines):
        line = lines[index]
        was_in_fence = fence is not None
        fence = _next_fence_state(line, fence)
        atx = (
            bool(ATX_H1_RE.match(line)) and _top_level_h1_start([*current_body, line]) == len(current_body)
            if not was_in_fence and fence is None
            else False
        )
        setext_start: int | None = None
        if (
            not atx
            and not was_in_fence
            and fence is None
            and index + 1 < len(lines)
            and SETEXT_H1_RE.match(lines[index + 1])
        ):
            candidate = [*current_body, line, lines[index + 1]]
            setext_start = _top_level_h1_start(candidate)
        if atx or setext_start is not None:
            if atx:
                title_source = line
                title_line = index + 1
                prefix = current_body
            else:
                assert setext_start is not None
                candidate = [*current_body, line, lines[index + 1]]
                title_source = "\n".join(candidate[setext_start:])
                title_line = index - (len(current_body) - setext_start) + 1
                prefix = current_body[:setext_start]
            _validate_metadata_comments(
                MD.parse(title_source),
                source_name=source_name,
                slide_index=len(slides) + (2 if current_title is not None else 1),
                base_line=title_line,
            )
            title, title_fragments = _heading_payload(title_source)
            if current_title is not None:
                slides.append(
                    RawSlide(
                        title=current_title,
                        title_fragments=current_title_fragments,
                        line_number=current_line or 1,
                        body_line_number=current_body_line or 1,
                        config=current_config,
                        body_markdown="\n".join(prefix).rstrip(),
                        title_source=current_title_source,
                    )
                )
                MD.parse("\n".join(prefix), reference_env)
            elif _visible_preamble(prefix, reference_env, source_name=source_name, base_line=preamble_line):
                first = next(i for i, part in enumerate(prefix) if part.strip())
                raise ParseError(
                    "content_before_first_slide",
                    "Content is not allowed before the first H1 slide.",
                    line=preamble_line + first,
                    input_path=source_name,
                )
            current_title = title
            current_title_source = title_source
            current_title_fragments = title_fragments
            current_line = title_line
            current_config = {}
            current_body = []
            index += 1 if atx else 2
            _reject_legacy_front_matter(lines, index, SLIDE_KEYS, source_name=source_name)
            if index < len(lines) and _metadata_scope(lines[index]) == "slide":
                current_config, index = _parse_metadata_comment(lines, index, SLIDE_KEYS, source_name=source_name)
            current_body_line = index + 1
            continue
        if not was_in_fence and fence is None and METADATA_PREFIX_RE.match(line):
            scope = _metadata_scope(line)
            raise ParseError(
                "metadata_comment_placement" if scope else "invalid_metadata_comment",
                (
                    f"{scope.capitalize()} metadata comment is not in its allowed position."
                    if scope
                    else "Metadata comment opening marker must be on its own line."
                ),
                line=index + 1,
                input_path=source_name,
            )
        current_body.append(line)
        index += 1

    if current_title is not None:
        slides.append(
            RawSlide(
                title=current_title,
                title_fragments=current_title_fragments,
                line_number=current_line or 1,
                body_line_number=current_body_line or 1,
                config=current_config,
                body_markdown="\n".join(current_body).rstrip(),
                title_source=current_title_source,
            )
        )
        MD.parse("\n".join(current_body), reference_env)
    elif _visible_preamble(current_body, reference_env, source_name=source_name, base_line=preamble_line):
        first = next(i for i, part in enumerate(current_body) if part.strip())
        raise ParseError(
            "content_before_first_slide",
            "Content is not allowed before the first H1 slide.",
            line=preamble_line + first,
            input_path=source_name,
        )
    return document_config, slides, reference_env.get("references", {})


def _visible_preamble(lines: list[str], env: dict, *, source_name: str, base_line: int) -> bool:
    """Reference definitions and ignored HTML may precede the first slide."""
    tokens = MD.parse("\n".join(lines), env)
    _validate_metadata_comments(
        tokens,
        source_name=source_name,
        slide_index=None,
        base_line=base_line,
        allow_element_comments=False,
    )
    for token in tokens:
        if token.type in {"paragraph_open", "paragraph_close"}:
            continue
        if token.type in {"html_block", "inline"} and not _html_text(token.content):
            continue
        return True
    return False


def _top_level_h1_start(lines: list[str]) -> int | None:
    tokens = MD.parse("\n".join(lines))
    if len(tokens) < 3:
        return None
    heading = tokens[-3]
    if (
        heading.type == "heading_open"
        and heading.tag == "h1"
        and heading.level == 0
        and heading.map is not None
        and heading.map[1] == len(lines)
    ):
        return heading.map[0]
    return None


def _heading_payload(source: str, *, references: dict | None = None) -> tuple[str, list[InlineText]]:
    tokens = MD.parse(source, {"references": dict(references or {})})
    inline = next(token for token in tokens if token.type == "inline")
    fragments = parse_inline_children(inline.children or [])
    return _plain_inline(fragments).strip(), fragments


def _plain_inline(fragments: list[InlineText]) -> str:
    parts: list[str] = []
    for fragment in fragments:
        if fragment.kind == "break":
            parts.append(" ")
        elif fragment.children:
            parts.append(_plain_inline(fragment.children))
        else:
            parts.append(fragment.text or "")
    return "".join(parts)


def _metadata_scope(line: str) -> str | None:
    match = METADATA_OPEN_RE.fullmatch(line)
    return match.group("scope") if match else None


def _reject_legacy_front_matter(lines: list[str], index: int, keys: set[str], *, source_name: str) -> None:
    if index + 1 < len(lines) and lines[index].strip() == "---":
        if any(lines[index + 1].lstrip().startswith(f"{key}:") for key in keys):
            raise ParseError(
                "legacy_front_matter",
                "YAML front matter is unsupported. Use a named markdown-pptx metadata comment.",
                line=index + 1,
                input_path=source_name,
            )


def _parse_metadata_comment(
    lines: list[str],
    start_index: int,
    allowed_keys: set[str],
    *,
    source_name: str,
) -> tuple[dict[str, object], int]:
    end_index = start_index + 1
    while end_index < len(lines) and lines[end_index].strip() != "-->":
        if "-->" in lines[end_index]:
            raise ParseError(
                "invalid_metadata_comment",
                "Metadata comment closing marker must be on its own line.",
                line=end_index + 1,
                input_path=source_name,
            )
        end_index += 1
    if end_index >= len(lines):
        raise ParseError(
            "unterminated_metadata_comment",
            "Metadata comment is not terminated.",
            line=start_index + 1,
            input_path=source_name,
        )
    raw = "\n".join(lines[start_index + 1 : end_index])
    try:
        loaded = load_settings_yaml(raw)
    except yaml.YAMLError as exc:
        raise ParseError(
            "invalid_yaml", f"Invalid YAML metadata: {exc}", line=start_index + 1, input_path=source_name
        ) from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ParseError(
            "invalid_metadata_comment",
            "Metadata comment must decode to a mapping.",
            line=start_index + 1,
            input_path=source_name,
        )
    if any(not isinstance(key, str) for key in loaded):
        raise ParseError(
            "invalid_metadata_comment",
            "Metadata keys must be strings.",
            line=start_index + 1,
            input_path=source_name,
        )
    unknown = sorted(set(loaded) - allowed_keys)
    if unknown:
        raise ParseError(
            "unknown_metadata_keys",
            f"Unknown metadata key(s): {', '.join(unknown)}.",
            line=start_index + 1,
            input_path=source_name,
        )
    return loaded, end_index + 1


def _parse_aspect_ratio(document_config: dict[str, object]) -> str:
    value = document_config.get("aspect_ratio", "16:9")
    if value not in {"16:9", "4:3"}:
        raise ParseError("invalid_aspect_ratio", "aspect_ratio must be '16:9' or '4:3'.")
    return str(value)


def _parse_fonts(document_config: dict[str, object]) -> tuple[Fonts, bool]:
    value = document_config.get("fonts")
    if value is None:
        return Fonts(), False
    if not isinstance(value, dict):
        raise ParseError("invalid_fonts", "fonts must be a mapping with 'body' and 'headings'.")
    unknown = sorted(set(value) - {"body", "headings"})
    if unknown:
        raise ParseError("unknown_font_keys", f"Unknown fonts key(s): {', '.join(unknown)}.")
    body = value.get("body", "Aptos")
    headings = value.get("headings", "Aptos Display")
    if not isinstance(body, str) or not isinstance(headings, str):
        raise ParseError("invalid_fonts", "fonts.body and fonts.headings must be strings.")
    return Fonts(body=body, headings=headings), True


def _parse_text_colors(config: dict[str, object], *, line: int) -> TextColors | None:
    title = _parse_optional_color(config, "title_color", line=line)
    body = _parse_optional_color(config, "body_color", line=line)
    if title is None and body is None:
        return None
    return TextColors(title=title, body=body)


def _parse_optional_color(config: dict[str, object], key: str, *, line: int) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ParseError("invalid_text_color", f"{key} must be a string color.", line=line)
    return _parse_color_expression(value)


def _parse_color_scheme(document_config: dict[str, object]) -> ColorScheme | None:
    if "color_scheme" not in document_config:
        return None
    presets = load_color_schemes()
    raw_value = document_config["color_scheme"]
    if not isinstance(raw_value, dict):
        raise ParseError("invalid_color_scheme", "color_scheme must be a mapping.")
    preset_name = raw_value.get("preset", "Office")
    if preset_name is not None and not isinstance(preset_name, str):
        raise ParseError("invalid_color_scheme", "color_scheme.preset must be a string.")
    matched_name = None
    colors: dict[str, str] = {}
    if preset_name:
        for candidate in presets:
            if candidate.casefold() == preset_name.casefold():
                matched_name = candidate
                colors.update(presets[candidate])
                break
        if matched_name is None:
            raise ParseError("unknown_color_scheme", f"Unknown color scheme preset '{preset_name}'.")
    else:
        matched_name = "Custom"
    unknown = sorted(set(raw_value) - (COLOR_KEYS | {"preset"}))
    if unknown:
        raise ParseError("unknown_color_keys", f"Unknown color_scheme key(s): {', '.join(unknown)}.")
    for key in COLOR_KEYS:
        if key in raw_value:
            value = raw_value[key]
            if not isinstance(value, str):
                raise ParseError("invalid_color_scheme", f"color_scheme.{key} must be a string color.")
            colors[key] = _parse_color_literal(value)
    missing = sorted(COLOR_KEYS - set(colors))
    if missing:
        raise ParseError("incomplete_color_scheme", f"Missing color scheme key(s): {', '.join(missing)}.")
    return ColorScheme(name=matched_name, colors=colors)


def _parse_background(value: object, *, line: int) -> Background | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ParseError("invalid_background", "background must be a string.", line=line)
    text = value.strip()
    if text.lower() == "none":
        return Background(kind="none")
    if HEX_COLOR_RE.match(text) or RGB_RE.match(text) or HSL_RE.match(text) or THEME_VAR_RE.match(text):
        return Background(kind="color", value=_parse_color_expression(text))
    match = URL_RE.match(text)
    if match:
        return Background(kind="image", url=_strip_quotes(match.group("value").strip()))
    match = LINEAR_RE.match(text)
    if match:
        angle, stops = _parse_gradient_arguments(match.group("args"), linear=True, line=line)
        return Background(kind="gradient", gradient_kind="linear", angle=angle, stops=stops)
    match = RADIAL_RE.match(text)
    if match:
        _, stops = _parse_gradient_arguments(match.group("args"), linear=False, line=line)
        return Background(kind="gradient", gradient_kind="radial", stops=stops)
    raise ParseError("invalid_background", f"Unsupported background syntax '{value}'.", line=line)


def _parse_gradient_arguments(raw_args: str, *, linear: bool, line: int) -> tuple[float | None, list[GradientStop]]:
    parts = _split_function_arguments(raw_args)
    if len(parts) < 2:
        raise ParseError("invalid_background", "Gradients require at least two stops.", line=line)
    angle: float | None = 180.0 if linear else None
    start_index = 0
    first = parts[0].strip()
    if linear and first.lower().endswith("deg"):
        try:
            angle = float(first[:-3])
        except ValueError as exc:
            raise ParseError("invalid_background", f"Invalid gradient angle '{first}'.", line=line) from exc
        start_index = 1
    elif not linear and first.lower() in {"circle", "ellipse"}:
        start_index = 1
    stops: list[GradientStop] = []
    for part in parts[start_index:]:
        stop_match = re.match(r"^(?P<color>.+?)\s+(?P<position>\d+(?:\.\d+)?)%$", part.strip())
        if not stop_match:
            raise ParseError("invalid_background", f"Invalid gradient stop '{part}'.", line=line)
        position = float(stop_match.group("position"))
        if position < 0 or position > 100:
            raise ParseError("invalid_background", "Gradient stop positions must be between 0% and 100%.", line=line)
        stops.append(GradientStop(color=_parse_color_expression(stop_match.group("color")), position=position / 100.0))
    if len(stops) < 2:
        raise ParseError("invalid_background", "Gradients require at least two stops.", line=line)
    return angle, stops


def _split_function_arguments(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current).strip())
    return parts


def _parse_color_expression(value: str) -> str:
    value = value.strip()
    var_match = THEME_VAR_RE.match(value)
    if var_match:
        name = var_match.group("name").lower()
        if name not in THEME_COLOR_VARS:
            raise ParseError("invalid_color", f"Unsupported theme color reference '{value}'.")
        return f"var(--{name})"
    return _parse_color_literal(value)


def _parse_color_literal(value: str) -> str:
    value = value.strip()
    hex_match = HEX_COLOR_RE.match(value)
    if hex_match:
        raw = hex_match.group("hex")
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        return f"#{raw.upper()}"
    rgb_match = RGB_RE.match(value)
    if rgb_match:
        channels = [int(item) for item in rgb_match.groups()]
        if any(channel < 0 or channel > 255 for channel in channels):
            raise ParseError("invalid_color", f"RGB color '{value}' is out of range.")
        return "#" + "".join(f"{channel:02X}" for channel in channels)
    hsl_match = HSL_RE.match(value)
    if hsl_match:
        hue = float(hsl_match.group(1)) % 360.0
        saturation = float(hsl_match.group(2))
        lightness = float(hsl_match.group(3))
        if saturation > 100 or lightness > 100:
            raise ParseError("invalid_color", f"HSL color '{value}' is out of range.")
        red, green, blue = colorsys.hls_to_rgb(hue / 360.0, lightness / 100.0, saturation / 100.0)
        return "#" + "".join(f"{round(channel * 255):02X}" for channel in (red, green, blue))
    raise ParseError("invalid_color", f"Unsupported color '{value}'.")


def _strip_quotes(value: str) -> str:
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    return value


def _next_fence_state(line: str, state: FenceState | None) -> FenceState | None:
    if state is not None:
        closing = re.match(rf"^[ ]{{0,3}}{re.escape(state.character)}{{{state.length},}}[ \t]*$", line)
        return None if closing else state
    opening = FENCE_OPEN_RE.match(line)
    if opening is None:
        return None
    marker = opening.group("marker")
    if marker[0] == "`" and "`" in opening.group("info"):
        return None
    return FenceState(character=marker[0], length=len(marker))


def _validate_layout_content(
    *,
    layout: str,
    title: str,
    body: BodyContent,
    slide_index: int,
    source_name: str,
    line: int,
) -> None:
    if layout == "Blank":
        if title or not body.is_empty:
            raise UnsupportedContentError(
                "Blank slides must have an empty title and empty body.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        return
    if layout == "Title Only":
        if not body.is_empty:
            raise UnsupportedContentError(
                "Title Only slides cannot contain body content.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        return
    if layout in {"Title Slide", "Section Header"}:
        if body.images or body.tables or body.videos:
            raise UnsupportedContentError(
                f"{layout} slides only support text-flow body content.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        return
    if layout in {"Title and Content", "Two Content"}:
        if body.has_text_flow and body.has_non_text:
            raise UnsupportedContentError(
                f"Each content area of a {layout} slide cannot mix text-flow blocks with images, tables, or videos.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        if len(body.images) + len(body.tables) + len(body.videos) > 1:
            raise UnsupportedContentError(
                f"Each content area of a {layout} slide may contain at most one non-text body object.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        return

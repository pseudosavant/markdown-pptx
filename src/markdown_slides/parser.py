from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from markdown_slides.assets import load_color_schemes
from markdown_slides.errors import ParseError, UnsupportedContentError
from markdown_slides.markdown_body import parse_body_markdown
from markdown_slides.models import (
    Background,
    BodyContent,
    ColorScheme,
    Deck,
    Fonts,
    GradientStop,
    Slide,
    TableOptions,
    TextColors,
    normalize_layout_name,
)

DOCUMENT_KEYS = {"aspect_ratio", "fonts", "color_scheme", "background", "title_color", "body_color"}
SLIDE_KEYS = {
    "master",
    "layout",
    "background",
    "title_color",
    "body_color",
    "hide_background_graphics",
    "notes",
    "table",
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
SETEXT_RE = re.compile(r"^\s*(=+|-+)\s*$")
ATX_H1_RE = re.compile(r"^#(?:\s+(.*)|\s*)$")
FENCE_OPEN_RE = re.compile(r"^[ ]{0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
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
    line_number: int
    config: dict[str, object]
    body_markdown: str


@dataclass(frozen=True, slots=True)
class FenceState:
    character: str
    length: int


def parse_deck(text: str, *, input_path: Path | None, source_name: str) -> Deck:
    lines = text.splitlines()
    document_config, slides = _split_source(lines, source_name=source_name)
    if not slides:
        raise ParseError("missing_slides", "The document must contain at least one '# H1' slide.")

    aspect_ratio = _parse_aspect_ratio(document_config)
    fonts, fonts_override = _parse_fonts(document_config)
    document_text_colors = _parse_text_colors(document_config, line=1)
    color_scheme = _parse_color_scheme(document_config)
    document_background = _parse_background(document_config.get("background"), line=1)

    parsed_slides: list[Slide] = []
    for slide_index, raw_slide in enumerate(slides, start=1):
        master = _parse_master_selector(
            raw_slide.config.get("master"),
            line=raw_slide.line_number,
            slide_index=slide_index,
            source_name=source_name,
        )
        layout = raw_slide.config.get("layout")
        if layout is not None and not isinstance(layout, str):
            raise ParseError(
                "invalid_slide_layout",
                "Slide layout must be a string.",
                line=raw_slide.line_number,
                slide_index=slide_index,
                input_path=source_name,
            )
        normalized_layout = normalize_layout_name(layout) if isinstance(layout, str) else None
        if normalized_layout is not None and normalized_layout not in SUPPORTED_LAYOUTS:
            raise ParseError(
                "unsupported_layout",
                f"Unsupported layout '{layout}'.",
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
        )
        slide_background = _parse_background(
            raw_slide.config.get("background"),
            line=raw_slide.line_number,
        )
        slide_text_colors = _parse_text_colors(raw_slide.config, line=raw_slide.line_number)
        _reject_setext(
            raw_slide.body_markdown.splitlines(), base_line=raw_slide.line_number + 1, source_name=source_name
        )
        body = parse_body_markdown(
            raw_slide.body_markdown,
            source_name=source_name,
            slide_index=slide_index,
            base_line=raw_slide.line_number + 1,
        )
        if normalized_layout is None:
            if raw_slide.title == "" and body.is_empty:
                normalized_layout = "Blank"
            else:
                normalized_layout = "Title and Content"
        _validate_layout_content(
            layout=normalized_layout,
            title=raw_slide.title,
            body=body,
            slide_index=slide_index,
            source_name=source_name,
            line=raw_slide.line_number,
        )
        if "table" in raw_slide.config and len(body.tables) != 1:
            raise UnsupportedContentError(
                "Slide table options require the slide body to contain exactly one table.",
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
    )


def _parse_table_options(
    value: object,
    *,
    configured: bool,
    line: int,
    slide_index: int,
    source_name: str,
) -> TableOptions:
    if not configured:
        return TableOptions()
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
    unknown = sorted(set(value) - set(TABLE_OPTION_DEFAULTS))
    if unknown:
        raise ParseError(
            "unknown_table_option_keys",
            f"Unknown table option key(s): {', '.join(unknown)}.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
    options = TABLE_OPTION_DEFAULTS | value
    invalid = [key for key, option in value.items() if not isinstance(option, bool)]
    if invalid:
        raise ParseError(
            "invalid_table_options",
            f"Table option(s) must be true or false: {', '.join(sorted(invalid))}.",
            line=line,
            slide_index=slide_index,
            input_path=source_name,
        )
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


def _split_source(lines: list[str], *, source_name: str) -> tuple[dict[str, object], list[RawSlide]]:
    index = 0
    document_config: dict[str, object] = {}
    if lines and lines[0].strip() == "---":
        document_config, index = _parse_yaml_front_matter(lines, 0, DOCUMENT_KEYS, source_name=source_name)

    slides: list[RawSlide] = []
    current_title: str | None = None
    current_line: int | None = None
    current_config: dict[str, object] = {}
    current_body: list[str] = []
    fence: FenceState | None = None

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        was_in_fence = fence is not None
        fence = _next_fence_state(line, fence)
        match = ATX_H1_RE.match(line) if not was_in_fence and fence is None else None
        if match:
            if current_title is not None:
                slides.append(
                    RawSlide(
                        title=current_title,
                        line_number=current_line or 1,
                        config=current_config,
                        body_markdown="\n".join(current_body).rstrip(),
                    )
                )
            current_title = (match.group(1) or "").strip()
            current_line = index + 1
            current_config = {}
            current_body = []
            index += 1
            if index < len(lines) and lines[index].strip() == "---":
                current_config, index = _parse_yaml_front_matter(lines, index, SLIDE_KEYS, source_name=source_name)
            continue
        if current_title is None:
            if stripped:
                raise ParseError(
                    "content_before_first_slide",
                    "Content is not allowed before the first '# H1' slide.",
                    line=index + 1,
                    input_path=source_name,
                )
        else:
            current_body.append(line)
        index += 1

    if current_title is not None:
        slides.append(
            RawSlide(
                title=current_title,
                line_number=current_line or 1,
                config=current_config,
                body_markdown="\n".join(current_body).rstrip(),
            )
        )
    return document_config, slides


def _parse_yaml_front_matter(
    lines: list[str],
    start_index: int,
    allowed_keys: set[str],
    *,
    source_name: str,
) -> tuple[dict[str, object], int]:
    end_index = start_index + 1
    while end_index < len(lines) and lines[end_index].strip() != "---":
        end_index += 1
    if end_index >= len(lines):
        raise ParseError(
            "unterminated_front_matter",
            "Front matter block is not terminated.",
            line=start_index + 1,
            input_path=source_name,
        )
    raw = "\n".join(lines[start_index + 1 : end_index])
    try:
        loaded = yaml.safe_load(raw) if raw.strip() else {}
    except yaml.YAMLError as exc:
        raise ParseError(
            "invalid_yaml", f"Invalid YAML front matter: {exc}", line=start_index + 1, input_path=source_name
        ) from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ParseError(
            "invalid_front_matter",
            "Front matter must decode to a mapping.",
            line=start_index + 1,
            input_path=source_name,
        )
    if any(not isinstance(key, str) for key in loaded):
        raise ParseError(
            "invalid_front_matter",
            "Front matter keys must be strings.",
            line=start_index + 1,
            input_path=source_name,
        )
    unknown = sorted(set(loaded) - allowed_keys)
    if unknown:
        raise ParseError(
            "unknown_front_matter_keys",
            f"Unknown front matter key(s): {', '.join(unknown)}.",
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


def _reject_setext(lines: list[str], *, base_line: int, source_name: str) -> None:
    fence: FenceState | None = None
    for index in range(len(lines) - 1):
        current = lines[index]
        next_line = lines[index + 1]
        was_in_fence = fence is not None
        fence = _next_fence_state(current, fence)
        if was_in_fence or fence is not None:
            continue
        if current.strip() and SETEXT_RE.match(next_line):
            raise ParseError(
                "setext_headings_unsupported",
                "Setext headings are not supported; use '#', '##', etc.",
                line=base_line + index,
                input_path=source_name,
            )


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
        if body.images or body.tables:
            raise UnsupportedContentError(
                f"{layout} slides only support text-flow body content.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        return
    if layout == "Title and Content":
        if body.has_text_flow and body.has_non_text:
            raise UnsupportedContentError(
                "A Title and Content slide cannot mix text-flow blocks with images or tables without synthesized text boxes.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        if len(body.images) > 1 or len(body.tables) > 1 or (body.images and body.tables):
            raise UnsupportedContentError(
                "A Title and Content slide may contain at most one non-text body object.",
                slide_index=slide_index,
                line=line,
                input_path=source_name,
            )
        return

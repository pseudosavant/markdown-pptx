"""Parse and merge constrained CSS-style media and table effects."""

from __future__ import annotations

import math
import re

import yaml

from markdown_slides.errors import ParseError
from markdown_slides.models import EffectBorder, EffectColor, EffectReflection, Effects, EffectShadow

EFFECT_COMMENT_RE = re.compile(r"^<!-- markdown-pptx:(?P<category>media_effects|table_effects)\b")
RESERVED_EFFECT_COMMENT_RE = re.compile(r"^<!-- markdown-pptx:(?:media_effects|table_effects|image|effects)\b")
MEDIA_EFFECT_KEYS = {"border", "border_radius", "shadow", "reflection"}
TABLE_EFFECT_KEYS = MEDIA_EFFECT_KEYS - {"border_radius"}
TABLE_COLOR_KEYS = {"header_fill", "row_fill", "banded_row_fill"}
LENGTH_RE = re.compile(r"^(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+))(?P<unit>pt|in|px)?$")
RGBA_RE = re.compile(r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d*(?:\.\d+)?)\s*\)$")
ALPHA_HEX_RE = re.compile(r"^#([0-9a-fA-F]{4}|[0-9a-fA-F]{8})$")


class _EffectsSettingsLoader(yaml.SafeLoader):
    def __init__(self, stream):
        self.source_lines = stream.splitlines()
        super().__init__(stream)

    def construct_mapping(self, node, deep=False):
        values = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, (str, int, float, bool, type(None))):
                raise yaml.constructor.ConstructorError(
                    None, None, "Setting keys must be scalars.", key_node.start_mark
                )
            if key in values:
                raise yaml.constructor.ConstructorError(None, None, f"Duplicate setting: {key}", key_node.start_mark)
            if key in MEDIA_EFFECT_KEYS | TABLE_COLOR_KEYS and isinstance(value_node, yaml.ScalarNode):
                if value_node.style is None and value_node.end_mark.line < len(self.source_lines):
                    tail = self.source_lines[value_node.end_mark.line][value_node.end_mark.column :]
                    if re.match(r"\s+#[0-9a-fA-F]{3,8}(?:\s|$)", tail):
                        raise yaml.constructor.ConstructorError(
                            None, None, "Quote the entire setting when it contains a hex color.", value_node.start_mark
                        )
            values[key] = self.construct_object(value_node, deep=deep)
        return values


def load_settings_yaml(source: str):
    return yaml.load(source, Loader=_EffectsSettingsLoader) if source.strip() else {}


def parse_effect_settings(
    comment: str, *, source_name: str, slide_index: int, line: int, category: str = "media_effects"
) -> Effects:
    def fail(message: str) -> ParseError:
        return ParseError(
            "invalid_effect_settings", message, input_path=source_name, slide_index=slide_index, line=line
        )

    lines = comment.splitlines()
    if len(lines) < 2 or lines[0].strip() != f"<!-- markdown-pptx:{category}" or lines[-1].strip() != "-->":
        raise fail("Effects comment must open and close on separate lines.")
    if any("-->" in value for value in lines[1:-1]):
        raise fail("Effects comment cannot contain an early closing marker.")
    try:
        data = load_settings_yaml("\n".join(lines[1:-1]))
    except yaml.YAMLError as exc:
        raise fail(f"Invalid effects settings: {exc}") from exc
    return parse_effect_values(data, category=category, source_name=source_name, slide_index=slide_index, line=line)


def parse_effect_values(
    data: object, *, category: str, source_name: str, line: int, slide_index: int | None = None
) -> Effects:
    def fail(message: str) -> ParseError:
        return ParseError(
            "invalid_effect_settings", message, input_path=source_name, slide_index=slide_index, line=line
        )

    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        raise fail(f"{category} must contain a mapping of effects.")
    if category == "table_effects" and "border_radius" in data:
        raise fail("border_radius is only supported in media_effects. Tables cannot have rounded corners.")
    allowed = MEDIA_EFFECT_KEYS if category == "media_effects" else TABLE_EFFECT_KEYS
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise fail(f"Unknown {category} setting: {', '.join(unknown)}.")
    if any(not isinstance(value, (str, int, float)) or isinstance(value, bool) for value in data.values()):
        raise fail("Effects must use CSS-style values. Quote values containing hex colors.")
    effects = Effects(specified={"border_radius_pt" if key == "border_radius" else key for key in data})
    try:
        if "border" in data:
            parts = _split_value(str(data["border"]))
            if parts != ["none"]:
                if len(parts) != 3 or parts[1] not in {"solid", "dashed", "dotted"}:
                    raise ValueError("border must be 'width solid|dashed|dotted color' or none.")
                effects.border = EffectBorder(_length(parts[0]), parts[1], _color(parts[2]))
        if "border_radius" in data:
            effects.border_radius_pt = _length(str(data["border_radius"]))
        if "shadow" in data:
            parts = _split_value(str(data["shadow"]))
            if parts != ["none"]:
                if not 2 <= len(parts) <= 4:
                    raise ValueError("shadow must be 'offset-x offset-y [blur] [color]' or none.")
                shadow = EffectShadow(_length(parts[0], signed=True), _length(parts[1], signed=True))
                remainder = parts[2:]
                if remainder and LENGTH_RE.fullmatch(remainder[0]):
                    shadow.blur_pt = _length(remainder.pop(0))
                if remainder:
                    if len(remainder) != 1:
                        raise ValueError("Only one outer shadow is supported, without spread or inset.")
                    shadow.color = _color(remainder[0])
                effects.shadow = shadow
        if "reflection" in data:
            parts = _split_value(str(data["reflection"]))
            if parts != ["none"]:
                if not 1 <= len(parts) <= 2:
                    raise ValueError("reflection must be 'distance [amount%]' or none.")
                reflection = EffectReflection(_length(parts[0]))
                if len(parts) == 2:
                    if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)%", parts[1]):
                        raise ValueError("Reflection amount must be a percentage greater than 0 and at most 100%.")
                    reflection.amount = float(parts[1][:-1]) / 100
                    if not 0 < reflection.amount <= 1:
                        raise ValueError("Reflection amount must be a percentage greater than 0 and at most 100%.")
                effects.reflection = reflection
    except (ValueError, ParseError) as exc:
        raise fail(str(exc)) from exc
    return effects


def merge_effects(*layers: Effects | None) -> Effects | None:
    merged = Effects()
    for layer in layers:
        if layer is not None:
            for name in layer.specified:
                setattr(merged, name, getattr(layer, name))
            merged.specified.update(layer.specified)
    return merged if merged.specified else None


def _split_value(value: str) -> list[str]:
    parts = []
    start = 0
    depth = 0
    for index, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if depth < 0:
            raise ValueError("Unbalanced parentheses in effect setting.")
        if char.isspace() and depth == 0:
            if index > start:
                parts.append(value[start:index])
            start = index + 1
    if depth:
        raise ValueError("Unbalanced parentheses in effect setting.")
    if start < len(value):
        parts.append(value[start:])
    return parts


def _length(value: str, *, signed: bool = False) -> float:
    match = LENGTH_RE.fullmatch(value)
    if match is None:
        raise ValueError("Effect lengths must use pt, in, or px. Unitless zero is also accepted.")
    number = float(match.group("number"))
    unit = match.group("unit")
    if not math.isfinite(number) or (unit is None and number != 0) or (not signed and number < 0):
        raise ValueError("Effect lengths must be nonnegative with explicit units, except signed shadow offsets.")
    return number * {"pt": 1, "in": 72, "px": 0.75, None: 1}[unit]


def _color(value: str) -> EffectColor:
    # The document parser imports the body parser. Resolve its shared color
    # validator at call time so effect colors use the same format contract.
    from markdown_slides.parser import _parse_color_expression

    rgba = RGBA_RE.fullmatch(value)
    if rgba:
        red, green, blue = (int(channel) for channel in rgba.groups()[:3])
        opacity = float(rgba.group(4))
        if max(red, green, blue) > 255 or not 0 <= opacity <= 1:
            raise ValueError("RGBA channels must be 0..255 and alpha must be 0..1.")
        return EffectColor(f"#{red:02X}{green:02X}{blue:02X}", opacity)
    alpha_hex = ALPHA_HEX_RE.fullmatch(value)
    if alpha_hex:
        raw = alpha_hex.group(1)
        if len(raw) == 4:
            raw = "".join(char * 2 for char in raw)
        return EffectColor(f"#{raw[:6].upper()}", int(raw[6:], 16) / 255)
    return EffectColor(_parse_color_expression(value))

"""Shared media and table placement inside native content placeholders."""

from __future__ import annotations

import math
import re

import yaml
from pptx.util import Inches

from markdown_slides.effect_settings import load_settings_yaml
from markdown_slides.errors import ParseError
from markdown_slides.models import ObjectLayout

LAYOUT_COMMENT_RE = re.compile(r"^<!-- markdown-pptx:(?P<category>media_layout|table_layout)\b")
MEDIA_LAYOUT_KEYS = {"width", "align", "valign"}
TABLE_LAYOUT_KEYS = {"width", "align"}
WIDTH_RE = re.compile(r"^(?:\d+(?:\.\d+)?)(?:%|in)$")


def parse_layout_values(data, *, category, source_name, line, slide_index=None) -> ObjectLayout:
    def fail(message):
        return ParseError(
            "invalid_layout_settings", message, input_path=source_name, line=line, slide_index=slide_index
        )

    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        raise fail(f"{category} must contain a mapping of settings.")
    allowed = MEDIA_LAYOUT_KEYS if category == "media_layout" else TABLE_LAYOUT_KEYS
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise fail(f"Unknown {category} setting: {', '.join(unknown)}.")
    width = data.get("width", "auto")
    if not isinstance(width, str) or (width != "auto" and not WIDTH_RE.fullmatch(width)):
        raise fail("Layout width must be auto, a percentage such as 50%, or inches such as 4in.")
    if width != "auto":
        value = float(width[:-1] if width.endswith("%") else width[:-2])
        if not math.isfinite(value) or value <= 0:
            raise fail("Layout width must be finite and greater than zero.")
    align = data.get("align", "center")
    valign = data.get("valign", "top")
    if not isinstance(align, str) or align not in {"left", "center", "right"}:
        raise fail("Layout align must be left, center, or right.")
    if not isinstance(valign, str) or valign not in {"top", "middle", "bottom"}:
        raise fail("Media layout valign must be top, middle, or bottom.")
    return ObjectLayout(width=width, align=align, valign=valign, specified=set(data))


def parse_layout_comment(comment, *, category, source_name, line, slide_index) -> ObjectLayout:
    def fail(message):
        return ParseError(
            "invalid_layout_settings", message, input_path=source_name, line=line, slide_index=slide_index
        )

    lines = comment.splitlines()
    if len(lines) < 2 or lines[0].strip() != f"<!-- markdown-pptx:{category}" or lines[-1].strip() != "-->":
        raise fail("Layout comment must open and close on separate lines.")
    if any("-->" in value for value in lines[1:-1]):
        raise fail("Layout comment cannot contain an early closing marker.")
    try:
        data = load_settings_yaml("\n".join(lines[1:-1]))
    except yaml.YAMLError as exc:
        raise fail(f"Invalid layout settings: {exc}") from exc
    return parse_layout_values(data, category=category, source_name=source_name, line=line, slide_index=slide_index)


def merge_layouts(*layers: ObjectLayout | None) -> ObjectLayout | None:
    result = ObjectLayout()
    for layer in layers:
        if layer is not None:
            for key in layer.specified:
                setattr(result, key, getattr(layer, key))
            result.specified.update(layer.specified)
    return result if result.specified else None


def requested_width(area_width: int, width: str) -> int:
    if width == "auto":
        return int(area_width)
    value = float(width[:-1] if width.endswith("%") else width[:-2])
    desired = area_width * (value / 100) if width.endswith("%") else value * Inches(1)
    return max(1, round(min(area_width, desired)))


def object_position(left, top, area_width, area_height, width, height, layout: ObjectLayout):
    horizontal = {"left": 0, "center": 0.5, "right": 1}[layout.align]
    vertical = {"top": 0, "middle": 0.5, "bottom": 1}[layout.valign]
    return int(left + (area_width - width) * horizontal), int(top + (area_height - height) * vertical)


def fit_media(left, top, area_width, area_height, aspect, layout: ObjectLayout):
    width = min(requested_width(area_width, layout.width), max(1, round(area_height * aspect)))
    height = max(1, min(int(area_height), round(width / aspect)))
    left, top = object_position(left, top, area_width, area_height, width, height, layout)
    return left, top, width, height

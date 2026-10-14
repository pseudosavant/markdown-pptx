"""Narrow adapters for native features missing from ps-python-pptx 1.3.0.

Keep XML access here until the library exposes content placeholder replacement,
slide visibility, picture geometry adjustments, effect opacity, outer shadows,
and reflections.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from copy import deepcopy

from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Pt

from markdown_slides.models import EffectColor, Effects


def replace_content_placeholder(placeholder, shape) -> None:
    """Replace an empty content placeholder while keeping its layout identity."""
    original = placeholder._element
    replacement = shape._element
    placeholder_properties = original.find(".//" + qn("p:ph"))
    non_visual_properties = replacement.find(".//" + qn("p:nvPr"))
    non_visual_properties.insert(0, deepcopy(placeholder_properties))
    original.addprevious(replacement)
    original.getparent().remove(original)


def set_slide_hidden(slide, hidden: bool) -> None:
    if hidden:
        slide._element.set("show", "0")
    else:
        slide._element.attrib.pop("show", None)


def apply_media_effects(picture, effects: Effects, *, set_color: Callable) -> None:
    if "border" in effects.specified:
        if effects.border is not None:
            border = effects.border
            picture.line.width = Pt(border.width_pt)
            picture.line.dash_style = {
                "solid": MSO_LINE_DASH_STYLE.SOLID,
                "dashed": MSO_LINE_DASH_STYLE.DASH,
                "dotted": MSO_LINE_DASH_STYLE.ROUND_DOT,
            }[border.style]
            set_color(picture.line.color, border.color.value)
            color_node = picture._element.spPr.ln.find(qn("a:solidFill"))[0]
            _alpha(color_node, border.color.opacity)
        else:
            picture.line.fill.background()

    if "border_radius_pt" in effects.specified:
        if hasattr(type(picture), "auto_shape_type"):
            picture.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if effects.border_radius_pt else MSO_SHAPE.RECTANGLE
        geometry = picture._element.spPr.find(qn("a:prstGeom"))
        if geometry is None:
            geometry = OxmlElement("a:prstGeom")
            picture._element.spPr.append(geometry)
        geometry.set("prst", "roundRect" if effects.border_radius_pt else "rect")
        adjustments = geometry.find(qn("a:avLst"))
        if adjustments is None:
            adjustments = OxmlElement("a:avLst")
            geometry.append(adjustments)
        for child in list(adjustments):
            adjustments.remove(child)
        if effects.border_radius_pt:
            adjustment = OxmlElement("a:gd")
            adjustment.set("name", "adj")
            fraction = min(0.5, Pt(effects.border_radius_pt) / min(picture.width, picture.height))
            adjustment.set("fmla", f"val {round(fraction * 100000)}")
            adjustments.append(adjustment)
    _apply_effect_list(picture._element.spPr, effects)


def apply_table_effects(shape, effects: Effects) -> None:
    table = shape._element.find(".//" + qn("a:tbl"))
    if "border" in effects.specified:
        rows = table.findall(qn("a:tr"))
        for row_index, row in enumerate(rows):
            cells = row.findall(qn("a:tc"))
            for column_index, cell in enumerate(cells):
                edges = []
                if column_index == 0:
                    edges.append("lnL")
                if column_index == len(cells) - 1:
                    edges.append("lnR")
                if row_index == 0:
                    edges.append("lnT")
                if row_index == len(rows) - 1:
                    edges.append("lnB")
                properties = cell.find(qn("a:tcPr"))
                for edge in edges:
                    old = properties.find(qn("a:" + edge))
                    if old is not None:
                        properties.remove(old)
                    line = OxmlElement("a:" + edge)
                    border = effects.border
                    line.set("w", str(Pt(border.width_pt)) if border else "0")
                    if border:
                        fill = OxmlElement("a:solidFill")
                        fill.append(_effect_color(border.color))
                        line.append(fill)
                        dash = OxmlElement("a:prstDash")
                        dash.set("val", {"solid": "solid", "dashed": "dash", "dotted": "sysDot"}[border.style])
                        line.append(dash)
                    else:
                        line.append(OxmlElement("a:noFill"))
                    order = ["lnL", "lnR", "lnT", "lnB", "lnTlToBr", "lnBlToTr"]
                    following = next(
                        (
                            node
                            for node in properties
                            if node.tag not in {qn("a:" + name) for name in order[: order.index(edge) + 1]}
                        ),
                        None,
                    )
                    if following is not None:
                        following.addprevious(line)
                    else:
                        properties.append(line)
    _apply_effect_list(table.find(qn("a:tblPr")), effects)


def _apply_effect_list(properties, effects: Effects) -> None:
    if not effects.specified & {"shadow", "reflection"}:
        return
    effect_list = properties.find(qn("a:effectLst"))
    if effect_list is None:
        effect_list = OxmlElement("a:effectLst")
        successors = {qn("a:tableStyle"), qn("a:tableStyleId"), qn("a:extLst")}
        following = next((node for node in properties if node.tag in successors), None)
        if following is not None:
            following.addprevious(effect_list)
        else:
            properties.append(effect_list)
    for name, tag in (("shadow", "outerShdw"), ("reflection", "reflection")):
        if name in effects.specified:
            for old in list(effect_list):
                if old.tag == qn("a:" + tag):
                    effect_list.remove(old)
    if "shadow" in effects.specified and effects.shadow is not None:
        shadow = effects.shadow
        element = OxmlElement("a:outerShdw")
        element.set("blurRad", str(Pt(shadow.blur_pt)))
        element.set("dist", str(Pt(math.hypot(shadow.offset_x_pt, shadow.offset_y_pt))))
        angle = math.degrees(math.atan2(shadow.offset_y_pt, shadow.offset_x_pt)) % 360
        element.set("dir", str(round(angle * 60000) % 21600000))
        element.set("algn", "ctr")
        element.set("rotWithShape", "0")
        element.append(_effect_color(shadow.color))
        effect_list.append(element)
    if "reflection" in effects.specified and effects.reflection is not None:
        reflection = effects.reflection
        element = OxmlElement("a:reflection")
        for key, value in {
            "blurRad": str(Pt(1)),
            "stA": "35000",
            "stPos": "0",
            "endA": "0",
            "endPos": str(round(reflection.amount * 100000)),
            "dist": str(Pt(reflection.distance_pt)),
            "dir": "5400000",
            "fadeDir": "5400000",
            "sy": "-100000",
            "algn": "bl",
            "rotWithShape": "0",
        }.items():
            element.set(key, value)
        effect_list.append(element)


def _effect_color(color: EffectColor):
    if color.value.startswith("var("):
        name = color.value[6:-1]
        value = {
            "dark-1": "dk1",
            "light-1": "lt1",
            "dark-2": "dk2",
            "light-2": "lt2",
            "hyperlink": "hlink",
            "followed-hyperlink": "folHlink",
        }.get(name, name.replace("-", ""))
        element = OxmlElement("a:schemeClr")
        element.set("val", value)
    else:
        element = OxmlElement("a:srgbClr")
        element.set("val", color.value[1:])
    _alpha(element, color.opacity)
    return element


def _alpha(element, opacity: float) -> None:
    if opacity != 1:
        alpha = OxmlElement("a:alpha")
        alpha.set("val", str(round(opacity * 100000)))
        element.append(alpha)

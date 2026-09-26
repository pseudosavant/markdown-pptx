"""Theme syntax colors and bounded background analysis. No PowerPoint internals."""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from itertools import pairwise

from PIL import Image
from pptx.enum.dml import MSO_THEME_COLOR
from pygments.token import Comment, Keyword, Literal, Name

CONTRAST_TARGET = 4.5
IMAGE_SAMPLE_SIZE = 256
GRADIENT_GRID_SIZE = 16
LINEAR_RGB = tuple(v / 3294.6 if v <= 10 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in range(256))


def luminance(rgb) -> float:
    return sum(weight * LINEAR_RGB[channel] for weight, channel in zip((0.2126, 0.7152, 0.0722), rgb, strict=True))


def contrast(first: float, second: float) -> float:
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def adjusted_rgb(rgb, brightness: float) -> tuple[int, int, int]:
    """Apply the HSL luminance adjustment used by ColorFormat.brightness."""
    h, light, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))
    light = light * (1 + brightness) if brightness < 0 else light * (1 - brightness) + brightness
    return tuple(round(channel * 255) for channel in colorsys.hls_to_rgb(h, light, saturation))


@dataclass(frozen=True)
class BackgroundRange:
    low: float
    high: float
    method: str
    samples: int

    def contrast(self, rgb) -> float:
        value = luminance(rgb)
        if self.low <= value <= self.high:
            return 1.0
        return min(contrast(value, self.low), contrast(value, self.high))


@dataclass(frozen=True)
class ThemeCodeColor:
    slot: MSO_THEME_COLOR
    brightness: float
    ratio: float


def fit_color(slot: MSO_THEME_COLOR, rgb, background: BackgroundRange, *, light: bool) -> ThemeCodeColor:
    ratio = background.contrast(rgb)
    # Enforce the selected polarity, even when a malformed theme puts a light color in Dark 1.
    correct_side = luminance(rgb) >= background.high if light else luminance(rgb) <= background.low
    if correct_side and ratio >= CONTRAST_TARGET:
        return ThemeCodeColor(slot, 0, ratio)
    direction = 1 if light else -1
    extreme = adjusted_rgb(rgb, direction)
    if background.contrast(extreme) < CONTRAST_TARGET:
        return ThemeCodeColor(slot, direction, background.contrast(extreme))
    # Search the same 1/100000 precision used by DrawingML luminance transforms.
    low, high = 0, 100000
    while high - low > 1:
        middle = (low + high) // 2
        candidate = adjusted_rgb(rgb, direction * middle / 100000)
        correct_side = luminance(candidate) >= background.high if light else luminance(candidate) <= background.low
        if correct_side and background.contrast(candidate) >= CONTRAST_TARGET:
            high = middle
        else:
            low = middle
    brightness = direction * high / 100000
    return ThemeCodeColor(slot, brightness, background.contrast(adjusted_rgb(rgb, brightness)))


def token_role(kind) -> str:
    if kind in Comment:
        return "comment"
    if kind in Keyword.Type or any(
        kind in family for family in (Name.Function, Name.Class, Name.Builtin, Name.Namespace, Name.Decorator)
    ):
        return "named"
    if kind in Literal or kind in Keyword.Constant:
        return "value"
    if kind in Keyword or kind in Name.Tag:
        return "keyword"
    if kind in Name.Attribute:
        return "named"
    return "base"


def make_palette(scheme, mode: str, background: BackgroundRange) -> dict[str, ThemeCodeColor]:
    light = mode == "theme-light"
    slots = {
        "base": MSO_THEME_COLOR.LIGHT_1 if light else MSO_THEME_COLOR.DARK_1,
        "keyword": MSO_THEME_COLOR.ACCENT_1,
        "value": MSO_THEME_COLOR.ACCENT_2,
        "named": MSO_THEME_COLOR.ACCENT_3,
    }
    result = {role: fit_color(slot, scheme[slot], background, light=light) for role, slot in slots.items()}
    result["comment"] = result["base"]
    return result


def solid_range(rgb) -> BackgroundRange:
    value = luminance(rgb)
    return BackgroundRange(value, value, "solid", 1)


def image_range(
    image: Image.Image, box: tuple[float, float, float, float], *, underlay=(255, 255, 255)
) -> BackgroundRange:
    """Nearest-neighbor samples retain local colors. Trim 1% at each histogram tail.

    Coordinates refer to the decoded image. The caller supplies the actual crop
    and opaque underlay. This estimates contrast, not every rendered pixel.
    """
    left, top, right, bottom = box
    box = (
        max(0, math.floor(left)),
        max(0, math.floor(top)),
        min(image.width, math.ceil(right)),
        min(image.height, math.ceil(bottom)),
    )
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError("code content area does not intersect the background image")
    width, height = box[2] - box[0], box[3] - box[1]
    scale = min(1, IMAGE_SAMPLE_SIZE / max(width, height))
    sample = image.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.NEAREST, box=box
    )
    if "A" in sample.getbands() or "transparency" in sample.info:
        layer = Image.new("RGBA", sample.size, (*underlay, 255))
        sample = Image.alpha_composite(layer, sample.convert("RGBA"))
    sample = sample.convert("RGB")
    histogram = [0] * 1024
    for frequency, (red, green, blue) in sample.getcolors(maxcolors=IMAGE_SAMPLE_SIZE**2):
        value = 0.2126 * LINEAR_RGB[red] + 0.7152 * LINEAR_RGB[green] + 0.0722 * LINEAR_RGB[blue]
        histogram[min(1023, int(value * 1024))] += frequency
    count = sample.width * sample.height
    trim = int(count * 0.01)
    cumulative = 0
    low = None
    high = 1023
    for index, frequency in enumerate(histogram):
        cumulative += frequency
        if low is None and cumulative > trim:
            low = index
        if cumulative >= count - trim:
            high = index
            break
    return BackgroundRange((low or 0) / 1024, min(1, (high + 1) / 1024), "image-percentiles", count)


def image_box(image_size, placement, region):
    """Map a slide rectangle to source pixels for a placed or stretched image."""
    x, y, width, height = placement
    left, top, region_width, region_height = region
    iw, ih = image_size
    return (
        (left - x) * iw / width,
        (top - y) * ih / height,
        (left + region_width - x) * iw / width,
        (top + region_height - y) * ih / height,
    )


def gradient_range(stops, *, angle: float, radial: bool, center, slide_size, region) -> BackgroundRange:
    """Estimate the generated background over a 16 by 16 grid including its edges."""
    width, height = slide_size
    left, top, rw, rh = region
    stops = sorted(stops, key=lambda stop: stop[0])
    if len(stops) < 2:
        raise ValueError("gradient needs at least two stops")
    dx, dy = math.cos(math.radians(angle)), -math.sin(math.radians(angle))
    start = min(0, width * dx) + min(0, height * dy)
    span = abs(width * dx) + abs(height * dy)
    values = []
    for row in range(GRADIENT_GRID_SIZE):
        for column in range(GRADIENT_GRID_SIZE):
            x, y = left + rw * column / (GRADIENT_GRID_SIZE - 1), top + rh * row / (GRADIENT_GRID_SIZE - 1)
            if radial:
                cx, cy = center
                radius = math.hypot(max(cx, 1 - cx), max(cy, 1 - cy))
                position = math.hypot(x / width - cx, y / height - cy) / radius
            else:
                position = (x * dx + y * dy - start) / span
            position = max(0, min(1, position))
            color = stops[0][1]
            for (p0, c0), (p1, c1) in pairwise(stops):
                if position < p0:
                    break
                if position >= p1:
                    color = c1
                    continue
                weight = (position - p0) / (p1 - p0)
                color = tuple(round(a + (b - a) * weight) for a, b in zip(c0, c1, strict=True))
                break
            values.append(luminance(color))
    return BackgroundRange(min(values), max(values), "gradient-grid", len(values))

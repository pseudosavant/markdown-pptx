"""Compare bounded range analysis with an average-only image baseline.

Run with `uv run python scripts/benchmark_code_colors.py`. Timings are medians
in milliseconds. Both paths use the same decoded image, crop, sample size,
and linear RGB luminance formula. Image decoding is measured separately.
"""

import io
import json
from statistics import median
from time import perf_counter

from PIL import Image

from markdown_slides.code_colors import LINEAR_RGB, gradient_range, image_range


def measure(function, count=21):
    function()
    times = []
    for _ in range(count):
        start = perf_counter()
        function()
        times.append((perf_counter() - start) * 1000)
    return median(times)


def average(image, box):
    width, height = box[2] - box[0], box[3] - box[1]
    scale = min(1, 256 / max(width, height))
    sample = image.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.NEAREST, box=box
    ).convert("RGB")
    return sum(
        count * (0.2126 * LINEAR_RGB[r] + 0.7152 * LINEAR_RGB[g] + 0.0722 * LINEAR_RGB[b])
        for count, (r, g, b) in sample.getcolors(65536)
    ) / (sample.width * sample.height)


def main():
    results = []
    # Deterministic, high-color image with light and dark detail.
    seed = Image.frombytes("RGB", (256, 256), bytes((i * 37 + i // 113) % 256 for i in range(256 * 256 * 3)))
    for size in ((1920, 1080), (3840, 2160)):
        image = seed.resize(size, Image.Resampling.BILINEAR)
        box = (size[0] // 20, size[1] // 5, size[0] * 19 // 20, size[1] * 9 // 10)
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")

        def decode(encoded=encoded):
            with Image.open(io.BytesIO(encoded.getvalue())) as opened:
                opened.load()

        simple = measure(lambda image=image, box=box: average(image, box))
        bounded = measure(lambda image=image, box=box: image_range(image, box))
        results.append(
            {
                "size": size,
                "decode_ms": round(measure(decode), 3),
                "average_ms": round(simple, 3),
                "range_ms": round(bounded, 3),
                "range_over_average": round(bounded / simple, 3),
            }
        )
    gradient = measure(
        lambda: gradient_range(
            [(0, (255, 255, 255)), (1, (200, 230, 250))],
            angle=135,
            radial=False,
            center=(0.5, 0.5),
            slide_size=(1920, 1080),
            region=(100, 220, 1700, 750),
        )
    )
    print(json.dumps({"images": results, "gradient_ms": round(gradient, 3)}, indent=2))


if __name__ == "__main__":
    main()

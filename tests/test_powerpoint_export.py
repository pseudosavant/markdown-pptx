from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from markdown_slides.errors import RenderError, UsageError
from markdown_slides.powerpoint_export import export_powerpoint_images, parse_slide_selection
from markdown_slides.powerpoint_worker import WorkerError, _perform_export


def test_parse_slide_selection_defaults_to_all_and_sorts_explicit_values() -> None:
    assert parse_slide_selection(None, slide_count=4) == [1, 2, 3, 4]
    assert parse_slide_selection("all", slide_count=3) == [1, 2, 3]
    assert parse_slide_selection("4, 1-2", slide_count=4) == [1, 2, 4]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "comma-separated"),
        ("1,,2", "comma-separated"),
        ("two", "comma-separated"),
        ("3-1", "descending"),
        ("0", "has 4 slide"),
        ("5", "has 4 slide"),
        ("1,1", "more than once"),
        ("1-2,2", "more than once"),
    ],
)
def test_parse_slide_selection_rejects_invalid_or_duplicate_values(value: str, message: str) -> None:
    with pytest.raises(UsageError, match=message):
        parse_slide_selection(value, slide_count=4)


def test_export_requires_windows_and_reports_retained_pptx(tmp_path: Path) -> None:
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"pptx")
    output_dir = tmp_path / "deck-images"

    with pytest.raises(RenderError) as raised:
        export_powerpoint_images(
            pptx,
            output_dir=output_dir,
            image_format="png",
            slide_numbers=[1],
            slide_count=1,
            platform="linux",
        )

    assert raised.value.context.code == "powerpoint_export_unavailable"
    assert raised.value.context.details == {
        "pptx_output": str(pptx),
        "image_directory": str(output_dir),
    }
    assert pptx.is_file()
    assert not output_dir.exists()


def test_export_publishes_selected_images_with_deterministic_names(tmp_path: Path) -> None:
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"pptx")
    output_dir = tmp_path / "previews"
    output_dir.mkdir()
    unrelated = output_dir / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")

    def fake_worker(request: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
        assert timeout_seconds == 90.0
        staging = Path(request["output_dir"])
        for item in request["slides"]:
            (staging / item["filename"]).write_bytes(f"slide {item['slide']}".encode())
        return {
            "ok": True,
            "width": request["width"],
            "height": 1080,
            "slides": request["slides"],
        }

    result = export_powerpoint_images(
        pptx,
        output_dir=output_dir,
        image_format="png",
        slide_numbers=[12, 1, 3],
        slide_count=12,
        width=1920,
        platform="win32",
        worker_runner=fake_worker,
    )

    assert result == {
        "backend": "powerpoint",
        "format": "png",
        "directory": str(output_dir),
        "width": 1920,
        "height": 1080,
        "slides": [
            {"slide": 1, "path": str(output_dir / "slide-001.png")},
            {"slide": 3, "path": str(output_dir / "slide-003.png")},
            {"slide": 12, "path": str(output_dir / "slide-012.png")},
        ],
    }
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert (output_dir / "slide-001.png").read_bytes() == b"slide 1"
    assert (output_dir / "slide-003.png").read_bytes() == b"slide 3"
    assert (output_dir / "slide-012.png").read_bytes() == b"slide 12"


def test_export_refuses_collisions_and_force_replaces_only_generated_files(tmp_path: Path) -> None:
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"pptx")
    output_dir = tmp_path / "previews"
    output_dir.mkdir()
    existing = output_dir / "slide-001.jpg"
    existing.write_bytes(b"old")
    unrelated = output_dir / "notes.txt"
    unrelated.write_text("keep", encoding="utf-8")
    worker_called = False

    def fake_worker(request: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
        nonlocal worker_called
        worker_called = True
        staging = Path(request["output_dir"])
        for item in request["slides"]:
            (staging / item["filename"]).write_bytes(b"new")
        return {"ok": True, "width": request["width"], "height": 1080, "slides": request["slides"]}

    with pytest.raises(RenderError) as raised:
        export_powerpoint_images(
            pptx,
            output_dir=output_dir,
            image_format="jpeg",
            slide_numbers=[1],
            slide_count=1,
            platform="win32",
            worker_runner=fake_worker,
        )
    assert raised.value.context.code == "image_output_exists"
    assert worker_called is False
    assert existing.read_bytes() == b"old"

    export_powerpoint_images(
        pptx,
        output_dir=output_dir,
        image_format="jpeg",
        slide_numbers=[1],
        slide_count=1,
        force=True,
        platform="win32",
        worker_runner=fake_worker,
    )

    assert existing.read_bytes() == b"new"
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_export_worker_failure_leaves_no_partial_images(tmp_path: Path) -> None:
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"pptx")
    output_dir = tmp_path / "previews"

    def failing_worker(request: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
        staging = Path(request["output_dir"])
        (staging / request["slides"][0]["filename"]).write_bytes(b"partial")
        raise RenderError("powerpoint_export_failed", "PowerPoint failed.")

    with pytest.raises(RenderError) as raised:
        export_powerpoint_images(
            pptx,
            output_dir=output_dir,
            image_format="png",
            slide_numbers=[1, 2],
            slide_count=2,
            platform="win32",
            worker_runner=failing_worker,
        )

    assert raised.value.context.code == "powerpoint_export_failed"
    assert raised.value.context.details is not None
    assert raised.value.context.details["pptx_output"] == str(pptx)
    assert not output_dir.exists()


class _FakeSlide:
    def __init__(self, number: int, *, fail: bool = False) -> None:
        self.number = number
        self.fail = fail
        self.calls: list[tuple[str, str, int, int]] = []

    def Export(self, filename: str, filter_name: str, width: int, height: int) -> None:
        self.calls.append((filename, filter_name, width, height))
        if self.fail:
            raise RuntimeError("export failed")
        Path(filename).write_bytes(f"image {self.number}".encode())


class _FakeSlides:
    def __init__(self, slides: list[_FakeSlide]) -> None:
        self._slides = slides
        self.Count = len(slides)

    def Item(self, number: int) -> _FakeSlide:
        return self._slides[number - 1]


class _FakePresentation:
    def __init__(self, slides: list[_FakeSlide]) -> None:
        self.Slides = _FakeSlides(slides)
        self.PageSetup = type("PageSetup", (), {"SlideWidth": 960.0, "SlideHeight": 540.0})()
        self.closed = False

    def Close(self) -> None:
        self.closed = True


class _FakePresentations:
    def __init__(self, presentation: _FakePresentation) -> None:
        self.presentation = presentation
        self.open_args: tuple[Any, ...] | None = None

    def Open(self, *args: Any) -> _FakePresentation:
        self.open_args = args
        return self.presentation


class _FakeApplication:
    def __init__(self, presentation: _FakePresentation) -> None:
        self.Presentations = _FakePresentations(presentation)
        self.DisplayAlerts: int | None = None
        self.AutomationSecurity: int | None = None
        self.quit = False

    def Quit(self) -> None:
        self.quit = True


def test_worker_exports_with_powerpoint_dimensions_and_cleans_up(tmp_path: Path) -> None:
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"pptx")
    staging = tmp_path / "staging"
    staging.mkdir()
    slides = [_FakeSlide(1), _FakeSlide(2)]
    presentation = _FakePresentation(slides)
    application = _FakeApplication(presentation)
    initialized: list[bool] = []
    uninitialized: list[bool] = []
    request = {
        "pptx_path": str(pptx),
        "output_dir": str(staging),
        "filter": "PNG",
        "width": 1600,
        "slides": [
            {"slide": 1, "filename": "slide-001.png"},
            {"slide": 2, "filename": "slide-002.png"},
        ],
    }

    result = _perform_export(
        request,
        create_application=lambda: application,
        co_initialize=lambda: initialized.append(True),
        co_uninitialize=lambda: uninitialized.append(True),
    )

    assert result == {"width": 1600, "height": 900, "slides": request["slides"]}
    assert application.Presentations.open_args == (str(pptx), True, False, False)
    assert slides[0].calls == [(str(staging / "slide-001.png"), "PNG", 1600, 900)]
    assert slides[1].calls == [(str(staging / "slide-002.png"), "PNG", 1600, 900)]
    assert presentation.closed is True
    assert application.quit is True
    assert initialized == [True]
    assert uninitialized == [True]


def test_worker_cleans_up_after_slide_export_failure(tmp_path: Path) -> None:
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"pptx")
    staging = tmp_path / "staging"
    staging.mkdir()
    presentation = _FakePresentation([_FakeSlide(1, fail=True)])
    application = _FakeApplication(presentation)
    uninitialized: list[bool] = []
    request = {
        "pptx_path": str(pptx),
        "output_dir": str(staging),
        "filter": "JPG",
        "width": 1000,
        "slides": [{"slide": 1, "filename": "slide-001.jpg"}],
    }

    with pytest.raises(WorkerError) as raised:
        _perform_export(
            request,
            create_application=lambda: application,
            co_initialize=lambda: None,
            co_uninitialize=lambda: uninitialized.append(True),
        )

    assert raised.value.code == "powerpoint_export_failed"
    assert presentation.closed is True
    assert application.quit is True
    assert uninitialized == [True]

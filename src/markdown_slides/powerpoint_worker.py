from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


class WorkerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def main() -> int:
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise WorkerError("powerpoint_worker_invalid_request", "PowerPoint export request must be a JSON object.")
        payload = _export_request(request)
        sys.stdout.write(json.dumps({"ok": True, **payload}))
        return 0
    except WorkerError as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": {"code": exc.code, "message": exc.message}}))
        return 1
    except Exception as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": {
                        "code": "powerpoint_worker_error",
                        "message": f"Unexpected PowerPoint worker error ({type(exc).__name__}).",
                    },
                }
            )
        )
        return 1


def _export_request(request: dict[str, Any]) -> dict[str, Any]:
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise WorkerError(
            "powerpoint_automation_unavailable",
            "Windows PowerPoint automation support is unavailable; reinstall markdown-pptx on Windows.",
        ) from exc

    return _perform_export(
        request,
        create_application=lambda: win32com.client.DispatchEx("PowerPoint.Application"),
        co_initialize=pythoncom.CoInitialize,
        co_uninitialize=pythoncom.CoUninitialize,
    )


def _perform_export(
    request: dict[str, Any],
    *,
    create_application: Callable[[], Any],
    co_initialize: Callable[[], None],
    co_uninitialize: Callable[[], None],
) -> dict[str, Any]:
    pptx_path, output_dir, filter_name, width, slides = _validate_request(request)
    application = None
    presentation = None
    active_error: BaseException | None = None
    cleanup_errors: list[str] = []
    co_initialize()
    try:
        try:
            application = create_application()
        except Exception as exc:
            code = "powerpoint_not_installed" if _is_class_not_registered(exc) else "powerpoint_start_failed"
            raise WorkerError(
                code,
                "Could not start desktop Microsoft PowerPoint. Ensure it is installed, licensed, and initialized "
                f"for the current Windows user ({type(exc).__name__}).",
            ) from exc

        try:
            application.DisplayAlerts = 1
        except Exception:
            pass
        try:
            application.AutomationSecurity = 3
        except Exception:
            pass

        try:
            presentation = application.Presentations.Open(str(pptx_path), True, False, False)
        except Exception as exc:
            raise WorkerError(
                "powerpoint_open_failed",
                f"Desktop PowerPoint could not open '{pptx_path}' ({type(exc).__name__}).",
            ) from exc

        slide_count = int(presentation.Slides.Count)
        invalid = [item["slide"] for item in slides if item["slide"] < 1 or item["slide"] > slide_count]
        if invalid:
            raise WorkerError(
                "invalid_slide_selection",
                f"Slide {invalid[0]} was requested, but PowerPoint opened a presentation with {slide_count} slide(s).",
            )
        slide_width = float(presentation.PageSetup.SlideWidth)
        slide_height = float(presentation.PageSetup.SlideHeight)
        if slide_width <= 0 or slide_height <= 0:
            raise WorkerError("powerpoint_invalid_page_size", "PowerPoint reported an invalid slide page size.")
        height = max(1, round(width * slide_height / slide_width))

        for item in slides:
            image_path = output_dir / item["filename"]
            try:
                presentation.Slides.Item(item["slide"]).Export(str(image_path), filter_name, width, height)
            except Exception as exc:
                raise WorkerError(
                    "powerpoint_export_failed",
                    f"Desktop PowerPoint could not export slide {item['slide']} ({type(exc).__name__}).",
                ) from exc
            if not image_path.is_file() or image_path.stat().st_size == 0:
                raise WorkerError(
                    "powerpoint_export_missing_file",
                    f"Desktop PowerPoint did not create the expected image for slide {item['slide']}.",
                )

        return {"width": width, "height": height, "slides": slides}
    except BaseException as exc:
        active_error = exc
        raise
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception as exc:
                cleanup_errors.append(f"presentation close failed ({type(exc).__name__})")
        if application is not None:
            try:
                application.Quit()
            except Exception as exc:
                cleanup_errors.append(f"PowerPoint quit failed ({type(exc).__name__})")
        presentation = None
        application = None
        co_uninitialize()
        if active_error is None and cleanup_errors:
            raise WorkerError("powerpoint_cleanup_failed", "; ".join(cleanup_errors).capitalize() + ".")


def _validate_request(request: dict[str, Any]) -> tuple[Path, Path, str, int, list[dict[str, Any]]]:
    pptx_path = Path(str(request.get("pptx_path", "")))
    output_dir = Path(str(request.get("output_dir", "")))
    filter_name = request.get("filter")
    width = request.get("width")
    slides = request.get("slides")
    if not pptx_path.is_file():
        raise WorkerError("powerpoint_output_not_found", f"PowerPoint file does not exist: {pptx_path}")
    if not output_dir.is_dir():
        raise WorkerError("image_output_not_directory", f"Image staging directory does not exist: {output_dir}")
    if filter_name not in {"PNG", "JPG"}:
        raise WorkerError("powerpoint_worker_invalid_request", "Image filter must be PNG or JPG.")
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise WorkerError("powerpoint_worker_invalid_request", "Image width must be a positive integer.")
    if not isinstance(slides, list) or not slides:
        raise WorkerError("powerpoint_worker_invalid_request", "At least one slide must be requested.")
    normalized: list[dict[str, Any]] = []
    for item in slides:
        if not isinstance(item, dict):
            raise WorkerError("powerpoint_worker_invalid_request", "Each requested slide must be an object.")
        number = item.get("slide")
        filename = item.get("filename")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise WorkerError("powerpoint_worker_invalid_request", "Requested slide numbers must be positive integers.")
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise WorkerError("powerpoint_worker_invalid_request", "Requested image filenames must be plain filenames.")
        normalized.append({"slide": number, "filename": filename})
    return pptx_path, output_dir, filter_name, width, normalized


def _is_class_not_registered(exc: Exception) -> bool:
    values = [str(exc)]
    values.extend(str(value) for value in getattr(exc, "args", ()))
    text = " ".join(values).lower()
    return "class not registered" in text or "-2147221164" in text or "0x80040154" in text


if __name__ == "__main__":
    raise SystemExit(main())

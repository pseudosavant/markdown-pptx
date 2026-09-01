from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from markdown_slides.errors import RenderError, UsageError

DEFAULT_IMAGE_WIDTH = 1920
MAX_IMAGE_WIDTH = 16384
IMAGE_FORMATS = {
    "png": {"filter": "PNG", "extension": ".png"},
    "jpeg": {"filter": "JPG", "extension": ".jpg"},
}

WorkerRunner = Callable[[dict[str, Any], float], dict[str, Any]]


def powerpoint_image_export_available(platform: str | None = None) -> bool:
    return (platform or sys.platform) == "win32"


def default_image_directory(pptx_path: Path) -> Path:
    return pptx_path.with_name(f"{pptx_path.stem}-images")


def parse_slide_selection(value: str | None, *, slide_count: int) -> list[int]:
    if slide_count < 1:
        raise UsageError("Cannot export images because the presentation contains no slides.")
    if value is None or value.strip().lower() == "all":
        return list(range(1, slide_count + 1))

    selected: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            raise UsageError("--slides must use a comma-separated 1-based list such as 1,3-5.")
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2 or not all(bound.isdigit() for bound in bounds):
                raise UsageError("--slides must use a comma-separated 1-based list such as 1,3-5.")
            start, end = (int(bound) for bound in bounds)
            if start > end:
                raise UsageError(f"--slides range '{part}' is descending; use {end}-{start} instead.")
            numbers = range(start, end + 1)
        elif part.isdigit():
            numbers = (int(part),)
        else:
            raise UsageError("--slides must use a comma-separated 1-based list such as 1,3-5.")

        for number in numbers:
            if number < 1 or number > slide_count:
                raise UsageError(f"--slides contains {number}, but the presentation has {slide_count} slide(s).")
            if number in selected:
                raise UsageError(f"--slides selects slide {number} more than once.")
            selected.add(number)

    return sorted(selected)


def export_powerpoint_images(
    pptx_path: Path,
    *,
    output_dir: Path,
    image_format: str,
    slide_numbers: list[int],
    slide_count: int,
    width: int = DEFAULT_IMAGE_WIDTH,
    force: bool = False,
    platform: str | None = None,
    worker_runner: WorkerRunner | None = None,
) -> dict[str, Any]:
    details = {"pptx_output": str(pptx_path), "image_directory": str(output_dir)}
    if not powerpoint_image_export_available(platform):
        raise RenderError(
            "powerpoint_export_unavailable",
            "Image export requires Windows and the desktop Microsoft PowerPoint application. "
            f"The PowerPoint file was still created at '{pptx_path}'.",
            details=details,
        )
    if image_format not in IMAGE_FORMATS:
        raise UsageError(f"Unsupported image format '{image_format}'. Choose png or jpeg.")
    if width < 1 or width > MAX_IMAGE_WIDTH:
        raise UsageError(f"--image-width must be between 1 and {MAX_IMAGE_WIDTH} pixels.")
    if not pptx_path.is_file():
        raise RenderError(
            "powerpoint_output_not_found",
            f"Cannot export images because the PowerPoint file does not exist: {pptx_path}",
            details=details,
        )
    if output_dir.exists() and not output_dir.is_dir():
        raise RenderError(
            "image_output_not_directory",
            f"Image output path is not a directory: {output_dir}",
            details=details,
        )

    expected = set(range(1, slide_count + 1))
    if not slide_numbers or any(number not in expected for number in slide_numbers):
        raise UsageError(f"Selected slides must be between 1 and {slide_count}.")
    if len(slide_numbers) != len(set(slide_numbers)):
        raise UsageError("Selected slides must not contain duplicates.")

    format_details = IMAGE_FORMATS[image_format]
    digits = max(3, len(str(slide_count)))
    planned = [
        {
            "slide": number,
            "filename": f"slide-{number:0{digits}d}{format_details['extension']}",
        }
        for number in sorted(slide_numbers)
    ]
    collisions = [output_dir / item["filename"] for item in planned if (output_dir / item["filename"]).exists()]
    non_files = [path for path in collisions if not path.is_file()]
    if non_files:
        raise RenderError(
            "image_output_not_file",
            f"Generated image path is not a file: {non_files[0]}",
            details=details,
        )
    if collisions and not force:
        raise RenderError(
            "image_output_exists",
            f"Image output already exists: {collisions[0]}; use --force to overwrite generated image files.",
            details=details,
        )

    try:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RenderError(
            "image_output_directory_error",
            f"Could not create image output parent directory '{output_dir.parent}': {exc}",
            details=details,
        ) from exc

    runner = worker_runner or _run_worker
    timeout_seconds = min(600.0, 60.0 + (10.0 * len(planned)))
    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}-", dir=output_dir.parent) as temp_name:
        staging_root = Path(temp_name)
        staging_dir = staging_root / "images"
        staging_dir.mkdir()
        request = {
            "pptx_path": str(pptx_path),
            "output_dir": str(staging_dir),
            "filter": format_details["filter"],
            "format": image_format,
            "width": width,
            "slides": planned,
        }
        try:
            payload = runner(request, timeout_seconds)
        except RenderError as exc:
            if exc.context.details is None:
                exc.context.details = details
            raise
        _validate_worker_result(payload, planned=planned, staging_dir=staging_dir, details=details)
        _publish_staged_images(
            staging_dir=staging_dir,
            staging_root=staging_root,
            output_dir=output_dir,
            planned=planned,
            details=details,
        )

    exported = [{"slide": item["slide"], "path": str(output_dir / item["filename"])} for item in planned]
    return {
        "backend": "powerpoint",
        "format": image_format,
        "directory": str(output_dir),
        "width": payload["width"],
        "height": payload["height"],
        "slides": exported,
    }


def _run_worker(request: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    command = [sys.executable, "-m", "markdown_slides.powerpoint_worker"]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            "powerpoint_export_timeout",
            f"PowerPoint image export did not finish within {round(timeout_seconds)} seconds.",
        ) from exc
    except OSError as exc:
        raise RenderError(
            "powerpoint_worker_start_failed",
            f"Could not start the PowerPoint image-export worker: {exc}",
        ) from exc

    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        stderr = completed.stderr.strip()
        suffix = f" Worker error: {stderr}" if stderr else ""
        raise RenderError(
            "powerpoint_worker_failed",
            f"PowerPoint image-export worker returned an invalid response.{suffix}",
        ) from exc
    if not isinstance(payload, dict):
        raise RenderError("powerpoint_worker_failed", "PowerPoint image-export worker returned an invalid response.")
    if completed.returncode != 0 or payload.get("ok") is not True:
        error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        code = str(error.get("code") or "powerpoint_export_failed")
        message = str(error.get("message") or "PowerPoint could not export the requested slide images.")
        raise RenderError(code, message)
    return payload


def _validate_worker_result(
    payload: dict[str, Any],
    *,
    planned: list[dict[str, Any]],
    staging_dir: Path,
    details: dict[str, str],
) -> None:
    if not isinstance(payload.get("width"), int) or not isinstance(payload.get("height"), int):
        raise RenderError(
            "powerpoint_worker_failed",
            "PowerPoint image-export worker did not report valid image dimensions.",
            details=details,
        )
    reported = payload.get("slides")
    if not isinstance(reported, list) or reported != planned:
        raise RenderError(
            "powerpoint_worker_failed",
            "PowerPoint image-export worker reported unexpected slide outputs.",
            details=details,
        )
    for item in planned:
        path = staging_dir / item["filename"]
        if not path.is_file() or path.stat().st_size == 0:
            raise RenderError(
                "powerpoint_export_missing_file",
                f"PowerPoint did not create the expected image for slide {item['slide']}.",
                details=details,
            )


def _publish_staged_images(
    *,
    staging_dir: Path,
    staging_root: Path,
    output_dir: Path,
    planned: list[dict[str, Any]],
    details: dict[str, str],
) -> None:
    output_existed = output_dir.exists()
    backup_dir = staging_root / "backups"
    moved_new: list[Path] = []
    backups: list[tuple[Path, Path]] = []
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir()
        for item in planned:
            destination = output_dir / item["filename"]
            if destination.exists():
                backup = backup_dir / item["filename"]
                destination.replace(backup)
                backups.append((backup, destination))
        for item in planned:
            source = staging_dir / item["filename"]
            destination = output_dir / item["filename"]
            source.replace(destination)
            moved_new.append(destination)
    except OSError as exc:
        for path in reversed(moved_new):
            path.unlink(missing_ok=True)
        for backup, destination in reversed(backups):
            if backup.exists():
                backup.replace(destination)
        if not output_existed:
            try:
                output_dir.rmdir()
            except OSError:
                pass
        raise RenderError(
            "image_output_write_error",
            f"Could not publish exported slide images to '{output_dir}': {exc}",
            details=details,
        ) from exc

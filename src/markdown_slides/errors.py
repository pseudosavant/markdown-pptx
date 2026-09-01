from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARSE = 3
EXIT_TEMPLATE = 4
EXIT_ASSET = 5
EXIT_UNSUPPORTED = 6
EXIT_RENDER = 7
EXIT_INTERNAL = 8


@dataclass(slots=True)
class ErrorContext:
    code: str
    message: str
    exit_code: int
    line: int | None = None
    slide_index: int | None = None
    input_path: str | None = None
    details: dict[str, Any] | None = None


class MarkdownSlidesError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        exit_code: int,
        line: int | None = None,
        slide_index: int | None = None,
        input_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.context = ErrorContext(
            code=code,
            message=message,
            exit_code=exit_code,
            line=line,
            slide_index=slide_index,
            input_path=input_path,
            details=details,
        )


class UsageError(MarkdownSlidesError):
    def __init__(self, message: str) -> None:
        super().__init__("usage_error", message, exit_code=EXIT_USAGE)


class InputError(MarkdownSlidesError):
    def __init__(self, code: str, message: str, *, input_path: str | None = None) -> None:
        super().__init__(code, message, exit_code=EXIT_USAGE, input_path=input_path)


class ParseError(MarkdownSlidesError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        slide_index: int | None = None,
        input_path: str | None = None,
        exit_code: int = EXIT_PARSE,
    ) -> None:
        super().__init__(
            code,
            message,
            exit_code=exit_code,
            line=line,
            slide_index=slide_index,
            input_path=input_path,
        )


class TemplateError(MarkdownSlidesError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, exit_code=EXIT_TEMPLATE)


class AssetError(MarkdownSlidesError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, exit_code=EXIT_ASSET)


class UnsupportedContentError(MarkdownSlidesError):
    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        slide_index: int | None = None,
        input_path: str | None = None,
    ) -> None:
        super().__init__(
            "unsupported_content",
            message,
            exit_code=EXIT_UNSUPPORTED,
            line=line,
            slide_index=slide_index,
            input_path=input_path,
        )


class RenderError(MarkdownSlidesError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, exit_code=EXIT_RENDER, details=details)

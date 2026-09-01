from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from markdown_slides import __version__
from markdown_slides.assets import default_template_path, list_color_scheme_names, load_syntax_payload
from markdown_slides.errors import EXIT_INTERNAL, InputError, MarkdownSlidesError, UsageError
from markdown_slides.models import Background, Deck
from markdown_slides.parser import parse_deck
from markdown_slides.powerpoint_export import (
    DEFAULT_IMAGE_WIDTH,
    MAX_IMAGE_WIDTH,
    default_image_directory,
    export_powerpoint_images,
    parse_slide_selection,
    powerpoint_image_export_available,
)
from markdown_slides.renderer import list_layout_details, list_master_details, render_pptx
from markdown_slides.skill import install_skill, remove_skill

PROGRAM_NAME = "markdown-pptx"
PROJECT_URL = "https://github.com/pseudosavant/markdown-pptx"
PROJECT_SUMMARY = "Render constrained Markdown slide decks to editable PowerPoint files."
PROJECT_LICENSE = "MIT"
EXIT_CODES = (
    (0, "success"),
    (2, "usage or input error"),
    (3, "Markdown or front-matter parse error"),
    (4, "template or layout error"),
    (5, "image or other asset error"),
    (6, "unsupported Markdown content"),
    (7, "PowerPoint rendering error"),
    (8, "unexpected internal error"),
)


class CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def build_parser(*, platform: str | None = None) -> argparse.ArgumentParser:
    parser = CliArgumentParser(
        prog=PROGRAM_NAME,
        description=PROJECT_SUMMARY,
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show the quick reference and exit.")
    parser.add_argument("input", nargs="?", help="Input Markdown path, or '-' for stdin.")
    parser.add_argument("output", nargs="?", help="Optional output .pptx path.")
    parser.add_argument("--input", dest="input_flag", help="Input Markdown path, or '-' for stdin.")
    parser.add_argument("--output", dest="output_flag", help="Output .pptx path.")
    parser.add_argument("--template", help="Template PPTX to use instead of the packaged default.")
    parser.add_argument(
        "--master",
        help="Default slide master: a 1-based index or exact unique master/theme name.",
    )
    parser.add_argument("--base-dir", help="Resolve relative assets from this directory when reading stdin.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated outputs.")
    parser.add_argument(
        "--ignore-document-colors",
        action="store_true",
        help="Keep template colors instead of document-level Markdown colors.",
    )
    parser.add_argument(
        "--ignore-slide-colors",
        action="store_true",
        help="Ignore slide-level Markdown color overrides.",
    )
    parser.add_argument(
        "--no-remote-images",
        action="store_true",
        help="Reject HTTP(S) image URLs instead of downloading them.",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output.")
    image_help = powerpoint_image_export_available(platform)
    parser.add_argument(
        "--export-images",
        choices=("png", "jpeg"),
        help="Export slides through desktop PowerPoint as png or jpeg." if image_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--image-dir",
        help="Directory for exported slide images." if image_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--slides",
        help="1-based slides to export, such as 1,3-5; defaults to all." if image_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--image-width",
        type=int,
        help=f"Export width in pixels; defaults to {DEFAULT_IMAGE_WIDTH}." if image_help else argparse.SUPPRESS,
    )
    parser.add_argument("--list-masters", action="store_true", help="List slide masters embedded in the template.")
    parser.add_argument("--list-layouts", action="store_true", help="List layouts on the selected template master.")
    parser.add_argument("--list-color-schemes", action="store_true", help="List built-in Office color schemes.")
    parser.add_argument("--syntax", action="store_true", help="Print the supported input syntax.")
    parser.add_argument("--about", action="store_true", help="Show project metadata and exit.")
    parser.add_argument("--version", action="store_true", help="Show the installed version and exit.")
    return parser


def build_root_help(*, platform: str | None = None) -> str:
    exit_lines = "\n".join(f"  {code}  {meaning}" for code, meaning in EXIT_CODES)
    image_section = ""
    if powerpoint_image_export_available(platform):
        image_section = f"""PowerPoint image export (Windows):
  --export-images FORMAT      Export slides as png or jpeg.
  --image-dir PATH            Directory for exported slide images.
  --slides RANGE              Export 1-based slides such as 1,3-5; default: all.
  --image-width PIXELS        Export width; default: {DEFAULT_IMAGE_WIDTH}.

"""
    return f"""{PROGRAM_NAME} {__version__}
{PROJECT_SUMMARY}

Usage:
  {PROGRAM_NAME} INPUT.md [OUTPUT.pptx] [OPTIONS]
  {PROGRAM_NAME} --input - --output OUTPUT.pptx --base-dir DIR [OPTIONS]

Happy path:
  {PROGRAM_NAME} deck.md
  {PROGRAM_NAME} deck.md out.pptx --template theme.pptx

Inspection:
  {PROGRAM_NAME} --syntax [--json]
  {PROGRAM_NAME} --list-color-schemes [--json]
  {PROGRAM_NAME} --list-masters [--template theme.pptx] [--json]
  {PROGRAM_NAME} --list-layouts [--template theme.pptx] [--master MASTER] [--json]

Agent skill:
  {PROGRAM_NAME} skill install [--skills-dir DIR] [--json]
  {PROGRAM_NAME} skill remove [--skills-dir DIR] [--force] [--json]

Common options:
  -h, --help                  Show this quick reference.
  --template PATH             Use a PowerPoint template.
  --master MASTER             Default to a 1-based master index or unique name.
  --force                     Overwrite existing generated outputs.
  --no-remote-images          Reject HTTP(S) images.
  --ignore-document-colors    Keep template document colors.
  --ignore-slide-colors       Keep template slide colors.
  --json                      Emit structured output.

{image_section}Metadata:
  {PROGRAM_NAME} --about
  {PROGRAM_NAME} --version

Exit codes:
{exit_lines}

Project: {PROJECT_URL}
License: {PROJECT_LICENSE}
"""


def build_about_text() -> str:
    return f"{PROGRAM_NAME} {__version__}\n{PROJECT_SUMMARY}\nProject: {PROJECT_URL}\nLicense: {PROJECT_LICENSE}\n"


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args_list = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in args_list

    try:
        if not args_list:
            stdout.write(build_root_help())
            return 0
        if "-h" in args_list or "--help" in args_list:
            if args_list[0] == "skill":
                stdout.write(build_skill_help())
            else:
                stdout.write(build_root_help())
            return 0
        if "--version" in args_list:
            if args_list != ["--version"]:
                raise UsageError("--version cannot be combined with other arguments.")
            stdout.write(f"{PROGRAM_NAME} {__version__}\n")
            return 0
        if "--about" in args_list:
            if args_list != ["--about"]:
                raise UsageError("--about cannot be combined with other arguments.")
            stdout.write(build_about_text())
            return 0
        if args_list[0] == "skill":
            return _run_skill_command(args_list[1:], stdout=stdout)

        args = build_parser().parse_args(args_list)
        return _run(args, stdin=stdin, stdout=stdout)
    except MarkdownSlidesError as exc:
        _write_error(exc, json_mode=json_mode, stdout=stdout, stderr=stderr)
        return exc.context.exit_code
    except KeyboardInterrupt:
        stderr.write("interrupted: operation cancelled\n")
        return 130
    except Exception as exc:
        message = f"unexpected {type(exc).__name__}: {exc}"
        if json_mode:
            stdout.write(
                json.dumps({"ok": False, "error": {"code": "internal_error", "message": message}}, indent=2) + "\n"
            )
        else:
            stderr.write(f"internal_error: {message}\n")
        return EXIT_INTERNAL


def build_skill_help() -> str:
    return f"""Usage:
  {PROGRAM_NAME} skill install [--skills-dir DIR] [--json]
  {PROGRAM_NAME} skill remove [--skills-dir DIR] [--force] [--json]

Install or remove the managed `{PROGRAM_NAME}` agent skill. The default skill root is
~/.agents/skills. Removal refuses unmanaged content unless --force is supplied.
"""


def _run_skill_command(args_list: list[str], *, stdout: TextIO) -> int:
    parser = CliArgumentParser(prog=f"{PROGRAM_NAME} skill", add_help=False)
    parser.add_argument("action", choices=("install", "remove"))
    parser.add_argument("--skills-dir", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(args_list)
    if args.action == "install" and args.force:
        raise UsageError("--force is valid only with 'skill remove'.")
    root = args.skills_dir.resolve() if args.skills_dir else None
    result = install_skill(root) if args.action == "install" else remove_skill(root, force=args.force)
    if args.json:
        stdout.write(json.dumps({"ok": True, "mode": f"skill_{args.action}", **result}, indent=2) + "\n")
    elif args.action == "install":
        if result["created"]:
            verb = "Installed"
        elif result["updated"]:
            verb = "Updated"
        else:
            verb = "Already installed"
        stdout.write(f"{verb} {result['path']}\n")
    elif result["removed"]:
        stdout.write(f"Removed {result['path']}\n")
    else:
        stdout.write(f"Skill is not installed at {result['path']}\n")
    return 0


def _run(args: argparse.Namespace, *, stdin: TextIO, stdout: TextIO) -> int:
    inspection_modes = {
        "list_masters": args.list_masters,
        "list_layouts": args.list_layouts,
        "list_color_schemes": args.list_color_schemes,
        "syntax": args.syntax,
    }
    selected = [name for name, enabled in inspection_modes.items() if enabled]
    if len(selected) > 1:
        raise UsageError("--list-masters, --list-layouts, --list-color-schemes, and --syntax are mutually exclusive.")

    if args.list_color_schemes:
        _validate_inspection_args(args, allowed={"json", "list_color_schemes"})
        names = list_color_scheme_names()
        _write_result({"ok": True, "mode": "list_color_schemes", "color_schemes": names}, names, args.json, stdout)
        return 0
    if args.syntax:
        _validate_inspection_args(args, allowed={"json", "syntax"})
        payload = load_syntax_payload()
        if args.json:
            stdout.write(json.dumps({"ok": True, "mode": "syntax", **payload}, indent=2) + "\n")
        else:
            stdout.write(_format_syntax(payload))
        return 0
    if args.list_masters:
        _validate_inspection_args(args, allowed={"json", "list_masters", "template"})
        template = Path(args.template).resolve() if args.template else default_template_path()
        masters = list_master_details(template)
        if args.json:
            stdout.write(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "list_masters",
                        "template": str(template),
                        "masters": masters,
                    },
                    indent=2,
                )
                + "\n"
            )
        else:
            stdout.write(
                "\n".join(
                    f"{item['index']}: {item['display_name']} ({item['layout_count']} layouts)" for item in masters
                )
                + "\n"
            )
        return 0
    if args.list_layouts:
        _validate_inspection_args(args, allowed={"json", "list_layouts", "template", "master"})
        template = Path(args.template).resolve() if args.template else default_template_path()
        details = list_layout_details(template, master=args.master)
        names = [layout["name"] for layout in details["layouts"]]
        if args.json:
            stdout.write(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "list_layouts",
                        "template": str(template),
                        "master": details["master"],
                        "layouts": names,
                        "layout_details": details["layouts"],
                    },
                    indent=2,
                )
                + "\n"
            )
        else:
            stdout.write("\n".join(names) + "\n")
        return 0

    input_arg = args.input_flag or args.input
    if args.input_flag and args.input:
        raise UsageError("Use either positional input or --input, not both.")
    output_arg = args.output_flag or args.output
    if args.output_flag and args.output:
        raise UsageError("Use either positional output or --output, not both.")
    if not input_arg:
        raise UsageError("An input Markdown file is required.")
    if input_arg == "-" and not output_arg:
        raise UsageError("--input - requires --output or a positional output path.")

    if input_arg == "-":
        if not args.base_dir:
            raise UsageError("stdin input requires --base-dir for resolving relative assets.")
        base_dir = Path(args.base_dir).resolve()
        if not base_dir.is_dir():
            raise InputError("invalid_base_dir", f"base directory does not exist: {base_dir}", input_path=str(base_dir))
        source_text = stdin.read()
        input_path = None
        source_name = "<stdin>"
    else:
        if args.base_dir:
            raise UsageError("--base-dir is valid only when reading from stdin.")
        input_path = Path(input_arg).resolve()
        source_text = _read_input_text(input_path)
        base_dir = input_path.parent
        source_name = str(input_path)

    output_path = (
        Path(output_arg).resolve()
        if output_arg
        else input_path.with_suffix(".pptx")
        if input_path is not None
        else Path("deck.pptx").resolve()
    )
    image_options = {
        "--image-dir": args.image_dir,
        "--slides": args.slides,
        "--image-width": args.image_width,
    }
    if args.export_images is None:
        orphaned = [name for name, value in image_options.items() if value is not None]
        if orphaned:
            raise UsageError(f"{', '.join(orphaned)} require --export-images png or --export-images jpeg.")
    if args.image_width is not None and not 1 <= args.image_width <= MAX_IMAGE_WIDTH:
        raise UsageError(f"--image-width must be between 1 and {MAX_IMAGE_WIDTH} pixels.")

    deck = parse_deck(source_text, input_path=input_path, source_name=source_name)
    deck = _apply_color_ignore_flags(
        deck,
        ignore_document_colors=args.ignore_document_colors,
        ignore_slide_colors=args.ignore_slide_colors,
    )
    template_path = Path(args.template).resolve() if args.template else None
    selected_slides = parse_slide_selection(args.slides, slide_count=len(deck.slides)) if args.export_images else None
    image_dir = (
        Path(args.image_dir).resolve()
        if args.image_dir
        else default_image_directory(output_path)
        if args.export_images
        else None
    )
    render_report: dict[str, object] = {}
    rendered_path = render_pptx(
        deck,
        output_path=output_path,
        template_path=template_path,
        force=args.force,
        base_dir=base_dir,
        allow_remote_images=not args.no_remote_images,
        master=args.master,
        report=render_report,
    )
    image_report = None
    if args.export_images:
        assert selected_slides is not None
        assert image_dir is not None
        image_report = export_powerpoint_images(
            rendered_path,
            output_dir=image_dir,
            image_format=args.export_images,
            slide_numbers=selected_slides,
            slide_count=len(deck.slides),
            width=args.image_width or DEFAULT_IMAGE_WIDTH,
            force=args.force,
        )
    if args.json:
        payload = {
            "ok": True,
            "mode": "render",
            "input": source_name,
            "output": str(rendered_path),
            "template": str(template_path or default_template_path()),
            "slides": len(deck.slides),
            "ignore_document_colors": args.ignore_document_colors,
            "ignore_slide_colors": args.ignore_slide_colors,
            "remote_images": not args.no_remote_images,
            **render_report,
        }
        if image_report is not None:
            payload["images"] = image_report
        stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        stdout.write(f"{rendered_path}\n")
        if image_report is not None:
            stdout.write(f"Exported {len(image_report['slides'])} slide image(s) to {image_report['directory']}\n")
    return 0


def _validate_inspection_args(args: argparse.Namespace, *, allowed: set[str]) -> None:
    ignored = {"help", "about", "version"}
    labels = {"input_flag": "--input", "output_flag": "--output", "input": "input", "output": "output"}
    conflicting: list[str] = []
    for name, value in vars(args).items():
        if name in allowed or name in ignored or value in (None, False):
            continue
        conflicting.append(labels.get(name, f"--{name.replace('_', '-')}"))
    if conflicting:
        mode = next(
            name for name in allowed if name in {"list_masters", "list_layouts", "list_color_schemes", "syntax"}
        )
        raise UsageError(f"--{mode.replace('_', '-')} cannot be combined with: {', '.join(conflicting)}")


def _read_input_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputError("input_not_found", f"input file does not exist: {path}", input_path=str(path)) from exc
    except IsADirectoryError as exc:
        raise InputError("input_not_file", f"input path is not a file: {path}", input_path=str(path)) from exc
    except UnicodeDecodeError as exc:
        raise InputError("input_not_utf8", f"input file is not valid UTF-8: {path}", input_path=str(path)) from exc
    except OSError as exc:
        raise InputError(
            "input_read_error", f"could not read input file '{path}': {exc}", input_path=str(path)
        ) from exc


def _write_result(payload: dict[str, object], lines: list[str], json_mode: bool, stdout: TextIO) -> None:
    if json_mode:
        stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        stdout.write("\n".join(lines) + "\n")


def _write_error(exc: MarkdownSlidesError, *, json_mode: bool, stdout: TextIO, stderr: TextIO) -> None:
    context = exc.context
    if json_mode:
        error = {
            "code": context.code,
            "message": context.message,
            "line": context.line,
            "slide_index": context.slide_index,
            "input": context.input_path,
        }
        if context.details is not None:
            error["details"] = context.details
        stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": error,
                },
                indent=2,
            )
            + "\n"
        )
        return
    stderr.write(f"{context.code}: {context.message}\n")


def _apply_color_ignore_flags(
    deck: Deck,
    *,
    ignore_document_colors: bool,
    ignore_slide_colors: bool,
) -> Deck:
    if not ignore_document_colors and not ignore_slide_colors:
        return deck
    document_background = deck.background
    if ignore_document_colors and _is_color_background(document_background):
        document_background = None
    slides = [
        replace(
            slide,
            text_colors=None if ignore_slide_colors else slide.text_colors,
            background=None if ignore_slide_colors and _is_color_background(slide.background) else slide.background,
        )
        for slide in deck.slides
    ]
    return replace(
        deck,
        text_colors=None if ignore_document_colors else deck.text_colors,
        color_scheme=None if ignore_document_colors else deck.color_scheme,
        background=document_background,
        slides=slides,
    )


def _is_color_background(background: Background | None) -> bool:
    return background is not None and background.kind != "image"


def _format_syntax(payload: dict[str, object]) -> str:
    color_scheme = payload["color_scheme_syntax"]
    table_options = payload["table_options"]
    lines = [
        "Document structure:",
        "  - Optional document front matter is allowed only at the top of the file.",
        "  - Each '# H1' starts a new slide.",
        "  - Optional slide front matter is allowed only immediately after an H1.",
        "  - Everything after the H1/front matter until the next H1 is the slide body.",
        "",
        f"Document front matter keys: {', '.join(payload['document_front_matter_keys'])}",
        f"aspect_ratio values: {', '.join(payload['aspect_ratio_values'])}",
        f"Slide front matter keys: {', '.join(payload['slide_front_matter_keys'])}",
        f"master selector: {payload['master_selector_syntax']}",
        f"layout values: {', '.join(payload['layout_values'])}",
        f"table options: {', '.join(table_options['defaults'])}",
        f"table option defaults: {json.dumps(table_options['defaults'])}",
        f"Supported markdown: {', '.join(payload['supported_markdown'])}",
        f"Unsupported markdown: {', '.join(payload['unsupported_markdown'])}",
        f"Theme color syntax: {payload['theme_color_syntax']}",
        f"Theme color variables: {', '.join(payload['theme_color_variables'])}",
        f"color_scheme preset example: {json.dumps(color_scheme['preset_example'])}",
        f"color_scheme custom keys: {', '.join(color_scheme['custom_keys'])}",
        "",
        "Example:",
        str(payload["example"]),
        "",
    ]
    return "\n".join(lines)

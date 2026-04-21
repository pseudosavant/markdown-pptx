from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from markdown_slides import __version__
from markdown_slides.assets import default_template_path, list_color_scheme_names, load_syntax_payload
from markdown_slides.errors import EXIT_INTERNAL, MarkdownSlidesError, UsageError
from markdown_slides.parser import parse_deck
from markdown_slides.renderer import list_layouts, render_pptx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md-to-pptx",
        description="Render constrained Markdown slide decks to editable PPTX.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Happy path:\n"
            "  md-to-pptx deck.md\n"
            "  md-to-pptx deck.md out.pptx\n"
            "  md-to-pptx --input deck.md --template theme.pptx\n"
            "\n"
            "Inspection:\n"
            "  md-to-pptx --syntax\n"
            "  md-to-pptx --list-color-schemes\n"
            "  md-to-pptx --list-layouts [--template theme.pptx]\n"
        ),
    )
    parser.add_argument("input", nargs="?", help="Input markdown path, or '-' for stdin.")
    parser.add_argument("output", nargs="?", help="Optional output .pptx path.")
    parser.add_argument("--input", dest="input_flag", help="Input markdown path, or '-' for stdin.")
    parser.add_argument("--output", dest="output_flag", help="Output .pptx path.")
    parser.add_argument("--template", help="Template PPTX to use instead of the packaged default.")
    parser.add_argument("--base-dir", help="Base directory for resolving relative assets when reading from stdin.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file.")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output.")
    parser.add_argument("--list-layouts", action="store_true", help="List available template layouts.")
    parser.add_argument("--list-color-schemes", action="store_true", help="List baked-in Office color schemes.")
    parser.add_argument("--syntax", action="store_true", help="Print the supported markdown/front-matter syntax.")
    parser.add_argument("--version", action="version", version=f"md-to-pptx {__version__}")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout=None, stderr=None) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--version" in args_list:
        stdout.write(f"md-to-pptx {__version__}\n")
        raise SystemExit(0)
    parser = build_parser()
    if not args_list:
        parser.print_help(stdout)
        return 0
    try:
        args = parser.parse_args(args_list)
        return _run(args, stdout=stdout, stderr=stderr)
    except MarkdownSlidesError as exc:
        _write_error(exc, json_mode="--json" in args_list, stdout=stdout, stderr=stderr)
        return exc.context.exit_code
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "mode": "internal_error", "error": {"code": "internal_error", "message": str(exc)}}
        if "--json" in args_list:
            stdout.write(json.dumps(payload, indent=2) + "\n")
        else:
            stderr.write(f"internal_error: {exc}\n")
        return EXIT_INTERNAL


def _run(args, *, stdout, stderr) -> int:
    mode_count = sum(bool(flag) for flag in (args.list_layouts, args.list_color_schemes, args.syntax))
    if mode_count > 1:
        raise UsageError("--list-layouts, --list-color-schemes, and --syntax are mutually exclusive.")
    if args.list_color_schemes:
        names = list_color_scheme_names()
        if args.json:
            stdout.write(json.dumps({"ok": True, "mode": "list_color_schemes", "color_schemes": names}, indent=2) + "\n")
        else:
            stdout.write("\n".join(names) + "\n")
        return 0
    if args.syntax:
        payload = load_syntax_payload()
        if args.json:
            stdout.write(json.dumps({"ok": True, "mode": "syntax", **payload}, indent=2) + "\n")
        else:
            stdout.write(_format_syntax(payload))
        return 0
    if args.list_layouts:
        if args.input or args.output or args.input_flag or args.output_flag:
            raise UsageError("--list-layouts cannot be combined with render arguments.")
        template = Path(args.template) if args.template else default_template_path()
        layouts = list_layouts(template)
        if args.json:
            stdout.write(json.dumps({"ok": True, "mode": "list_layouts", "template": str(template), "layouts": layouts}, indent=2) + "\n")
        else:
            stdout.write("\n".join(layouts) + "\n")
        return 0

    input_arg = args.input_flag or args.input
    if args.input_flag and args.input:
        raise UsageError("Use either positional input or --input, not both.")
    output_arg = args.output_flag or args.output
    if args.output_flag and args.output:
        raise UsageError("Use either positional output or --output, not both.")
    if not input_arg:
        raise UsageError("An input markdown file is required.")
    if input_arg == "-" and not output_arg:
        raise UsageError("--input - requires --output.")

    if input_arg == "-":
        source_text = sys.stdin.read()
        base_dir = Path(args.base_dir).resolve() if args.base_dir else None
        if base_dir is None:
            raise UsageError("--input - requires --base-dir for resolving relative assets.")
        input_path = None
        source_name = "<stdin>"
    else:
        input_path = Path(input_arg).resolve()
        source_text = input_path.read_text(encoding="utf-8")
        base_dir = input_path.parent
        source_name = str(input_path)
    output_path = Path(output_arg).resolve() if output_arg else Path(str((input_path or Path("deck")).with_suffix(".pptx"))).resolve()
    deck = parse_deck(source_text, input_path=input_path, source_name=source_name)
    rendered_path = render_pptx(
        deck,
        output_path=output_path,
        template_path=Path(args.template).resolve() if args.template else None,
        force=args.force,
        base_dir=base_dir,
    )
    if args.json:
        stdout.write(
            json.dumps(
                {
                    "ok": True,
                    "mode": "render",
                    "input": source_name,
                    "output": str(rendered_path),
                    "template": str(Path(args.template).resolve() if args.template else default_template_path()),
                    "slides": len(deck.slides),
                },
                indent=2,
            )
            + "\n"
        )
    else:
        stdout.write(f"{rendered_path}\n")
    return 0


def _write_error(exc: MarkdownSlidesError, *, json_mode: bool, stdout, stderr) -> None:
    context = exc.context
    if json_mode:
        stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": {
                        "code": context.code,
                        "message": context.message,
                        "line": context.line,
                        "slide_index": context.slide_index,
                        "input": context.input_path,
                    },
                },
                indent=2,
            )
            + "\n"
        )
        return
    stderr.write(f"{context.code}: {context.message}\n")


def _format_syntax(payload: dict[str, object]) -> str:
    color_scheme = payload["color_scheme_syntax"]
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
        f"layout values: {', '.join(payload['layout_values'])}",
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

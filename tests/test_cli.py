from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from markdown_slides import __version__
from markdown_slides.cli import build_parser, main


def test_no_args_prints_help() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert "md-to-pptx deck.md" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_version_flag_prints_version() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    with pytest.raises(SystemExit) as excinfo:
        main(["--version"], stdout=stdout, stderr=stderr)

    assert excinfo.value.code == 0
    assert stdout.getvalue() == f"md-to-pptx {__version__}\n"
    assert stderr.getvalue() == ""


def test_help_mentions_agent_friendly_modes() -> None:
    help_text = build_parser().format_help()
    assert "--list-layouts" in help_text
    assert "--list-color-schemes" in help_text
    assert "--syntax" in help_text
    assert "md-to-pptx deck.md" in help_text


def test_list_color_schemes_plain_output() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--list-color-schemes"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert "Office" in stdout.getvalue().splitlines()
    assert "Blue Warm" in stdout.getvalue().splitlines()
    assert stderr.getvalue() == ""


def test_list_color_schemes_json_output() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--list-color-schemes", "--json"], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["mode"] == "list_color_schemes"
    assert "Office" in payload["color_schemes"]
    assert stderr.getvalue() == ""


def test_syntax_json_output() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--syntax", "--json"], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["ok"] is True
    assert "document_front_matter_keys" in payload
    assert "slide_front_matter_keys" in payload
    assert payload["aspect_ratio_values"] == ["16:9", "4:3"]
    assert payload["layout_values"] == ["Title Slide", "Title and Content", "Section Header", "Title Only", "Blank"]
    assert payload["theme_color_syntax"] == (
        "Use var(--slot-name) in text colors and backgrounds, for example var(--accent-1) or var(--dark-1)."
    )
    assert payload["color_scheme_syntax"]["preset_example"] == {"preset": "Office"}
    assert payload["color_scheme_syntax"]["custom_keys"] == [
        "dark_1",
        "light_1",
        "dark_2",
        "light_2",
        "accent_1",
        "accent_2",
        "accent_3",
        "accent_4",
        "accent_5",
        "accent_6",
        "hyperlink",
        "followed_hyperlink",
    ]
    assert payload["theme_color_variables"] == [
        "var(--dark-1)",
        "var(--light-1)",
        "var(--dark-2)",
        "var(--light-2)",
        "var(--accent-1)",
        "var(--accent-2)",
        "var(--accent-3)",
        "var(--accent-4)",
        "var(--accent-5)",
        "var(--accent-6)",
        "var(--hyperlink)",
        "var(--followed-hyperlink)",
    ]
    assert stderr.getvalue() == ""


def test_syntax_plain_output_lists_all_theme_color_variables() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--syntax"], stdout=stdout, stderr=stderr)

    output = stdout.getvalue()
    assert exit_code == 0
    assert "aspect_ratio values: 16:9, 4:3" in output
    assert "layout values: Title Slide, Title and Content, Section Header, Title Only, Blank" in output
    assert "Theme color syntax:" in output
    assert "Theme color variables:" in output
    assert 'color_scheme preset example: {"preset": "Office"}' in output
    assert "color_scheme custom keys: dark_1, light_1, dark_2, light_2, accent_1, accent_2, accent_3, accent_4, accent_5, accent_6, hyperlink, followed_hyperlink" in output
    assert "var(--dark-1)" in output
    assert "var(--light-2)" in output
    assert "var(--accent-6)" in output
    assert "var(--hyperlink)" in output
    assert "var(--followed-hyperlink)" in output
    assert stderr.getvalue() == ""


def test_list_layouts_uses_default_template() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--list-layouts"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    layouts = stdout.getvalue().splitlines()
    assert "Title Slide" in layouts
    assert "Title and Content" in layouts
    assert "Blank" in layouts
    assert stderr.getvalue() == ""


def test_stdin_requires_output() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--input", "-"], stdout=stdout, stderr=stderr)

    assert exit_code == 2
    assert "--input - requires --output" in stderr.getvalue()


def test_positional_and_flag_input_are_mutually_exclusive(tmp_path: Path) -> None:
    deck = tmp_path / "deck.md"
    deck.write_text("# Title\n\nBody\n", encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(deck), "--input", str(deck)], stdout=stdout, stderr=stderr)

    assert exit_code == 2
    assert "Use either positional input or --input" in stderr.getvalue()


def test_render_prints_default_output_path(tmp_path: Path) -> None:
    deck = tmp_path / "myFavoriteSlides.md"
    deck.write_text("# Slide\n\nBody text.\n", encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(deck)], stdout=stdout, stderr=stderr)

    expected = str(deck.with_suffix(".pptx").resolve())
    assert exit_code == 0
    assert stdout.getvalue().strip() == expected
    assert Path(expected).exists()
    assert stderr.getvalue() == ""


def test_render_json_output(tmp_path: Path) -> None:
    deck = tmp_path / "deck.md"
    deck.write_text("# Slide\n\nBody text.\n", encoding="utf-8")
    output = tmp_path / "out.pptx"
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(deck), str(output), "--json"], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["mode"] == "render"
    assert payload["slides"] == 1
    assert Path(payload["output"]).exists()
    assert stderr.getvalue() == ""

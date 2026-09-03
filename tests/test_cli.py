from __future__ import annotations

import io
import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from markdown_slides import __version__, skill
from markdown_slides.assets import default_template_path
from markdown_slides.cli import _apply_color_ignore_flags, build_parser, build_root_help, main
from markdown_slides.errors import RenderError
from markdown_slides.parser import parse_deck


def test_no_args_prints_help() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert "markdown-pptx deck.md" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_version_flag_prints_version() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--version"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert stdout.getvalue() == f"markdown-pptx {__version__}\n"
    assert stderr.getvalue() == ""


def test_help_mentions_agent_friendly_modes() -> None:
    help_text = build_root_help()
    assert "--list-layouts" in help_text
    assert "--list-masters" in help_text
    assert "--master" in help_text
    assert "--list-color-schemes" in help_text
    assert "--syntax" in help_text
    assert "--ignore-document-colors" in help_text
    assert "--ignore-slide-colors" in help_text
    assert "skill install" in help_text
    assert "--no-remote-images" in help_text
    assert "markdown-pptx deck.md" in help_text


def test_help_shows_powerpoint_image_export_only_on_windows() -> None:
    windows_help = build_root_help(platform="win32")
    linux_help = build_root_help(platform="linux")
    macos_help = build_root_help(platform="darwin")

    assert "PowerPoint image export (Windows)" in windows_help
    assert "--export-images" in windows_help
    assert "--image-width" in windows_help
    assert "--export-images" not in linux_help
    assert "--export-images" not in macos_help


def test_non_windows_parser_accepts_hidden_image_export_options() -> None:
    parser = build_parser(platform="linux")

    args = parser.parse_args(["deck.md", "--export-images", "png", "--slides", "1,3-5"])

    assert args.export_images == "png"
    assert args.slides == "1,3-5"


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
    assert "master" in payload["slide_front_matter_keys"]
    assert "table" in payload["slide_front_matter_keys"]
    assert "1-based" in payload["master_selector_syntax"]
    assert payload["table_options"] == {
        "scope": "Slide-level options that require exactly one pipe table in the slide body.",
        "defaults": {
            "header_row": True,
            "total_row": False,
            "first_column": False,
            "last_column": False,
            "banded_rows": True,
            "banded_columns": False,
        },
    }
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
    assert "table options: header_row, total_row, first_column, last_column, banded_rows, banded_columns" in output
    assert 'table option defaults: {"header_row": true' in output
    assert "Theme color syntax:" in output
    assert "Theme color variables:" in output
    assert 'color_scheme preset example: {"preset": "Office"}' in output
    assert (
        "color_scheme custom keys: dark_1, light_1, dark_2, light_2, accent_1, accent_2, accent_3, accent_4, accent_5, accent_6, hyperlink, followed_hyperlink"
        in output
    )
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


def test_list_masters_describes_default_template() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--list-masters", "--json"], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["mode"] == "list_masters"
    assert payload["masters"][0]["index"] == 1
    assert payload["masters"][0]["theme_name"] == "Office Theme"
    assert payload["masters"][0]["layout_count"] >= 5
    assert stderr.getvalue() == ""


def test_list_layouts_json_describes_selected_master_and_compatibility() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--list-layouts", "--json"], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["master"]["index"] == 1
    assert payload["master"]["embedded_master_count"] >= 1
    title_and_content = next(item for item in payload["layout_details"] if item["name"] == "Title and Content")
    assert title_and_content["compatible"] is True
    assert {item["type"] for item in title_and_content["placeholders"]} >= {"title", "object"}
    two_content = next(item for item in payload["layout_details"] if item["name"] == "Two Content")
    assert two_content["compatible"] is False
    assert stderr.getvalue() == ""


def test_list_layouts_accepts_master_name() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(
        ["--list-layouts", "--master", "Office Theme", "--json"],
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["master"]["index"] == 1
    assert payload["master"]["display_name"] == "Office Theme"
    assert stderr.getvalue() == ""


def test_about_is_exact_mode() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    assert main(["--about"], stdout=stdout, stderr=stderr) == 0
    assert "github.com/pseudosavant/markdown-pptx" in stdout.getvalue()
    assert "License: MIT" in stdout.getvalue()
    assert stderr.getvalue() == ""

    stdout = io.StringIO()
    stderr = io.StringIO()
    assert main(["--about", "--json"], stdout=stdout, stderr=stderr) == 2
    assert "cannot be combined" in json.loads(stdout.getvalue())["error"]["message"]
    assert stderr.getvalue() == ""


def test_inspection_modes_reject_render_options() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(["--syntax", "--force"], stdout=stdout, stderr=stderr)

    assert exit_code == 2
    assert "--syntax cannot be combined with: --force" in stderr.getvalue()


def test_skill_install_and_remove(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(
        ["skill", "install", "--skills-dir", str(skills_dir), "--json"],
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    skill_file = skills_dir / "markdown-pptx" / "SKILL.md"
    assert exit_code == 0
    assert payload["installed"] is True
    assert payload["created"] is True
    assert payload["updated"] is False
    assert skill_file.is_file()
    skill_content = skill_file.read_text(encoding="utf-8")
    assert "managed-by: markdown-pptx" in skill_content
    assert "Always invoke the tool as `uvx markdown-pptx ...`" in skill_content
    assert "## Set A Deck-Wide Theme Palette" in skill_content
    assert "preset: null" in skill_content
    assert "## Style Tables With Slide Metadata" in skill_content
    assert "banded_columns: false" in skill_content
    assert "## Export Slide Images On Windows" in skill_content
    assert "uvx markdown-pptx deck.md deck.pptx --export-images png --json" in skill_content
    command_lines = [
        line.strip()
        for line in skill_content.splitlines()
        if line.strip().startswith(("markdown-pptx", "uvx markdown-pptx"))
    ]
    assert command_lines
    assert all(line.startswith("uvx markdown-pptx") for line in command_lines)

    stdout = io.StringIO()
    exit_code = main(
        ["skill", "install", "--skills-dir", str(skills_dir), "--json"],
        stdout=stdout,
        stderr=stderr,
    )
    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["created"] is False
    assert payload["updated"] is False

    skill_file.write_text("<!-- managed-by: markdown-pptx -->\noutdated\n", encoding="utf-8")
    stdout = io.StringIO()
    exit_code = main(
        ["skill", "install", "--skills-dir", str(skills_dir), "--json"],
        stdout=stdout,
        stderr=stderr,
    )
    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["created"] is False
    assert payload["updated"] is True
    updated_content = skill_file.read_text(encoding="utf-8")
    assert "## Style Tables With Slide Metadata" in updated_content
    assert "## Export Slide Images On Windows" in updated_content

    stdout = io.StringIO()
    exit_code = main(
        ["skill", "remove", "--skills-dir", str(skills_dir), "--json"],
        stdout=stdout,
        stderr=stderr,
    )
    assert exit_code == 0
    assert json.loads(stdout.getvalue())["removed"] is True
    assert not skill_file.parent.exists()


def test_skill_remove_refuses_unmanaged_directory(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "markdown-pptx"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("user content\n", encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(
        ["skill", "remove", "--skills-dir", str(tmp_path / "skills")],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert "not marked as managed" in stderr.getvalue()
    assert target.exists()


@pytest.fixture
def installed_older_skill(monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(skill, "is_local_development_build", lambda: False)
    with monkeypatch.context() as patch:
        patch.setattr(skill, "__version__", "1.0.0")
        result = skill.install_skill()
    return Path(result["path"])


@pytest.mark.parametrize(
    "args", [[], ["--help"], ["-h"], ["--version"], ["--about"], ["--syntax"], ["--list-layouts", "--json"]]
)
def test_normal_commands_synchronize_skills(installed_older_skill: Path, args: list[str]) -> None:
    stdout, stderr = io.StringIO(), io.StringIO()
    assert main(args, stdout=stdout, stderr=stderr) == 0
    assert installed_older_skill.read_text(encoding="utf-8") == skill.render_skill()
    assert "1.0.0 -> " + __version__ in stderr.getvalue()
    if "--json" in args:
        assert json.loads(stdout.getvalue())["ok"] is True


def test_render_synchronizes_skill(installed_older_skill: Path, tmp_path: Path) -> None:
    stdout, stderr = io.StringIO(), io.StringIO()
    output = tmp_path / "deck.pptx"
    assert (
        main(
            ["--input", "-", "--output", str(output), "--base-dir", str(tmp_path), "--json"],
            stdin=io.StringIO("# Slide\n\nBody\n"),
            stdout=stdout,
            stderr=stderr,
        )
        == 0
    )
    assert output.is_file()
    assert json.loads(stdout.getvalue())["ok"] is True
    assert installed_older_skill.read_text(encoding="utf-8") == skill.render_skill()
    assert "Updated managed skill" in stderr.getvalue()


@pytest.mark.parametrize("problem", ["filesystem", "yaml", "utf8", "altered"])
def test_sync_problem_does_not_break_primary_json(
    installed_older_skill: Path,
    monkeypatch: pytest.MonkeyPatch,
    problem: str,
) -> None:
    if problem == "filesystem":

        def fail(*args: object) -> None:
            raise PermissionError("simulated permission failure")

        monkeypatch.setattr(skill.os, "replace", fail)
    elif problem == "yaml":
        installed_older_skill.write_text("---\nmetadata: [\n---\n", encoding="utf-8")
    elif problem == "utf8":
        installed_older_skill.write_bytes(b"\xff")
    else:
        with installed_older_skill.open("a", encoding="utf-8") as stream:
            stream.write("User changes\n")
    before = installed_older_skill.read_bytes()
    stdout, stderr = io.StringIO(), io.StringIO()
    assert main(["--syntax", "--json"], stdout=stdout, stderr=stderr) == 0
    assert json.loads(stdout.getvalue())["ok"] is True
    assert installed_older_skill.read_bytes() == before
    assert stderr.getvalue()
    if problem == "altered":
        assert skill.FORCE_INSTALL_COMMAND in stderr.getvalue()


@pytest.mark.parametrize("args", [["install"], ["remove"], ["status"], ["--help"], ["install", "--help"], []])
def test_skill_commands_never_synchronize(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    def fail(**kwargs: object) -> None:
        pytest.fail("skill management must not invoke automatic synchronization")

    monkeypatch.setattr("markdown_slides.cli.synchronize_skill", fail)
    code = main(["skill", *args], stdout=io.StringIO(), stderr=io.StringIO())
    assert code == (2 if not args else 0)


def test_skill_status_json_is_read_only(installed_older_skill: Path) -> None:
    raw = installed_older_skill.read_bytes()
    mtime = installed_older_skill.stat().st_mtime_ns
    stdout, stderr = io.StringIO(), io.StringIO()
    assert main(["skill", "status", "--json"], stdout=stdout, stderr=stderr) == 0
    payload = json.loads(stdout.getvalue())
    assert payload == {
        "ok": True,
        "mode": "skill_status",
        "skill": "markdown-pptx",
        "path": str(installed_older_skill),
        "standard_location": True,
        "installed": True,
        "managed": True,
        "cli_version": __version__,
        "managed_version": "1.0.0",
        "version_relation": "older",
        "integrity": "valid",
        "automatic_sync_eligible": True,
        "local_development_build": False,
        "force_install_command": None,
    }
    assert installed_older_skill.read_bytes() == raw
    assert installed_older_skill.stat().st_mtime_ns == mtime
    assert stderr.getvalue() == ""


def test_skill_status_plain_reports_development_and_missing_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(skill, "is_local_development_build", lambda: True)
    custom = tmp_path / "custom"
    stdout = io.StringIO()
    assert main(["skill", "status", "--skills-dir", str(custom)], stdout=stdout, stderr=io.StringIO()) == 0
    text = stdout.getvalue()
    assert str(custom / "markdown-pptx" / "SKILL.md") in text
    assert "Installed: no" in text
    assert "Standard location: no" in text
    assert "Automatic synchronization eligible: no" in text
    assert "Automatic synchronization skipped for local development: yes" in text
    assert not custom.exists()


def test_force_install_cli_and_status_recommendation(installed_older_skill: Path) -> None:
    with installed_older_skill.open("a", encoding="utf-8") as stream:
        stream.write("User changes\n")
    stdout = io.StringIO()
    assert main(["skill", "status"], stdout=stdout, stderr=io.StringIO()) == 0
    assert "Integrity: altered" in stdout.getvalue()
    assert skill.FORCE_INSTALL_COMMAND in stdout.getvalue()
    stdout = io.StringIO()
    assert main(["skill", "install", "--json"], stdout=stdout, stderr=io.StringIO()) == 2
    assert json.loads(stdout.getvalue())["error"]["code"] == "usage_error"
    assert skill.FORCE_INSTALL_COMMAND in json.loads(stdout.getvalue())["error"]["message"]
    stdout = io.StringIO()
    assert main(["skill", "install", "--force", "--json"], stdout=stdout, stderr=io.StringIO()) == 0
    assert json.loads(stdout.getvalue())["updated"] is True
    assert installed_older_skill.read_text(encoding="utf-8") == skill.render_skill()


def test_status_force_is_usage_error() -> None:
    stdout = io.StringIO()
    assert main(["skill", "status", "--force", "--json"], stdout=stdout, stderr=io.StringIO()) == 2
    assert json.loads(stdout.getvalue())["error"]["code"] == "usage_error"


def test_skill_help_documents_lifecycle() -> None:
    stdout = io.StringIO()
    assert main(["skill", "--help"], stdout=stdout, stderr=io.StringIO()) == 0
    text = stdout.getvalue()
    assert "skill install [--skills-dir DIR] [--force] [--json]" in text
    assert "skill remove [--skills-dir DIR] [--force] [--json]" in text
    assert "skill status [--skills-dir DIR] [--json]" in text
    assert skill.FORCE_INSTALL_COMMAND in text
    assert "editable" in text and "Custom" in text and "stderr" in text


def test_missing_input_file_has_stable_json_error(tmp_path: Path) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(tmp_path / "missing.md"), "--json"], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue())
    assert exit_code == 2
    assert payload["error"]["code"] == "input_not_found"
    assert stderr.getvalue() == ""


def test_unsupported_markdown_has_stable_exit_code(tmp_path: Path) -> None:
    deck = tmp_path / "unsupported.md"
    deck.write_text("# Slide\n\n<span>raw HTML</span>\n", encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(deck), "--json"], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue())
    assert exit_code == 6
    assert payload["error"]["code"] == "unsupported_content"
    assert stderr.getvalue() == ""


def test_base_dir_is_only_valid_for_stdin(tmp_path: Path) -> None:
    deck = tmp_path / "deck.md"
    deck.write_text("# Slide\n\nBody\n", encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(deck), "--base-dir", str(tmp_path)], stdout=stdout, stderr=stderr)

    assert exit_code == 2
    assert "valid only when reading from stdin" in stderr.getvalue()


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
    assert payload["default_master"]["index"] == 1
    assert payload["retained_master_count"] == 1
    assert [item["index"] for item in payload["masters_used"]] == [1]
    assert payload["ignore_document_colors"] is False
    assert payload["ignore_slide_colors"] is False
    assert Path(payload["output"]).exists()
    assert stderr.getvalue() == ""


def test_image_options_require_export_images(tmp_path: Path) -> None:
    deck = tmp_path / "deck.md"
    deck.write_text("# Slide\n\nBody.\n", encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(deck), "--slides", "1"], stdout=stdout, stderr=stderr)

    assert exit_code == 2
    assert "--slides require --export-images" in stderr.getvalue()
    assert not deck.with_suffix(".pptx").exists()


def test_image_export_json_reports_selected_images(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    deck = tmp_path / "deck.md"
    deck.write_text("# First\n\nOne.\n\n# Second\n\nTwo.\n", encoding="utf-8")
    output = tmp_path / "deck.pptx"
    image_dir = tmp_path / "previews"
    stdout = io.StringIO()
    stderr = io.StringIO()

    def fake_export(pptx_path: Path, **kwargs: object) -> dict[str, object]:
        assert pptx_path == output
        assert pptx_path.is_file()
        assert kwargs["image_format"] == "png"
        assert kwargs["slide_numbers"] == [2]
        assert kwargs["slide_count"] == 2
        assert kwargs["width"] == 800
        assert kwargs["force"] is False
        return {
            "backend": "powerpoint",
            "format": "png",
            "directory": str(image_dir),
            "width": 800,
            "height": 450,
            "slides": [{"slide": 2, "path": str(image_dir / "slide-002.png")}],
        }

    monkeypatch.setattr("markdown_slides.cli.export_powerpoint_images", fake_export)
    exit_code = main(
        [
            str(deck),
            str(output),
            "--export-images",
            "png",
            "--image-dir",
            str(image_dir),
            "--slides",
            "2",
            "--image-width",
            "800",
            "--json",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["images"]["backend"] == "powerpoint"
    assert payload["images"]["slides"] == [{"slide": 2, "path": str(image_dir / "slide-002.png")}]
    assert stderr.getvalue() == ""


def test_image_export_failure_reports_retained_pptx_in_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    deck = tmp_path / "deck.md"
    deck.write_text("# Slide\n\nBody.\n", encoding="utf-8")
    output = tmp_path / "deck.pptx"
    stdout = io.StringIO()
    stderr = io.StringIO()

    def failing_export(pptx_path: Path, **kwargs: object) -> dict[str, object]:
        raise RenderError(
            "powerpoint_export_unavailable",
            "Image export requires Windows; the PPTX was retained.",
            details={"pptx_output": str(pptx_path), "image_directory": str(kwargs["output_dir"])},
        )

    monkeypatch.setattr("markdown_slides.cli.export_powerpoint_images", failing_export)
    exit_code = main(
        [str(deck), str(output), "--export-images", "png", "--json"],
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 7
    assert output.is_file()
    assert payload["error"]["code"] == "powerpoint_export_unavailable"
    assert payload["error"]["details"]["pptx_output"] == str(output)
    assert stderr.getvalue() == ""


def test_apply_color_ignore_flags_keeps_image_backgrounds() -> None:
    deck = parse_deck(
        """---
background: "linear-gradient(90deg, #112233 0%, #445566 100%)"
title_color: "#010203"
body_color: "#040506"
color_scheme:
  preset: Office
---

# Slide A
---
background: "url('./bg.png')"
title_color: "#111111"
body_color: "#222222"
---

Body

# Slide B
---
background: "#778899"
title_color: "#333333"
body_color: "#444444"
---

Body
""",
        input_path=Path("deck.md"),
        source_name="deck.md",
    )

    adjusted = _apply_color_ignore_flags(deck, ignore_document_colors=True, ignore_slide_colors=True)

    assert adjusted.color_scheme is None
    assert adjusted.text_colors is None
    assert adjusted.background is None
    assert adjusted.slides[0].background is not None
    assert adjusted.slides[0].background.kind == "image"
    assert adjusted.slides[0].text_colors is None
    assert adjusted.slides[1].background is None
    assert adjusted.slides[1].text_colors is None


def test_ignore_document_colors_preserves_template_theme_and_slide_overrides(tmp_path: Path) -> None:
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    template = tmp_path / "template.pptx"
    shutil.copyfile(default_template_path(), template)
    customized_template = tmp_path / "template-customized.pptx"
    with (
        zipfile.ZipFile(template, "r") as source,
        zipfile.ZipFile(customized_template, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "ppt/theme/theme1.xml":
                root = ET.fromstring(data)
                clr = root.find(".//a:clrScheme", ns)
                assert clr is not None
                clr.set("name", "Custom Template Theme")
                accent1 = clr.find("a:accent1", ns)
                assert accent1 is not None
                accent1[0].set("val", "ABCDEF")
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            target.writestr(info, data)

    deck = tmp_path / "deck.md"
    deck.write_text(
        """---
color_scheme:
  preset: Blue Warm
title_color: "#112233"
body_color: "#445566"
---

# Slide
---
layout: Title and Content
title_color: "#778899"
body_color: "#AABBCC"
---

Body
""",
        encoding="utf-8",
    )
    output = tmp_path / "out.pptx"
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(
        [str(deck), str(output), "--template", str(customized_template), "--ignore-document-colors"],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    with zipfile.ZipFile(output) as zf:
        theme = ET.fromstring(zf.read("ppt/theme/theme1.xml"))
        slide_xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
    clr = theme.find(".//a:clrScheme", ns)
    assert clr is not None
    assert clr.attrib["name"] == "Custom Template Theme"
    accent1 = clr.find("a:accent1", ns)
    assert accent1 is not None
    assert accent1[0].attrib["val"] == "ABCDEF"
    assert 'val="778899"' in slide_xml
    assert 'val="AABBCC"' in slide_xml
    assert 'val="112233"' not in slide_xml
    assert 'val="445566"' not in slide_xml
    assert stderr.getvalue() == ""


def test_ignore_slide_colors_keeps_document_colors(tmp_path: Path) -> None:
    deck = tmp_path / "deck.md"
    deck.write_text(
        """---
title_color: "#112233"
body_color: "#445566"
---

# Slide
---
layout: Title and Content
title_color: "#778899"
body_color: "#AABBCC"
---

Body
""",
        encoding="utf-8",
    )
    output = tmp_path / "out.pptx"
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(deck), str(output), "--ignore-slide-colors"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    with zipfile.ZipFile(output) as zf:
        slide_xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
    assert 'val="112233"' in slide_xml
    assert 'val="445566"' in slide_xml
    assert 'val="778899"' not in slide_xml
    assert 'val="AABBCC"' not in slide_xml
    assert stderr.getvalue() == ""

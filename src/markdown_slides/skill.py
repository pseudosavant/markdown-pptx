from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlsplit

import yaml
from packaging.version import InvalidVersion, Version
from yaml.nodes import MappingNode, Node, ScalarNode

from markdown_slides import __version__
from markdown_slides.errors import UsageError

SKILL_NAME = "markdown-pptx"
DISTRIBUTION_NAME = "markdown-pptx"
MANAGED_MARKER = "<!-- managed-by: markdown-pptx -->"
FORCE_INSTALL_COMMAND = "uvx markdown-pptx skill install --force"
_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")


_SKILL_TEMPLATE = f"""---
name: markdown-pptx
description: Create editable PowerPoint presentations from strict Markdown using `uvx markdown-pptx`. Use when the user asks an agentic tool to create, render, validate, or inspect a PowerPoint deck expressed as Markdown, or to work with markdown-pptx templates, layouts, colors, notes, images, or syntax.
metadata:
  managed-by: {DISTRIBUTION_NAME}
  managed-version: ""
  managed-content-sha256: ""
---

# Markdown PPTX

Use the published CLI through `uvx markdown-pptx`. It converts a strict Markdown and YAML format into editable PowerPoint files using real layouts and placeholders.

Always invoke the tool as `uvx markdown-pptx ...`. Do not assume that a bare `markdown-pptx` command is installed globally, and do not substitute another launcher unless the user explicitly asks for one. This applies to rendering, inspection, validation, metadata, and skill-management commands.

## Start With Inspection

When the format or template is unfamiliar, inspect it before writing the deck:

```text
uvx markdown-pptx --syntax
uvx markdown-pptx --list-color-schemes
uvx markdown-pptx --list-masters --template theme.pptx
uvx markdown-pptx --list-layouts --template theme.pptx
```

Use `--json` when programmatic inspection is more reliable. The renderer retains all slide masters in a supplied template. Master selectors are 1-based indices or exact unique master/theme names; prefer indices because names can be blank or duplicated.

## Create A Deck

Each `# H1` starts exactly one slide. Document front matter is allowed only at the beginning of the file, and slide front matter is allowed only immediately after its H1.

```text
uvx markdown-pptx deck.md deck.pptx --json
```

If no output path is supplied, the tool writes a `.pptx` beside the Markdown input. Prefer an explicit output path for agent workflows so the result is easy to report.

## Use Templates Carefully

Inspect the template layouts first, then use only compatible layout names reported by the CLI:

```text
uvx markdown-pptx --list-masters --template theme.pptx --json
uvx markdown-pptx --list-layouts --template theme.pptx --master 2 --json
uvx markdown-pptx deck.md deck.pptx --template theme.pptx --master 2 --json
```

The first embedded master is the default unless `--master` selects another. A slide can override that default with `master` in its front matter:

```text
# Financial summary
---
master: 2
layout: Title and Content
---
```

Selection precedence is slide `master`, CLI `--master`, then master `1`. Layout names are resolved only within the effective master. All embedded masters remain in the output so users can switch a slide's layout/master group later in PowerPoint.

Do not invent floating text boxes to compensate for missing or ambiguous placeholders. Correct the Markdown layout choice or template instead.

Use `--ignore-document-colors` or `--ignore-slide-colors` only when the template should control those colors.

## Set A Deck-Wide Theme Palette

Use document-level `color_scheme` to recolor theme-aware content throughout the output. Start from a preset and override selected slots, or set `preset: null` and provide all 12 PowerPoint theme colors for a fully custom palette:

```text
---
color_scheme:
  preset: Office
  dark_1: "#10263F"
  light_1: "#F9F9F9"
  accent_1: "#1D6FA8"
  accent_2: "#5AA9E6"
title_color: "var(--dark-1)"
body_color: "var(--dark-2)"
---
```

Theme-aware template objects and `var(--...)` references follow the resulting palette. Hard-coded RGB colors and embedded images do not. Inspect `--syntax` for all 12 keys and supported color formats.

## Style Tables With Slide Metadata

Keep pipe-table syntax standard and put PowerPoint table-style flags in the slide front matter. Use `table` only when the slide body contains exactly one table:

```text
# Quarterly summary
---
layout: Title and Content
table:
  header_row: true
  total_row: true
  first_column: true
  last_column: false
  banded_rows: true
  banded_columns: false
---

| Region | Revenue |
| --- | ---: |
| North | $50,000 |
| Total | $50,000 |
```

The defaults are `header_row: true`, `banded_rows: true`, and false for the other four options. These settings control native PowerPoint styling. They do not calculate totals, and disabling `header_row` does not change Markdown's syntactic header row.

## Images And Paths

Relative image paths resolve from the Markdown file's directory. For stdin, provide both an output path and `--base-dir`:

```text
uvx markdown-pptx --input - --output deck.pptx --base-dir ./assets
```

Remote images are downloaded during rendering. Add `--no-remote-images` for offline work or untrusted Markdown. Download remote assets separately and reference local files when deterministic builds matter.

## Export Slide Images On Windows

When running on Windows with desktop Microsoft PowerPoint installed, use PowerPoint itself to export previews after generating the editable PPTX:

```text
uvx markdown-pptx deck.md deck.pptx --export-images png --json
uvx markdown-pptx deck.md deck.pptx --export-images jpeg --slides 1,3-5 --image-width 1600 --json
```

Use `--image-dir DIR` to choose the destination; otherwise images go into `<pptx-name>-images`. PNG is preferred for slide text and diagrams. The slide selector is 1-based and accepts comma-separated numbers and ranges. Image export requires Windows, an interactive desktop session, and an installed, licensed, initialized PowerPoint application. Do not use these options on Linux or macOS, and do not treat the feature as a server-side or built-in PPTX renderer.

The editable PPTX is retained if PowerPoint image export fails. With `--json`, inspect `error.details.pptx_output` before reporting the partial result. Add `--force` only when replacement of the PPTX or colliding generated images is authorized; unrelated files in the image directory are preserved.

## Overwrite Safety

The CLI refuses to overwrite an existing output or colliding generated image. Add `--force` only when the user explicitly permits replacement or the output is a disposable generated artifact.

```text
uvx markdown-pptx deck.md deck.pptx --force --json
```

## Handle Results

Prefer `--json` and parse the response. On success, report the absolute output path and slide count. On failure, use the structured error code and message to correct the input; do not repeat the same failing command unchanged.

Useful discovery and metadata commands are:

```text
uvx markdown-pptx --help
uvx markdown-pptx --about
uvx markdown-pptx --version
```
"""


def default_skills_dir() -> Path:
    return Path.home() / ".agents" / "skills"


def skill_dir(skills_dir: Path | None = None) -> Path:
    return (skills_dir or default_skills_dir()) / SKILL_NAME


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _mapping(node: Node) -> dict[str, Node]:
    if not isinstance(node, MappingNode):
        raise ValueError("expected a YAML mapping")
    result: dict[str, Node] = {}
    for key, value in node.value:
        if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str" or key.value in result:
            raise ValueError("ambiguous YAML mapping keys")
        if value.start_mark.index < key.end_mark.index:
            raise ValueError("aliased lifecycle metadata is not supported")
        result[key.value] = value
    return result


def _front_matter(text: str) -> tuple[dict[str, Node], int]:
    # Node offsets let us replace only a scalar value without reserializing YAML.
    opening = re.match(r"\A\ufeff?---[ \t]*\n", text)
    if opening is None:
        return {}, 0
    offset = opening.end()
    end = re.search(r"^---[ \t]*(?:\n|$)", text[offset:], re.MULTILINE)
    if end is None:
        raise ValueError("unclosed skill front matter")
    root = yaml.compose(text[offset : offset + end.start()], Loader=yaml.SafeLoader)
    if root is None:
        return {}, offset
    fields = _mapping(root)
    return (_mapping(fields["metadata"]) if "metadata" in fields else {}), offset


def _string(node: Node | None) -> str | None:
    if isinstance(node, ScalarNode) and node.tag == "tag:yaml.org,2002:str":
        return node.value
    return None


def _replace_value(text: str, node: Node, offset: int, value: str) -> str:
    return text[: offset + node.start_mark.index] + value + text[offset + node.end_mark.index :]


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def render_skill() -> str:
    """Render the single bundled skill with the exact CLI version and its own hash."""
    text = _normalize(_SKILL_TEMPLATE)
    fields, offset = _front_matter(text)
    text = _replace_value(text, fields["managed-version"], offset, json.dumps(__version__))
    fields, offset = _front_matter(text)
    return _replace_value(text, fields["managed-content-sha256"], offset, json.dumps(_digest(text)))


def _integrity(text: str, fields: dict[str, Node], offset: int) -> str:
    node = fields.get("managed-content-sha256")
    if node is None:
        return "missing"
    stored = _string(node)
    if stored is None or not _HASH_PATTERN.fullmatch(stored):
        return "malformed"
    # Multiline scalars and aliases are not the canonical hash value representation.
    source = text[offset + node.start_mark.index : offset + node.end_mark.index]
    if node.start_mark.line != node.end_mark.line or source not in (stored, f'"{stored}"', f"'{stored}'"):
        return "malformed"
    empty = _replace_value(text, node, offset, '""')
    return "valid" if _digest(empty) == stored else "altered"


def _version(value: str | None) -> Version | None:
    if value is None:
        return None
    try:
        return Version(value)
    except InvalidVersion:
        return None


@dataclass(frozen=True)
class _SkillState:
    raw: bytes | None = None
    managed: bool = False
    version: str | None = None
    integrity: str = "not_applicable"

    def relation(self, running: Version | None) -> str | None:
        installed = _version("0" if self.integrity == "legacy" else self.version)
        if installed is None or running is None:
            return None
        return "older" if installed < running else "newer" if installed > running else "equal"

    def needs_update(self, running: Version | None) -> bool:
        return (
            self.managed
            and running is not None
            and (self.version is None or (self.relation(running) == "older" and self.integrity == "valid"))
        )


def _read_skill(skill_path: Path) -> _SkillState:
    if skill_path.is_symlink() or skill_path.parent.is_symlink():
        raise UsageError(f"refusing to manage symlinked skill '{skill_path}'.")
    if skill_path.parent.exists() and not skill_path.parent.is_dir():
        raise UsageError(f"expected a skill directory at '{skill_path.parent}'.")
    if skill_path.exists() and not skill_path.is_file():
        raise UsageError(f"expected a regular skill file at '{skill_path}'.")
    try:
        raw = skill_path.read_bytes()
    except FileNotFoundError:
        return _SkillState()
    text = _normalize(raw.decode("utf-8"))
    try:
        fields, offset = _front_matter(text)
    except (ValueError, yaml.YAMLError) as exc:
        raise UsageError(f"cannot parse skill front matter in '{skill_path}': {exc}") from exc
    legacy = MANAGED_MARKER in text
    managed = _string(fields["managed-by"]) == DISTRIBUTION_NAME if "managed-by" in fields else legacy
    if not managed:
        return _SkillState(raw=raw)
    version = _string(fields.get("managed-version"))
    if _version(version) is None:
        version = None
    integrity = _integrity(text, fields, offset)
    if legacy and "managed-version" not in fields:
        integrity = "legacy"
    return _SkillState(raw, True, version, integrity)


def is_local_development_build() -> bool:
    """Fail closed for unknown sources, source checkouts, and PEP 610 directory installs."""
    try:
        dist = metadata.distribution(DISTRIBUTION_NAME)
        module_path = Path(__file__).resolve()
        # A checkout can shadow a different installed distribution on sys.path.
        if Path(dist.locate_file("markdown_slides/skill.py")).resolve() != module_path:
            return True
        direct_url = dist.read_text("direct_url.json")
        if direct_url is None:
            # Older source installs can expose egg-info without PEP 610 metadata.
            package_root = module_path.parent.parent
            return (package_root / "pyproject.toml").is_file() or (
                package_root.name == "src" and (package_root.parent / "pyproject.toml").is_file()
            )
        source = json.loads(direct_url)
        if "dir_info" in source:
            return True
        url = urlsplit(source["url"])
        if url.scheme == "file":
            # Installing a built wheel is a normal installation, even from a local archive.
            return not (url.path.lower().endswith(".whl") and isinstance(source.get("archive_info"), dict))
        return not bool(url.scheme)
    except (metadata.PackageNotFoundError, OSError, ValueError, KeyError, TypeError):
        return True


def _force_recommendation(skills_dir: Path | None = None) -> str:
    command = FORCE_INSTALL_COMMAND
    if skills_dir is not None:
        command += f' --skills-dir "{skills_dir}"'
    return command


def skill_status(skills_dir: Path | None = None) -> dict[str, Any]:
    """Inspect skill lifecycle state without creating or changing any files."""
    path = skill_dir(skills_dir) / "SKILL.md"
    state = _read_skill(path)
    local = is_local_development_build()
    standard = path == skill_dir() / "SKILL.md"
    running = _version(__version__)
    unverifiable = (
        state.managed
        and state.version is not None
        and state.integrity != "valid"
        and state.relation(running) != "newer"
    )
    return {
        "skill": SKILL_NAME,
        "path": str(path),
        "standard_location": standard,
        "installed": state.raw is not None,
        "managed": state.managed,
        "cli_version": __version__,
        "managed_version": state.version,
        "version_relation": state.relation(running),
        "integrity": state.integrity,
        "automatic_sync_eligible": standard and not local and state.needs_update(running),
        "local_development_build": local,
        "force_install_command": _force_recommendation(skills_dir) if unverifiable else None,
    }


def _atomic_write(skill_path: Path, text: str, expected: bytes | None) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=skill_path.parent,
            prefix=".SKILL.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        # Re-read after staging. A changed, removed, or newer skill cancels this write.
        if _read_skill(skill_path).raw != expected:
            raise UsageError(f"skill changed during installation at '{skill_path}'. Retry the command.")
        os.replace(temporary, skill_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def install_skill(skills_dir: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    target = skill_dir(skills_dir)
    skill_path = target / "SKILL.md"
    state = _read_skill(skill_path)
    existed = state.raw is not None
    if target.exists() and not existed:
        raise UsageError(f"refusing to install into '{target}' because it contains no managed SKILL.md.")
    if existed and not state.managed:
        raise UsageError(f"refusing to overwrite unmanaged skill file '{skill_path}'.")
    running = _version(__version__)
    relation = state.relation(running)
    # Force permits restoring managed edits, but never downgrading a known newer version.
    if relation != "newer" and state.version is not None and state.integrity != "valid" and not force:
        raise UsageError(
            f"refusing to overwrite altered or unverifiable managed skill '{skill_path}'. "
            f"Use `{_force_recommendation(skills_dir)}` to replace it."
        )
    text = render_skill()
    replace = not existed or state.version is None or (relation != "newer" and (force or relation == "older"))
    updated = replace and existed and state.raw != text.encode("utf-8")
    if replace and (not existed or updated):
        target.mkdir(parents=True, exist_ok=True)
        _atomic_write(skill_path, text, state.raw)
    return {
        "installed": True,
        "created": not existed,
        "updated": updated,
        "skill": SKILL_NAME,
        "path": str(skill_path),
    }


def _notice(stderr: TextIO, message: str) -> None:
    try:
        stderr.write(message + "\n")
    except Exception:
        pass  # Maintenance must not fail the primary command, even with a closed stderr.


def synchronize_skill(*, stderr: TextIO) -> None:
    """Best-effort local maintenance of an already installed standard skill."""
    try:
        running = _version(__version__)
        if running is None or is_local_development_build():
            return
        path = skill_dir() / "SKILL.md"
        state = _read_skill(path)
        if state.needs_update(running):
            _atomic_write(path, render_skill(), state.raw)
            old = state.version or ("0 (legacy)" if state.integrity == "legacy" else "unknown")
            _notice(stderr, f"Updated managed skill {old} -> {__version__} at {path}")
        elif state.managed and state.relation(running) == "older" and state.integrity != "valid":
            _notice(stderr, f"Preserved altered or unverifiable skill at {path}. Use `{FORCE_INSTALL_COMMAND}`.")
    except Exception as exc:
        _notice(
            stderr, f"Skill synchronization skipped: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}"
        )


def remove_skill(skills_dir: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    target = skill_dir(skills_dir)
    skill_path = target / "SKILL.md"
    if not target.exists():
        return {
            "removed": False,
            "skill": SKILL_NAME,
            "path": str(target),
            "reason": "not_installed",
        }
    if not skill_path.exists():
        raise UsageError(f"refusing to remove '{target}' because SKILL.md is missing.")
    if not force and not _read_skill(skill_path).managed:
        raise UsageError(
            f"refusing to remove '{target}' because it is not marked as managed by markdown-pptx. "
            "use --force to override."
        )
    extra_paths = [path for path in target.iterdir() if path.name != "SKILL.md"]
    if extra_paths and not force:
        names = ", ".join(sorted(path.name for path in extra_paths))
        raise UsageError(
            f"refusing to remove '{target}' because it contains unmanaged entries: {names}. Use --force to override."
        )
    shutil.rmtree(target)
    return {"removed": True, "skill": SKILL_NAME, "path": str(target)}

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from markdown_slides.errors import UsageError

SKILL_NAME = "markdown-pptx"
MANAGED_MARKER = "<!-- managed-by: markdown-pptx -->"


SKILL_MD = f"""---
name: markdown-pptx
description: Create editable PowerPoint presentations from strict Markdown using `uvx markdown-pptx`. Use when the user asks an agentic tool to create, render, validate, or inspect a PowerPoint deck expressed as Markdown, or to work with markdown-pptx templates, layouts, colors, notes, images, or syntax.
---

{MANAGED_MARKER}

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

## Overwrite Safety

The CLI refuses to overwrite an existing output. Add `--force` only when the user explicitly permits replacement or the output is a disposable generated artifact.

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


def install_skill(skills_dir: Path | None = None) -> dict[str, Any]:
    target = skill_dir(skills_dir)
    skill_path = target / "SKILL.md"
    if target.exists() and not skill_path.exists():
        raise UsageError(f"refusing to install into '{target}' because it contains no managed SKILL.md.")
    if skill_path.exists() and MANAGED_MARKER not in skill_path.read_text(encoding="utf-8"):
        raise UsageError(f"refusing to overwrite unmanaged skill file '{skill_path}'.")
    target.mkdir(parents=True, exist_ok=True)
    existed = skill_path.exists()
    previous = skill_path.read_text(encoding="utf-8") if existed else ""
    updated = existed and previous != SKILL_MD
    skill_path.write_text(SKILL_MD, encoding="utf-8", newline="\n")
    return {
        "installed": True,
        "created": not existed,
        "updated": updated,
        "skill": SKILL_NAME,
        "path": str(skill_path),
    }


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
    content = skill_path.read_text(encoding="utf-8")
    if MANAGED_MARKER not in content and not force:
        raise UsageError(
            f"refusing to remove '{target}' because it is not marked as managed by markdown-pptx; "
            "use --force to override."
        )
    extra_paths = [path for path in target.iterdir() if path.name != "SKILL.md"]
    if extra_paths and not force:
        names = ", ".join(sorted(path.name for path in extra_paths))
        raise UsageError(
            f"refusing to remove '{target}' because it contains unmanaged entries: {names}; use --force to override."
        )
    shutil.rmtree(target)
    return {"removed": True, "skill": SKILL_NAME, "path": str(target)}

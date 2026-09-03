# markdown-pptx

`markdown-pptx` turns constrained Markdown into editable PowerPoint `.pptx` presentations built from real PowerPoint layouts and placeholders. It is a strict, predictable CLI designed for both people and coding agents.

## Prerequisite

`markdown-pptx` is designed to be used with [`uv`](https://docs.astral.sh/uv/getting-started/installation/). Install `uv` before continuing. The documented workflows and managed agent skill use `uvx` to run the tool without requiring a global installation.

## Quick start with an agent

Install the managed agent skill:

```powershell
uvx markdown-pptx skill install
```

Then use `$markdown-pptx` in Codex, Claude Code, or another agent harness that supports skills:

> Use $markdown-pptx to create a seven-slide presentation about our product launch. Use a clear narrative, include speaker notes, and save both the Markdown source and editable PowerPoint deck.

The skill teaches the agent how to inspect the format and templates, write valid slide Markdown, render the deck, and handle the result.

## Manage the agent skill

The standard location is `~/.agents/skills/markdown-pptx/SKILL.md`. Normal invocations of an installed CLI, including help and version output, automatically synchronize an already-installed managed skill to the running CLI version. Missing and unmanaged skills are left alone. Skill-management commands skip this automatic check.

Synchronization is local only. It does not query a package index, refresh uv's cache, or update the CLI. The running CLI version is the authority. PEP 440 version comparison prevents downgrades and leaves equal versions unchanged. The skill continues to instruct agents to use `uvx markdown-pptx`.

Each generated `SKILL.md` stores lifecycle data in its YAML `metadata` mapping:

```yaml
metadata:
  managed-by: markdown-pptx
  managed-version: "1.3.0"
  managed-content-sha256: "sha256:<64 lowercase hexadecimal characters>"
```

The version above is illustrative. The generated value exactly matches `uvx markdown-pptx --version`. The SHA-256 hash covers the entire UTF-8 file with LF line endings and only the hash value replaced by `""`. Verification preserves the original YAML formatting and normalizes CRLF and CR line endings. This detects modifications. It is not a signature or security boundary. No sidecar files are used.

An older managed skill updates only when its own stored hash verifies. Modified files and valid-version files with missing or malformed hashes are preserved. The legacy HTML managed marker remains recognized. Legacy skills without a version migrate as version 0. Managed skills with missing or invalid version metadata receive a fresh replacement as a recovery step, without hash verification. A conflicting `managed-by` value always prevents replacement.

Inspect the path, ownership, versions, integrity, and automatic synchronization eligibility without changing anything:

```powershell
uvx markdown-pptx skill status
uvx markdown-pptx skill status --json
```

A normal explicit install creates a missing skill or updates a pristine older one. It refuses to overwrite modified or unverifiable managed content with valid version metadata. To restore the bundled skill and discard those edits:

```powershell
uvx markdown-pptx skill install --force
```

Install-time `--force` still refuses unmanaged skills and never downgrades a newer version. Removal accepts current and legacy managed skills. Its existing `--force` option also permits removing unmanaged content and extra files in the selected skill directory:

```powershell
uvx markdown-pptx skill remove
```

All three commands accept `--skills-dir PATH`. Custom locations require explicit updates because normal CLI invocations inspect only the standard location. Local source checkouts, local direct-source installs, and editable builds do not synchronize automatically. Unidentifiable installation origins are skipped conservatively. An installed wheel remains eligible. Explicit commands such as `uvx --from . markdown-pptx skill install` still work during development.

Automatic replacements are atomic and recheck the installed file before replacement. Maintenance failures do not change the primary command's exit status. Update notices and preservation warnings go to stderr, so documented JSON results on stdout stay valid. Changes affect future agent skill loading and may not change instructions already loaded into a running agent session.

## What it creates

Markdown stays readable, while the generated presentation remains easy to edit in PowerPoint.

![Rendered PowerPoint slide example](https://github.com/user-attachments/assets/99859d77-ca0b-4f4c-9dee-ac2be729a0e9)

## Use the CLI directly

Render a deck without installing the package globally:

```powershell
uvx markdown-pptx deck.md deck.pptx
```

Inspect the supported format or the layouts in the default template:

```powershell
uvx markdown-pptx --syntax
uvx markdown-pptx --list-layouts
```

To install the command as a persistent tool instead:

```powershell
uv tool install markdown-pptx
```

The examples below continue to use `uvx markdown-pptx` so they work without a global installation.

## How the format works

The document model has four core rules:

1. Optional document front matter may appear only at the beginning of the file.
2. Each `# H1` starts exactly one slide.
3. Optional slide front matter may appear only immediately after its H1.
4. Everything until the next H1 belongs to that slide.

A minimal two-slide deck looks like this:

```markdown
# Quarterly review
---
layout: Title Slide
---

Acme Corporation

# Highlights
---
layout: Title and Content
---

- Revenue grew 18%
- Customer retention reached 94%
- Two new products launched
```

Render it with:

```powershell
uvx markdown-pptx deck.md deck.pptx
```

If no `--template` is provided, the packaged default template is used.

## Use a PowerPoint template

Inspect a template before writing the deck, then use only the layouts it provides:

```powershell
uvx markdown-pptx --list-masters --template theme.pptx
uvx markdown-pptx --list-layouts --template theme.pptx --master 2
uvx markdown-pptx deck.md deck.pptx --template theme.pptx --master 2
```

All embedded slide masters are retained in the output. This keeps every layout group available in PowerPoint after the deck is generated.

The effective master is selected in this order:

1. The slide-level `master` value
2. The CLI `--master` option
3. The first embedded master

Master selectors may be 1-based indices or exact unique master or theme names. Indices are the most reliable choice because template names can be blank or duplicated. Layout names are resolved only within the effective master.

The renderer uses real placeholders for slide titles and bodies. Missing placeholders, duplicate layout names, and ambiguous placeholder mappings are errors. It does not invent free-positioned text boxes to compensate for an incompatible template.

## Customize a deck

Document front matter sets deck-wide defaults:

| Key | Purpose |
| --- | --- |
| `aspect_ratio` | Select `16:9` or `4:3` |
| `fonts` | Set body and heading fonts |
| `color_scheme` | Start from a preset or define PowerPoint theme colors |
| `background` | Set a solid color, gradient, image, or no background |
| `title_color` | Set the default title color |
| `body_color` | Set the default body and subtitle color |

Slide front matter controls an individual slide:

| Key | Purpose |
| --- | --- |
| `master` | Override the default slide master |
| `layout` | Select a layout from the effective master |
| `background` | Override the document background |
| `title_color` | Override the document title color |
| `body_color` | Override the document body color |
| `hide_background_graphics` | Hide inherited master graphics |
| `notes` | Add speaker notes to the PowerPoint notes pane |
| `table` | Set native PowerPoint table-style flags |

Run `uvx markdown-pptx --syntax` for the complete schema, accepted values, and examples.

### Theme colors

Use `color_scheme` to recolor theme-aware template content throughout the presentation:

```yaml
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

Colors accept hex, RGB, HSL, and PowerPoint theme references such as `var(--accent-1)`. Set `preset: null` and provide all 12 theme slots for a fully custom palette. Theme-aware template objects follow the resulting palette, while hard-coded RGB colors and images do not.

When a template should provide the colors, use `--ignore-document-colors`, `--ignore-slide-colors`, or both. These options do not change images, layouts, or content.

### Tables

Write standard Markdown pipe tables and put PowerPoint styling options in slide front matter:

```markdown
# Quarterly summary
---
layout: Title and Content
table:
  header_row: true
  total_row: true
  first_column: true
  banded_rows: true
---

| Region | Revenue |
| --- | ---: |
| North | $50,000 |
| Total | $50,000 |
```

Table flags control native PowerPoint styling. They do not calculate totals or change the Markdown table structure. A slide may use `table` metadata only when its body contains exactly one table.

### Images and paths

Local image paths are resolved relative to the Markdown file. Remote HTTP and HTTPS images are enabled by default. Use `--no-remote-images` for offline builds or untrusted Markdown. Download assets ahead of time and use local paths when reproducible builds matter.

When reading Markdown from stdin, provide an output path and a base directory for relative assets:

```powershell
uvx markdown-pptx --input - --output deck.pptx --base-dir ./assets
```

## Layouts and supported content

The built-in template provides these common layouts. Supplied templates may use different names and placeholders.

| Layout | Body behavior |
| --- | --- |
| `Title Slide` | Body text is placed in the subtitle placeholder |
| `Section Header` | Body text is placed in the subtitle or body placeholder |
| `Title and Content` | Accepts text flow, one image, or one table |
| `Title Only` | Does not accept body content |
| `Blank` | Requires an empty title and empty body |

Supported Markdown includes:

- Paragraphs
- Bullet and ordered lists, nested up to three levels
- `##` through `######` headings within a slide
- Emphasis, strong text, inline code, and links
- Fenced code blocks
- Blockquotes
- Pipe tables
- Local and remote images

The intentionally unsupported set includes:

- Setext headings
- Indented code blocks
- Horizontal rules
- Raw HTML
- Task lists
- Footnotes
- Arbitrary positioning
- Layered backgrounds
- Animations

## Automation and image export

### Structured results and overwrite safety

Use `--json` for agent and automation workflows:

```powershell
uvx markdown-pptx deck.md deck.pptx --json
```

Successful JSON includes the output path, slide count, and template master details. Failures include a stable error code and relevant input, line, slide, or partial-output context.

The CLI refuses to overwrite an existing presentation or colliding generated image. Add `--force` only when replacing generated output is intended:

```powershell
uvx markdown-pptx deck.md deck.pptx --force --json
```

### Export slide images on Windows

On Windows, the CLI can use an installed desktop copy of Microsoft PowerPoint to export PNG or JPEG previews after generating the editable presentation:

```powershell
uvx markdown-pptx deck.md deck.pptx --export-images png --slides 1,3-5 --image-width 1600 --json
```

Image export requires Windows, an interactive desktop session, and an installed, licensed, initialized PowerPoint application. The default output directory is `<pptx-name>-images`. PNG is recommended for text and diagrams.

The editable `.pptx` is retained if image export fails. With `--json`, the partial output path is reported in `error.details.pptx_output`.

## Reference

Useful discovery and metadata commands:

```powershell
uvx markdown-pptx --help
uvx markdown-pptx --syntax
uvx markdown-pptx --list-color-schemes
uvx markdown-pptx --list-masters --template theme.pptx
uvx markdown-pptx --list-layouts --template theme.pptx --master 2
uvx markdown-pptx --about
uvx markdown-pptx --version
```

Exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | Success |
| `2` | Usage or input error |
| `3` | Markdown or front-matter parse error |
| `4` | Template or layout error |
| `5` | Image or other asset error |
| `6` | Unsupported Markdown content |
| `7` | PowerPoint rendering error |
| `8` | Unexpected internal error |

## Examples

- [Sample source deck](sample/showcase.md)
- [Sample rendered deck](sample/showcase.pptx)
- [Sample multi-master template](sample/showcase-template.pptx)
- [Sample local image](sample/showcase-local.png)

Regenerate the showcase from the repository checkout:

```powershell
uvx --refresh --from . markdown-pptx sample/showcase.md sample/showcase.pptx --template sample/showcase-template.pptx --force
```

## Development

Install the development environment and run the checks:

```powershell
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The real PowerPoint export smoke test is optional and requires desktop PowerPoint:

```powershell
$env:MARKDOWN_PPTX_TEST_POWERPOINT="1"
uv run pytest tests/test_powerpoint_integration.py
```

Build and validate distributable packages:

```powershell
uv build
uv run twine check dist/*
```

CI runs `tests/wheel_smoke.py` with an isolated installed wheel. It checks version discovery, generated skill metadata, automatic synchronization, and inspection output. Run `uv run python tests/wheel_smoke.py --expect-local` to check development-build exclusion and explicit installation. Both the smoke checks and pytest use temporary skill directories.

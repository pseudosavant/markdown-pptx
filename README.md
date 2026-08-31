# markdown-pptx

`markdown-pptx` is a Markdown-to-PowerPoint CLI for both people and agents. You can use it directly from the terminal, but the format and CLI are intentionally designed to be easy for coding agents to use reliably, and this extends their natural strength with Markdown into generating real, editable PowerPoint slides instead of plain text outlines or ad hoc exports.

It converts constrained Markdown slide decks into editable PowerPoint `.pptx` presentations using real PowerPoint layouts and placeholders. The format is intentionally strict: each `# H1` starts a slide, YAML front matter controls document and slide behavior, and the tool exposes inspection-friendly modes like `--syntax`, `--list-masters`, `--list-layouts`, and `--list-color-schemes` while failing on ambiguous mappings instead of inventing free-positioned text boxes.


## What it does

Convert markdown like this:

```markdown
# What markdown-pptx is

`markdown-pptx` converts constrained Markdown slide decks into editable PowerPoint `.pptx` presentations.

It uses real PowerPoint layouts and placeholders, so the output stays easy to edit in PowerPoint instead of becoming a pile of free-positioned text boxes.
```

Into this:

![Rendered PowerPoint slide example](https://github.com/user-attachments/assets/99859d77-ca0b-4f4c-9dee-ac2be729a0e9)

## Install

### Run directly with uvx

```powershell
uvx markdown-pptx --help
```

### Install as a tool

```powershell
uv tool install markdown-pptx
```

### Install the agent skill

Install a managed, agent-neutral skill into the shared `~/.agents/skills` convention:

```powershell
uvx markdown-pptx skill install
uvx markdown-pptx skill remove
```

Use `--skills-dir DIR` to target another skill root. Removal is idempotent and refuses to delete an unmarked, user-managed skill unless `--force` is explicitly supplied.

## CLI

```powershell
markdown-pptx deck.md
markdown-pptx deck.md out.pptx
markdown-pptx deck.md --ignore-document-colors
markdown-pptx deck.md --ignore-document-colors --ignore-slide-colors
markdown-pptx --list-masters --template theme.pptx
markdown-pptx --list-layouts
markdown-pptx --list-layouts --template theme.pptx --master 2
markdown-pptx deck.md out.pptx --template theme.pptx --master 2
markdown-pptx --list-color-schemes
markdown-pptx --syntax
markdown-pptx --about
```

Running `markdown-pptx` with no arguments prints the same concise quick reference as `--help`. Inspection commands accept `--json` and reject unrelated render flags so automation cannot accidentally invoke an ambiguous mode.

When you use `--template`, every embedded slide master is retained in the output. This keeps all of the template's layout groups available in PowerPoint, so a slide can be reassigned later from PowerPoint's **Layout** gallery without rebuilding the deck. The template's existing theme colors and theme fonts are kept unless the Markdown explicitly sets `color_scheme` or `fonts`.

The first master is the default. Use `--list-masters --template theme.pptx` to inspect the available masters and `--master 2` (or an exact unique master/theme name) to choose another default. Use `--list-layouts --template theme.pptx --master 2 --json` to inspect the layouts, placeholders, and compatibility results for that master. Numeric master selectors are 1-based and are the most reliable choice because PowerPoint templates can contain blank or duplicate names.

A slide-level `master` value overrides the CLI default for that slide. Selection precedence is slide `master`, then CLI `--master`, then the first embedded master. Layout lookup and duplicate-name checks are scoped to the selected master. Selecting a master never removes the others from the output.

Document-level backgrounds are applied to every retained master. Explicit document `color_scheme` and `fonts` overrides update every theme referenced by the retained masters; without those overrides, template themes are preserved.

`--ignore-document-colors` ignores document-level markdown color settings (`color_scheme`, `title_color`, `body_color`, and non-image document backgrounds). `--ignore-slide-colors` ignores slide-level `title_color`, `body_color`, and non-image slide backgrounds. Use both flags together to let the template provide all colors while still keeping the markdown content and layouts.

Remote HTTP(S) images are enabled by default. Downloads are streamed, cached per URL during a render, limited to 25 MiB, checked for an image content type when the server supplies one, decoded with Pillow, and limited to 50 million pixels. Use `--no-remote-images` for offline builds or untrusted Markdown. For reproducible builds, download assets ahead of time and reference local files.

## Format

### Document structure

1. An optional document front matter block may appear only at the top of the file.
2. Each `# H1` starts a new slide.
3. An optional slide front matter block may appear only immediately after an `# H1`.
4. Everything until the next `# H1` is that slide's body content.

### Example deck

```markdown
---
aspect_ratio: "16:9"
fonts:
  body: Aptos
  headings: Aptos Display
color_scheme:
  preset: Office
title_color: "var(--dark-1)"
body_color: "var(--dark-1)"
background: "linear-gradient(90deg, var(--light-1) 0%, var(--light-2) 100%)"
---

# Title slide
---
layout: Title Slide
notes: |
  Introduce the deck.
---

Markdown in. Editable PowerPoint out.

# Overview
---
master: 1
layout: Title and Content
background: "linear-gradient(90deg, var(--accent-1) 0%, var(--accent-2) 100%)"
---

## Goals
- Keep the markdown readable
- Use real PowerPoint placeholders
- Fail on ambiguous mappings
```

## Document-level front matter

These keys are valid only in the opening front matter block at the top of the document:

- `aspect_ratio`
  - `"16:9"` or `"4:3"`
- `fonts`
  - `body`
  - `headings`
- `color_scheme`
  - `preset: Office`
  - or explicit overrides for the 12 PowerPoint theme colors
- `background`
  - solid color
  - `linear-gradient(...)`
  - `radial-gradient(...)`
  - `url(...)`
  - `none`
- `title_color`
  - default color for title placeholders across the deck
- `body_color`
  - default color for body/subtitle placeholders across the deck

### Document front matter example

```yaml
---
aspect_ratio: "16:9"
fonts:
  body: Aptos
  headings: Aptos Display
color_scheme:
  preset: Office
title_color: "var(--dark-1)"
body_color: "var(--accent-4)"
background: "linear-gradient(90deg, var(--light-1) 0%, var(--light-2) 100%)"
---
```

## Slide-level front matter

These keys are valid only immediately after a slide `# H1`:

- `master`
  - a positive 1-based index, such as `1` or `2`
  - or an exact unique slide-master/theme name reported by `--list-masters`
  - overrides the CLI `--master` default for that slide
- `layout`
  - `Title Slide`
  - `Title and Content`
  - `Section Header`
  - `Title Only`
  - `Blank`
- `background`
  - overrides the document background for that slide
- `title_color`
  - overrides the document title color for that slide
- `body_color`
  - overrides the document body color for that slide
- `hide_background_graphics`
  - hides inherited master graphics on that slide
- `notes`
  - speaker notes stored in the PPTX notes pane
- `table`
  - PowerPoint table-style options for a slide containing exactly one pipe table
  - `header_row`, `total_row`, `first_column`, `last_column`, `banded_rows`, and `banded_columns`
  - every option must be `true` or `false`

### Slide front matter example

```markdown
# Section break
---
master: 1
layout: Section Header
background: "linear-gradient(90deg, var(--accent-1) 0%, var(--accent-2) 100%)"
title_color: "var(--light-1)"
body_color: "var(--light-1)"
notes: |
  Introduce the next section.
---

This subtitle is rendered into the Section Header body/subtitle placeholder.
```

`color_scheme` can start from a built-in preset and override only selected slots. This is useful when a template already has the right layouts but needs a bespoke palette:

```yaml
color_scheme:
  preset: Office
  dark_1: "#10263F"
  light_1: "#F9F9F9"
  accent_1: "#1D6FA8"
  accent_2: "#5AA9E6"
  accent_3: "#FFB347"
```

For a completely custom PowerPoint theme, set `preset: null` and provide all 12 slots: `dark_1`, `light_1`, `dark_2`, `light_2`, `accent_1` through `accent_6`, `hyperlink`, and `followed_hyperlink`. Theme-aware template objects and `var(--...)` references follow the resulting palette; hard-coded RGB colors and images do not.

Table styling is also slide metadata, leaving the pipe table itself as standard Markdown:

```markdown
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

`total_row`, `first_column`, and `last_column` apply PowerPoint styling only; they do not calculate totals or change table semantics. Setting `header_row: false` removes the special PowerPoint header styling, but the first Markdown row remains the syntactic table header.

## Supported color syntax

For `title_color`, `body_color`, and color-bearing backgrounds/gradient stops:

- Hex: `#0E2841`
- RGB: `rgb(14, 40, 65)`
- HSL: `hsl(210, 65%, 15%)`
- Theme references:
  - `var(--dark-1)`
  - `var(--light-1)`
  - `var(--dark-2)`
  - `var(--light-2)`
  - `var(--accent-1)` through `var(--accent-6)`
  - `var(--hyperlink)`
  - `var(--followed-hyperlink)`

## Supported markdown

- Paragraphs
- Bullet lists
- Ordered lists
- Nested lists up to three levels
- `##` through `######` headings inside a slide
- Emphasis, strong, inline code, links
- Fenced code blocks
- Blockquotes
- Pipe tables
- Local images
- Remote images

Fenced code blocks follow CommonMark fence rules: backticks or tildes, a run of at least three markers, and a closing run using the same marker with at least the opening length.

Pipe tables treat the first Markdown row as the table header. The PowerPoint output uses the `Medium Style 1 - Accent 1` table style. Defaults are **Header Row** and **Banded Rows** enabled, with **Total Row**, **First Column**, **Last Column**, and **Banded Columns** disabled. Override those native PowerPoint flags with slide-level `table` metadata.

## Layout and rendering rules

- All embedded template masters are retained in the output.
- Master selection precedence is slide `master`, CLI `--master`, then master `1`.
- Master and theme names are accepted only when they resolve uniquely; 1-based numeric selectors are canonical.
- Layout lookup is scoped to the effective master for each slide.
- `Blank` requires an empty title and empty body.
- `Title Only` allows no body content.
- `Title Slide` and `Section Header` render slide body text into the subtitle/body placeholder.
- `Title and Content` supports either text flow, one image, or one table.
- Missing required placeholders are treated as errors.
- Duplicate layout names and multiple matching required placeholders are treated as errors.
- The renderer uses real PowerPoint placeholders rather than synthesized text boxes for title/body content.
- Linear and radial gradients preserve every declared color stop.

## Unsupported markdown/features

- Setext headings
- Indented code blocks
- Horizontal rules
- Raw HTML
- Task lists
- Footnotes
- Arbitrary positioning
- Layered backgrounds
- Animations

## Exit codes

- `0`: success
- `2`: usage or input error
- `3`: Markdown or front-matter parse error
- `4`: template or layout error
- `5`: image or other asset error
- `6`: unsupported Markdown content
- `7`: PowerPoint rendering error
- `8`: unexpected internal error

With `--json`, failures are written as structured JSON with a stable error code and relevant input, line, and slide context. Successful render JSON includes the default master, retained-master count, and masters actually used by generated slides.

## Examples

- Sample source deck: `sample/showcase.md`
- Sample rendered deck: `sample/showcase.pptx`
- Sample multi-master template: `sample/showcase-template.pptx`
- Sample local image: `sample/showcase-local.png`

Regenerate the showcase with the local source and its two-master template:

```powershell
uvx --refresh --from . markdown-pptx sample/showcase.md sample/showcase.pptx --template sample/showcase-template.pptx --force
```

## Development

Run tests:

```powershell
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Build distributables:

```powershell
uv build
uv run twine check dist/*
```

CI tests Python 3.11 through 3.14 on Windows and Linux, checks Ruff lint/format, builds both distributions, validates metadata, and smoke-tests the built wheel. PyPI publishing repeats the release gates and verifies that release tags match the package version.

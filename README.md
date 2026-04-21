# md-to-pptx

Convert constrained Markdown slide decks into editable PowerPoint `.pptx` presentations using real PowerPoint layouts and placeholders.

`md-to-pptx` is intentionally strict. Each `# H1` starts a slide, YAML front matter controls document and slide behavior, and the renderer fails on ambiguous mappings instead of inventing free-positioned text boxes.

`md-to-pptx` is a Markdown-to-PowerPoint CLI for both people and agents. You can use it directly from the terminal, but the format and CLI are intentionally designed to be easy for coding agents to use reliably: slide boundaries are unambiguous, front matter is strict, and the tool exposes inspection-friendly modes like `--syntax`, `--list-layouts`, and `--list-color-schemes`. Agents already work naturally with Markdown, and this extends that strength into generating real, editable PowerPoint slides instead of plain text outlines or ad hoc exports.

## Install

### Run directly with uvx

```powershell
uvx md-to-pptx --help
```

### Install as a tool

```powershell
uv tool install md-to-pptx
```

## CLI

```powershell
md-to-pptx deck.md
md-to-pptx deck.md out.pptx
md-to-pptx --list-layouts
md-to-pptx --list-color-schemes
md-to-pptx --syntax
```

When you use `--template`, the template's existing theme colors and theme fonts are kept unless the markdown explicitly sets `color_scheme` or `fonts`.

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

### Slide front matter example

```markdown
# Section break
---
layout: Section Header
background: "linear-gradient(90deg, var(--accent-1) 0%, var(--accent-2) 100%)"
title_color: "var(--light-1)"
body_color: "var(--light-1)"
notes: |
  Introduce the next section.
---

This subtitle is rendered into the Section Header body/subtitle placeholder.
```

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

## Layout and rendering rules

- `Blank` requires an empty title and empty body.
- `Title Only` allows no body content.
- `Title Slide` and `Section Header` render slide body text into the subtitle/body placeholder.
- `Title and Content` supports either text flow, one image, or one table.
- Missing required placeholders are treated as errors.
- The renderer uses real PowerPoint placeholders rather than synthesized text boxes for title/body content.

## Unsupported markdown/features

- Setext headings
- Indented code blocks
- Raw HTML
- Task lists
- Footnotes
- Arbitrary positioning
- Layered backgrounds
- Animations

## Examples

- Sample source deck: `sample/showcase.md`
- Sample rendered deck: `sample/showcase.pptx`
- Sample local image: `sample/showcase-local.png`

## Development

Run tests:

```powershell
uv run pytest
```

Build distributables:

```powershell
uv build
```

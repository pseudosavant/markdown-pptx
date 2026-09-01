---
aspect_ratio: "16:9"
fonts:
  body: Aptos
  headings: Aptos Display
color_scheme:
  preset:
  dark_1: "#10263F"
  light_1: "#F9F9F9"
  dark_2: "#355A78"
  light_2: "#EEF8FF"
  accent_1: "#1D6FA8"
  accent_2: "#5AA9E6"
  accent_3: "#7FC8F8"
  accent_4: "#FFB347"
  accent_5: "#FF6392"
  accent_6: "#144F79"
  hyperlink: "#1D6FA8"
  followed_hyperlink: "#355A78"
title_color: "var(--accent-6)"
body_color: "var(--dark-1)"
background: "linear-gradient(90deg, #F3FAFF 0%, #E6F4FF 54%, #FFE7BF 100%)"
---

# markdown-pptx
---
layout: Title Slide
---

Markdown in. Editable PowerPoint out.

# What markdown-pptx is

`markdown-pptx` converts constrained Markdown slide decks into editable PowerPoint `.pptx` presentations.

It uses real PowerPoint layouts and placeholders, so the output stays easy to edit in PowerPoint instead of becoming a pile of free-positioned text boxes.

# How the format works

An optional document front matter block sets deck-wide defaults such as aspect ratio, fonts, colors, and background behavior.

Each `# H1` starts a new slide, optional slide front matter appears immediately after the H1, and everything until the next H1 becomes that slide's content.

# Basic CLI usage

Run `uvx markdown-pptx deck.md` to write `deck.pptx` next to the source markdown file.

Use `uvx markdown-pptx deck.md out.pptx` to choose the output path, `--template theme.pptx` to render against an existing PowerPoint template, and `--force` to overwrite an existing file.

Run `uvx markdown-pptx` with no arguments for the quick reference or use `--about` for project metadata.

# Inspection-friendly CLI modes

Use `--syntax` to print the supported deck format, `--list-masters` to inspect a template's slide masters, `--list-layouts` to inspect layouts on a selected master, and `--list-color-schemes` to see the built-in theme presets.

Add `--json` for structured results. Master and layout inspection report names, indices, placeholder inventory, and compatibility so people and coding agents can discover valid inputs before generating a deck.

# Master and layout selection
---
master: "Showcase Alternate"
layout: Title and Content
---

This slide uses the template's `Showcase Alternate` master while the rest of the deck defaults to master 1. Templates keep every embedded master in the output.

Master selection uses slide metadata first, then the CLI default, then master 1. Layout names are resolved within the selected master.

# Agent skill support

Run `uvx markdown-pptx skill install` to install the managed agent skill under `~/.agents/skills`, or `uvx markdown-pptx skill remove` to remove it safely.

The skill teaches agents to inspect syntax, masters, and layouts; prefer structured output; respect overwrite safety; and handle local or remote images predictably.

# Color and template control

Markdown can set document-level and slide-level colors with `color_scheme`, `title_color`, `body_color`, and background values such as solid colors, gradients, and images.

When a template already has the colors you want, `--ignore-document-colors` and `--ignore-slide-colors` let the template remain the source of truth for those color settings.

# Supported color formats
---
title_color: "hsl(204, 71%, 39%)"
body_color: "rgb(16, 38, 63)"
background: "#DEF"
---

Colors accept short or long hex, RGB, HSL, and PowerPoint theme references such as `var(--accent-1)`.

# Every PowerPoint theme color
---
layout: Title Only
title_color: "var(--light-1)"
background: "linear-gradient(270deg, var(--dark-1) 0%, var(--dark-1) 20%, var(--light-1) 20%, var(--light-1) 27.273%, var(--dark-2) 27.273%, var(--dark-2) 34.545%, var(--light-2) 34.545%, var(--light-2) 41.818%, var(--accent-1) 41.818%, var(--accent-1) 49.091%, var(--accent-2) 49.091%, var(--accent-2) 56.364%, var(--accent-3) 56.364%, var(--accent-3) 63.636%, var(--accent-4) 63.636%, var(--accent-4) 70.909%, var(--accent-5) 70.909%, var(--accent-5) 78.182%, var(--accent-6) 78.182%, var(--accent-6) 85.455%, var(--hyperlink) 85.455%, var(--hyperlink) 92.727%, var(--followed-hyperlink) 92.727%, var(--followed-hyperlink) 100%)"
notes: |
  This slide uses every theme color as a hard band in the background.
  From top to bottom: Dark 1, Light 1, Dark 2, Light 2, Accent 1 through Accent 6, Hyperlink, and Followed Hyperlink.
---

# Feature examples
---
layout: Section Header
---

Each slide after this one isolates a single `markdown-pptx` feature.

# Title Slide layout
---
layout: Title Slide
---

This slide uses the Title Slide layout.

# Section Header layout
---
layout: Section Header
---

This slide uses the Section Header layout.

# Title and Content layout
---
master: 1
layout: Title and Content
---

This slide explicitly uses master 1 and its Title and Content layout.

# Title Only layout
---
layout: Title Only
---

# Body text with hyperlinks

`markdown-pptx` can include links in normal body text, such as the [project repository](https://github.com/pseudosavant/markdown-pptx) and the [python-pptx documentation](https://python-pptx.readthedocs.io/en/latest/).

# Inline text styling

Normal text can mix **strong emphasis**, *italic emphasis*, `inline code`, and [hyperlinks](https://github.com/pseudosavant/markdown-pptx) in the same editable placeholder.

# H2 through H6 headings

## H2 heading

### H3 heading

#### H4 heading

##### H5 heading

###### H6 heading

# Bulleted list

- Write a readable Markdown deck
- Choose a template if needed
- Render an editable PowerPoint file

# Nested lists

- Inspect the template
  - Select a master
    - Choose a compatible layout
- Write the Markdown
  - Keep each slide focused
- Render and review the PowerPoint

# Numbered list

1. Write the markdown source
2. Run the CLI
3. Open the generated `.pptx`

# Pipe table
---
table:
  header_row: true
  total_row: true
  first_column: true
  last_column: true
  banded_rows: true
  banded_columns: true
---

| Markdown input | PowerPoint result |
| --- | --- |
| `# H1` | New slide |
| `layout` | Real slide layout |
| `master` | Master-specific layout group |
| `notes` | Editable speaker notes |
| Total | All six native table-style flags |

# Blockquote

> markdown-pptx keeps the source format simple enough to read directly while still producing a real presentation.

# Code block

```powershell
uvx markdown-pptx sample/showcase.md sample/showcase.pptx --template sample/showcase-template.pptx --force
```

# Local image

![Local markdown-pptx sample image](./showcase-local.png)

# Remote image
---
notes: |
  This slide demonstrates downloading a remote image during rendering.
  [Sources]
  - https://raw.githubusercontent.com/github/explore/main/topics/python/python.png (Python logo)
---

![Remote Python logo](https://raw.githubusercontent.com/github/explore/main/topics/python/python.png)

# Background color
---
background: "#EAF3FF"
---

This slide uses a solid slide background color.

# Transparent background and hidden master graphics
---
master: 2
layout: Title and Content
background: none
hide_background_graphics: true
---

This slide removes its slide-level fill and hides the orange accent graphic inherited from the alternate master.

#
---
layout: Blank
background: "url('./showcase-local.png')"
notes: This slide demonstrates a full-slide background image on the Blank layout.
---

# Linear gradient background
---
background: "linear-gradient(90deg, var(--accent-2) 0%, var(--accent-3) 48%, var(--accent-4) 100%)"
---

This slide uses a three-stop linear gradient background.

# Radial gradient background
---
background: "radial-gradient(circle, var(--accent-2) 0%, var(--accent-4) 58%, var(--light-1) 100%)"
---

This slide uses a radial gradient background.

# Slide colors override document colors
---
title_color: "var(--light-1)"
body_color: "var(--light-1)"
background: "linear-gradient(90deg, var(--accent-1) 0%, var(--accent-4) 100%)"
---

This slide overrides the document-level title and body colors.

#
---
layout: Blank
notes: |
  This slide intentionally demonstrates the Blank layout.
---

# Markdown in. Editable PowerPoint out.
---
layout: Title Slide
---

Run `uvx markdown-pptx --help` to get started.

# Changelog

## 3.0.0

- **Behavior change:** Infer Title Slide from a nonempty first H1 alone or followed by one H2. Infer Section Header for the same structure on later slides. The H2 becomes the native subtitle. Multiple H2s or additional content retain ordinary layout behavior. Explicit slide layouts win, and heading inference precedes the deck default.
- Infer Two Content from one top-level Markdown thematic break. Add deck-wide default layouts and omit redundant layout comments from examples and authoring guidance.
- Size table rows to their content using zero-height native rows. Tables default to full content-area width and stay top aligned. Markdown separator colons control horizontal cell alignment. Cell text defaults to left aligned and vertically centered. Oversized tables are not automatically shrunk.
- Add `media_layout` and `table_layout` at deck, slide, and element scope. Width percentages use the assigned content box. Horizontal alignment defaults to center. Media now defaults to top alignment and also supports middle and bottom placement.
- Add scoped `media_effects` and `table_effects` for borders, shadows, and reflections. Media also supports corner radius. Tables reject corner radius. Properties inherit independently and accept explicit resets. Effects preserve object size and position.
- Replace content placeholders with native tables, pictures, and videos while retaining their layout identity. Remove empty placeholders underneath those objects.
- Add deck and slide table fill colors while preserving native defaults and total-row styling. Preserve rich inline formatting, hyperlinks, and ScreenTips inside table cells.
- Add hidden slides with `hidden: true` in slide metadata.
- Reject unknown and misplaced reserved metadata comments, including orphan directives before the first H1. Preserve ordinary comments, reference definitions, and literal code examples.
- Replace the original showcase with a vanilla Markdown default showcase and a separate advanced showcase. Retain coverage of all 61 original topics. Update the README, built-in skill, syntax catalog, examples, and tests. Exclude generated PNG preview folders from source distributions.

## 2.0.0

- **Breaking change:** Replace deck and slide YAML front matter with hidden `markdown-pptx:deck` and `markdown-pptx:slide` HTML comments. The old `---` front matter format is rejected. Move the same YAML settings inside the matching comment:

  ```markdown
  <!-- markdown-pptx:deck
  aspect_ratio: "16:9"
  -->

  # Slide title
  <!-- markdown-pptx:slide
  layout: Title and Content
  -->
  ```

- Turn standalone Markdown links to H.264 MP4 files and YouTube videos into PowerPoint video objects. Local and HTTPS MP4 files are embedded. YouTube playback remains online.
- Use a linked image to provide a custom MP4 poster. Otherwise, PyAV generates a poster from the first decoded frame and reads the video's display aspect ratio.
- Add optional video comments for sizing and placement. MP4 playback also supports `start`, `fullscreen`, `loop`, and `mute`. Remote MP4 downloads have a configurable size limit.
- Add video examples and Big Buck Bunny slides to the showcase. Update the CLI syntax, README, and managed skill for the new format.

## 1.3.0

- Automatically synchronize an already-installed managed skill during normal installed CLI runs. Use the running version, PEP 440 ordering, content hashes, and atomic replacement to preserve edits and avoid downgrades.
- Add managed YAML metadata, legacy migration, read-only `skill status`, and `skill install --force`. Preserve `uvx` guidance, custom-directory support, and removal safety.
- Skip automatic synchronization for local source and editable builds. Keep maintenance local and notices on stderr, with focused lifecycle tests and installed-wheel smoke checks.

## 1.2.0

- Add optional Windows desktop PowerPoint image export for all or selected slides as PNG/JPEG, with deterministic filenames, aspect-preserving dimensions, isolated automation, transactional staging, structured output/errors, and platform-aware help.
- Remove the obsolete Berlin-template sample trio now superseded by the current multi-master showcase.

## 1.1.0

- Align the CLI with the sibling agent tools: useful no-argument help, `--about`, exact inspection modes, stable exit codes, JSON errors, and managed `skill install` / `skill remove` commands.
- Retain every embedded template slide master; add `--list-masters`, CLI `--master`, and slide-level `master` selection; scope layouts to the effective master; apply explicit document theme/background overrides across retained masters; and report master usage in JSON.
- Preserve all linear and radial gradient stops and correctly render a `0deg` gradient.
- Add strict slide-level `table` metadata for PowerPoint Header Row, Total Row, First Column, Last Column, Banded Rows, and Banded Columns styling.
- Follow CommonMark backtick and tilde fence rules and strictly reject raw HTML, task lists, footnotes, horizontal rules, and non-boolean `hide_background_graphics` values.
- Harden remote images with streaming downloads, a 25 MiB cap, content-type and decode validation, a 50-megapixel cap, per-render caching, sanitized errors, and `--no-remote-images`.
- Add locked Ruff, pytest, build, metadata, wheel-smoke, Python 3.11–3.14, Windows/Linux, tag/version, and trusted-publishing quality gates.

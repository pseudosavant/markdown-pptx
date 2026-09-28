# Changelog

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

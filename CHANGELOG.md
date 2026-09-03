# Changelog

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

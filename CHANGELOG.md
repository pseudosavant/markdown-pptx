# Changelog

## 1.1.0

- Align the CLI with the sibling agent tools: useful no-argument help, `--about`, exact inspection modes, stable exit codes, JSON errors, and managed `skill install` / `skill remove` commands.
- Retain every embedded template slide master; add `--list-masters`, CLI `--master`, and slide-level `master` selection; scope layouts to the effective master; apply explicit document theme/background overrides across retained masters; and report master usage in JSON.
- Preserve all linear and radial gradient stops and correctly render a `0deg` gradient.
- Add strict slide-level `table` metadata for PowerPoint Header Row, Total Row, First Column, Last Column, Banded Rows, and Banded Columns styling.
- Follow CommonMark backtick and tilde fence rules and strictly reject raw HTML, task lists, footnotes, horizontal rules, and non-boolean `hide_background_graphics` values.
- Harden remote images with streaming downloads, a 25 MiB cap, content-type and decode validation, a 50-megapixel cap, per-render caching, sanitized errors, and `--no-remote-images`.
- Add locked Ruff, pytest, build, metadata, wheel-smoke, Python 3.11–3.14, Windows/Linux, tag/version, and trusted-publishing quality gates.

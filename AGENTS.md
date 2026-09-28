# AGENTS.md

This repository contains **`markdown-pptx`**, a Python CLI that converts constrained Markdown with hidden metadata comments into editable PowerPoint `.pptx` files using real PowerPoint layouts and placeholders.

## Project identity

- **Published package name:** `markdown-pptx`
- **CLI command:** `markdown-pptx`
- **Python package import:** `markdown_slides`

Do not rename the import package unless the user explicitly asks. The distribution/CLI name and the import package name are intentionally different.

## Repo layout

- `src/markdown_slides/cli.py` — CLI argument parsing, JSON/plain output, render entrypoint
- `src/markdown_slides/parser.py` handles document metadata and slide parsing.
- `src/markdown_slides/markdown_body.py` — markdown body parsing into internal models
- `src/markdown_slides/models.py` — dataclasses for deck/slide/body structures
- `src/markdown_slides/renderer.py` — PPTX rendering, template/theme handling, background and text formatting
- `src/markdown_slides/assets/` — packaged default template and static syntax/color assets
- `tests/` — pytest coverage for CLI, parser, and renderer behavior
- `sample/` — showcase/sample decks and rendered outputs

## Working conventions

- The format is intentionally **strict**. Preserve that philosophy.
- `# H1` is the only slide boundary.
- Deck metadata uses a `markdown-pptx:deck` HTML comment at the start of the file.
- Slide metadata uses a `markdown-pptx:slide` HTML comment immediately after an H1.
- Standalone MP4 and YouTube links become videos. A linked image to an MP4 supplies its poster. Optional `markdown-pptx:video` comments hold playback settings.
- The renderer should use **real template placeholders/layouts** and should fail when required placeholders are missing rather than inventing floating text boxes.
- Keep behavior predictable for both humans and coding agents.
- Prefer adding tests for behavior changes, especially parser and renderer semantics.

## Commands

Common commands from repo root:

```powershell
uvx --refresh --from . markdown-pptx --help
uvx --refresh --with-editable . pytest --basetemp=.pytest-tmp
uvx --refresh --from . markdown-pptx sample\showcase.md sample\showcase.pptx --template sample\showcase-template.pptx --force
uvx --refresh --from . markdown-pptx --syntax
uvx --refresh --from . markdown-pptx --list-layouts
```

Because this repo often lives on OneDrive-backed storage, use:

```powershell
$env:UV_LINK_MODE="copy"
```

before `uv` / `uvx` commands if hardlink errors appear.

## Important behavior details

### Templates

- If no `--template` is provided, rendering uses the packaged `example.pptx`.
- If `--template` is provided, template theme colors and theme fonts should be preserved unless markdown explicitly overrides them.
- Body paragraph spacing defaults are only injected when **no** explicit `--template` is provided.

### Color handling

- Document-level colors include `color_scheme`, `title_color`, `body_color`, and non-image document backgrounds.
- Slide-level colors include `title_color`, `body_color`, and non-image slide backgrounds.
- CLI flags:
  - `--ignore-document-colors`
  - `--ignore-slide-colors`
- These flags strip markdown color overrides in favor of template colors; do not let them affect images or layout/content structure.

### Theme color variables

Supported `var(...)` references include:

- `var(--dark-1)`
- `var(--light-1)`
- `var(--dark-2)`
- `var(--light-2)`
- `var(--accent-1)` through `var(--accent-6)`
- `var(--hyperlink)`
- `var(--followed-hyperlink)`

If you add or change supported variables, update:

- `src/markdown_slides/assets/syntax.json`
- `README.md`
- CLI tests that validate `--syntax`

## Editing guidance

- Keep changes surgical.
- Reuse existing helpers and model structures instead of duplicating logic.
- When changing CLI behavior, update:
  - help text / parser options
  - JSON output if applicable
  - tests in `tests/test_cli.py`
- When changing render semantics, add or update XML-level assertions in `tests/test_renderer.py`.
- When changing the document format contract, update:
  - parser tests
  - `README.md`
  - `src/markdown_slides/assets/syntax.json`

## Sample deck expectations

`sample/showcase.md` is the main product showcase. It is meant to demonstrate the tool itself plus isolated format/rendering features. If you change visible rendering behavior, consider whether `sample/showcase.md` and `sample/showcase.pptx` should be refreshed.

## Publishing notes

- GitHub repo: `pseudosavant/markdown-pptx`
- PyPI/trusted publishing workflow: `.github/workflows/publish-pypi.yml`
- Release/version updates should keep `pyproject.toml` and `src/markdown_slides/__init__.py` in sync.

## Tests

- Main suite: `pytest`
- Tests are semantic/XML-based, not visual screenshot regression tests.
- A change can pass tests and still look wrong in PowerPoint, so sample deck regeneration is useful for presentation-facing changes.

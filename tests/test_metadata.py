from __future__ import annotations

import tomllib
from pathlib import Path

from markdown_slides import __version__


def test_package_versions_are_in_sync() -> None:
    project_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "markdown-pptx"
    assert pyproject["project"]["version"] == __version__

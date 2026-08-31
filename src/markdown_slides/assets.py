from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

PACKAGE_ASSETS = files("markdown_slides").joinpath("assets")


def asset_path(name: str) -> Path:
    return Path(str(PACKAGE_ASSETS.joinpath(name)))


@lru_cache(maxsize=1)
def load_color_schemes() -> dict[str, dict[str, str]]:
    data = json.loads(asset_path("color_schemes.json").read_text(encoding="utf-8"))
    return {item["name"]: item["colors"] for item in data}


def list_color_scheme_names() -> list[str]:
    return sorted(load_color_schemes(), key=str.casefold)


@lru_cache(maxsize=1)
def load_syntax_payload() -> dict[str, Any]:
    return json.loads(asset_path("syntax.json").read_text(encoding="utf-8"))


def default_template_path() -> Path:
    return asset_path("example.pptx")

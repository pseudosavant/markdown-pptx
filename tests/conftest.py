from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def isolated_skills_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from markdown_slides import skill

    root = tmp_path / "home" / ".agents" / "skills"
    monkeypatch.setattr(skill, "default_skills_dir", lambda: root)
    return root

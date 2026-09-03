from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from markdown_slides import __version__, skill
from markdown_slides.errors import UsageError


def versioned_skill(monkeypatch: pytest.MonkeyPatch, version: str = "1.0.0") -> str:
    with monkeypatch.context() as patch:
        patch.setattr(skill, "__version__", version)
        return skill.render_skill()


def write_skill(text: str, root: Path | None = None) -> Path:
    path = skill.skill_dir(root) / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def stored_metadata(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])["metadata"]


def rehash(text: str) -> str:
    empty = re.sub(r'(?m)^(  managed-content-sha256: )"[^"]*"', r'\1""', text, count=1)
    normalized = empty.replace("\r\n", "\n").replace("\r", "\n")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return empty.replace('managed-content-sha256: ""', f'managed-content-sha256: "sha256:{digest}"', 1)


@pytest.fixture
def released(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill, "is_local_development_build", lambda: False)


def test_canonical_metadata_and_complete_file_hash() -> None:
    result = skill.install_skill()
    path = Path(result["path"])
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    metadata = stored_metadata(text)
    assert metadata["managed-by"] == "markdown-pptx"
    assert metadata["managed-version"] == __version__
    assert f'managed-version: "{__version__}"' in text
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", metadata["managed-content-sha256"])
    assert rehash(text) == text
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    assert "version" not in yaml.safe_load(text.split("---", 2)[1])
    assert skill.MANAGED_MARKER not in text
    assert "Always invoke the tool as `uvx markdown-pptx ...`" in text
    assert list(path.parent.iterdir()) == [path]


def test_canonical_generation_preserves_other_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        skill, "_SKILL_TEMPLATE", skill._SKILL_TEMPLATE.replace("metadata:\n", "metadata:\n  author: Test\n")
    )
    text = skill.render_skill()
    assert stored_metadata(text)["author"] == "Test"
    assert rehash(text) == text


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_verification_normalizes_newlines(newline: str) -> None:
    write_skill(skill.render_skill().replace("\n", newline))
    assert skill.skill_status()["integrity"] == "valid"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("# Markdown PPTX", "# My edited skill"),
        ("name: markdown-pptx", "name: modified-name"),
        ("description: Create", "description: Alter"),
        ("metadata:\n", "metadata:\n  author: User\n"),
        (f'managed-version: "{__version__}"', 'managed-version: "1.0.0"'),
    ],
)
def test_body_and_front_matter_edits_fail_integrity(before: str, after: str) -> None:
    text = skill.render_skill()
    assert before in text
    write_skill(text.replace(before, after, 1))
    assert skill.skill_status()["integrity"] == "altered"


def test_hash_replacement_does_not_touch_examples_or_other_fields() -> None:
    text = skill.render_skill() + '\nmanaged-content-sha256: "example"\n'
    text = rehash(text)
    write_skill(text)
    assert skill.skill_status()["integrity"] == "valid"


def test_verification_preserves_yaml_formatting() -> None:
    text = skill.render_skill().replace("managed-by: markdown-pptx", 'managed-by: "markdown-pptx"  # retained')
    write_skill(rehash(text))
    assert skill.skill_status()["integrity"] == "valid"


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("directory_exists", [False, True])
def test_automatic_sync_never_installs_missing_skill(directory_exists: bool) -> None:
    target = skill.skill_dir()
    if directory_exists:
        target.mkdir(parents=True)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert not (target / "SKILL.md").exists()
    assert target.exists() == directory_exists
    assert stderr.getvalue() == ""


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("owner", [None, "another-tool", "null"])
def test_unmanaged_content_is_preserved_even_with_force(owner: str | None) -> None:
    text = (
        "user content\n" if owner is None else (f"---\nmetadata:\n  managed-by: {owner}\n---\n{skill.MANAGED_MARKER}\n")
    )
    path = write_skill(text)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    for force in (False, True):
        with pytest.raises(UsageError, match="unmanaged"):
            skill.install_skill(force=force)
    assert path.read_text(encoding="utf-8") == text
    assert skill.skill_status()["managed"] is False
    assert stderr.getvalue() == ""


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("opening", ["\ufeff---\n", "--- \t\n"])
def test_front_matter_variants_cannot_hide_conflicting_owner(opening: str) -> None:
    text = opening + "metadata:\n  managed-by: another-tool\n---\n" + skill.MANAGED_MARKER
    path = write_skill(text)
    skill.synchronize_skill(stderr=io.StringIO())
    assert skill.skill_status()["managed"] is False
    with pytest.raises(UsageError, match="unmanaged"):
        skill.install_skill(force=True)
    assert path.read_bytes() == text.encode("utf-8")


def test_adding_bom_is_a_detectable_edit() -> None:
    write_skill("\ufeff" + skill.render_skill())
    assert skill.skill_status()["integrity"] == "altered"


@pytest.mark.usefixtures("released")
def test_pristine_older_skill_updates_and_reports_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_skill(versioned_skill(monkeypatch))
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert path.read_text(encoding="utf-8") == skill.render_skill()
    notice = stderr.getvalue()
    assert len(notice.splitlines()) == 1
    assert "1.0.0" in notice and __version__ in notice and str(path) in notice


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("problem", ["altered", "missing", "malformed", "uppercase"])
def test_unverifiable_versioned_skill_requires_force(monkeypatch: pytest.MonkeyPatch, problem: str) -> None:
    text = versioned_skill(monkeypatch)
    digest = stored_metadata(text)["managed-content-sha256"]
    if problem == "altered":
        text += "\nUser instructions\n"
    elif problem == "missing":
        text = re.sub(r"(?m)^  managed-content-sha256:.*\n", "", text)
    elif problem == "malformed":
        text = text.replace(digest, "invalid")
    else:
        text = text.replace(digest, digest.upper())
    path = write_skill(text)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert path.read_text(encoding="utf-8") == text
    assert skill.FORCE_INSTALL_COMMAND in stderr.getvalue()
    status = skill.skill_status()
    assert status["integrity"] == ("malformed" if problem == "uppercase" else problem)
    assert status["automatic_sync_eligible"] is False
    assert status["force_install_command"] == skill.FORCE_INSTALL_COMMAND
    with pytest.raises(UsageError, match=skill.FORCE_INSTALL_COMMAND):
        skill.install_skill()
    assert skill.install_skill(force=True)["updated"] is True
    assert path.read_text(encoding="utf-8") == skill.render_skill()


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("installed", [__version__, "99.0"])
def test_equal_and_newer_skills_are_never_rewritten(monkeypatch: pytest.MonkeyPatch, installed: str) -> None:
    path = write_skill(versioned_skill(monkeypatch, installed))
    original = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert skill.install_skill()["updated"] is False
    if installed == "99.0":
        assert skill.install_skill(force=True)["updated"] is False
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == mtime
    assert stderr.getvalue() == ""


@pytest.mark.usefixtures("released")
def test_equal_altered_skill_is_quiet_automatically_but_explicit_install_requires_force() -> None:
    text = skill.render_skill() + "\nEdit\n"
    path = write_skill(text)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert stderr.getvalue() == ""
    with pytest.raises(UsageError, match="--force"):
        skill.install_skill()
    assert path.read_text(encoding="utf-8") == text
    assert skill.install_skill(force=True)["updated"] is True


@pytest.mark.usefixtures("released")
def test_newer_altered_skill_is_never_downgraded_even_with_force(monkeypatch: pytest.MonkeyPatch) -> None:
    text = versioned_skill(monkeypatch, "99") + "\nEdit\n"
    path = write_skill(text)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert stderr.getvalue() == ""
    for force in (False, True):
        assert skill.install_skill(force=force)["updated"] is False
    assert skill.skill_status()["force_install_command"] is None
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("version", [None, "bad-version", "", "null", "12.3"])
def test_missing_or_malformed_version_recovers_without_hash(version: str | None) -> None:
    line = "" if version is None else f"  managed-version: {version}\n"
    path = write_skill(f"---\nmetadata:\n  managed-by: markdown-pptx\n{line}---\nold content\n")
    skill.synchronize_skill(stderr=io.StringIO())
    assert path.read_text(encoding="utf-8") == skill.render_skill()


@pytest.mark.usefixtures("released")
def test_legacy_migration_is_version_zero() -> None:
    path = write_skill(skill.MANAGED_MARKER + "\nlegacy content\n")
    status = skill.skill_status()
    assert status["managed"] is True
    assert status["integrity"] == "legacy"
    assert status["version_relation"] == "older"
    assert status["automatic_sync_eligible"] is True
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert "0 (legacy)" in stderr.getvalue()
    assert path.read_text(encoding="utf-8") == skill.render_skill()


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize(
    ("installed", "running", "relation"),
    [
        ("1.9", "1.10", "older"),
        ("1.10", "1.9", "newer"),
        ("1.2.0rc1", "1.2", "older"),
        ("1.2.dev1", "1.2a1", "older"),
        ("1.2", "1.2.post1", "older"),
        ("1!0", "99", "newer"),
        ("1.2+vendor", "1.2", "newer"),
        ("1.2.0", "1.2", "equal"),
    ],
)
def test_pep440_version_order(monkeypatch: pytest.MonkeyPatch, installed: str, running: str, relation: str) -> None:
    text = versioned_skill(monkeypatch, installed)
    path = write_skill(text)
    monkeypatch.setattr(skill, "__version__", running)
    assert skill.skill_status()["version_relation"] == relation
    skill.synchronize_skill(stderr=io.StringIO())
    assert path.read_text(encoding="utf-8") == (skill.render_skill() if relation == "older" else text)


@pytest.mark.usefixtures("released")
def test_invalid_running_version_skips_automatic_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    text = versioned_skill(monkeypatch)
    path = write_skill(text)
    monkeypatch.setattr(skill, "__version__", "unparseable")
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert path.read_text(encoding="utf-8") == text
    assert stderr.getvalue() == ""


@pytest.mark.parametrize(
    ("direct_url", "local"),
    [
        (None, False),
        ({"url": "file:///tmp/project", "dir_info": {}}, True),
        ({"url": "file:///tmp/project", "dir_info": {"editable": True}}, True),
        ({"url": "file:///tmp/project.tar.gz", "archive_info": {}}, True),
        ({"url": "file:///tmp/project.whl", "archive_info": {}}, False),
        ({"url": "https://example.org/project.whl", "archive_info": {}}, False),
        ({"url": "file:///tmp/project.whl"}, True),
        ({"url": "unknown"}, True),
        ({}, True),
        ("malformed json", True),
    ],
)
def test_distribution_origin_detection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    direct_url: object,
    local: bool,
) -> None:
    monkeypatch.setattr(skill, "__file__", str(tmp_path / "site-packages" / "markdown_slides" / "skill.py"))
    raw = direct_url if isinstance(direct_url, str) or direct_url is None else json.dumps(direct_url)
    dist = SimpleNamespace(locate_file=lambda _: Path(skill.__file__), read_text=lambda _: raw)
    monkeypatch.setattr(skill.metadata, "distribution", lambda name: dist)
    assert skill.is_local_development_build() is local


def test_checkout_metadata_without_pep610_is_still_local(monkeypatch: pytest.MonkeyPatch) -> None:
    dist = SimpleNamespace(locate_file=lambda _: Path(skill.__file__), read_text=lambda _: None)
    monkeypatch.setattr(skill.metadata, "distribution", lambda name: dist)
    assert skill.is_local_development_build() is True


def test_source_checkout_cannot_borrow_other_installed_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dist = SimpleNamespace(locate_file=lambda _: tmp_path / "installed" / "skill.py", read_text=lambda _: None)
    monkeypatch.setattr(skill.metadata, "distribution", lambda name: dist)
    assert skill.is_local_development_build() is True


def test_missing_distribution_is_local(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(name: str) -> None:
        raise skill.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(skill.metadata, "distribution", missing)
    assert skill.is_local_development_build() is True


@pytest.mark.parametrize("editable", [False, True])
def test_development_build_skips_sync_but_allows_explicit_install(
    monkeypatch: pytest.MonkeyPatch, editable: bool
) -> None:
    dist = SimpleNamespace(
        locate_file=lambda _: Path(skill.__file__),
        read_text=lambda _: json.dumps({"url": "file:///project", "dir_info": {"editable": editable}}),
    )
    monkeypatch.setattr(skill.metadata, "distribution", lambda name: dist)
    text = versioned_skill(monkeypatch)
    path = write_skill(text)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert path.read_text(encoding="utf-8") == text
    assert stderr.getvalue() == ""
    status = skill.skill_status()
    assert status["local_development_build"] is True
    assert status["automatic_sync_eligible"] is False
    assert skill.install_skill()["updated"] is True


@pytest.mark.usefixtures("released")
def test_custom_location_requires_explicit_updates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom = tmp_path / "custom skills"
    text = versioned_skill(monkeypatch)
    path = write_skill(text, custom)
    standard = write_skill(text)
    skill.synchronize_skill(stderr=io.StringIO())
    assert standard.read_text(encoding="utf-8") == skill.render_skill()
    assert path.read_text(encoding="utf-8") == text
    status = skill.skill_status(custom)
    assert status["standard_location"] is False
    assert status["automatic_sync_eligible"] is False
    assert skill.install_skill(custom)["updated"] is True
    assert skill.remove_skill(custom)["removed"] is True


@pytest.mark.usefixtures("released")
def test_atomic_replacement_observes_only_complete_files(monkeypatch: pytest.MonkeyPatch) -> None:
    text = versioned_skill(monkeypatch)
    path = write_skill(text)
    replace = skill.os.replace
    calls = []

    def observe(source: Path, destination: Path) -> None:
        assert destination.read_text(encoding="utf-8") == text
        assert source.parent == destination.parent
        assert source.read_text(encoding="utf-8") == skill.render_skill()
        replace(source, destination)
        assert destination.read_text(encoding="utf-8") == skill.render_skill()
        calls.append(destination)

    monkeypatch.setattr(skill.os, "replace", observe)
    skill.synchronize_skill(stderr=io.StringIO())
    assert calls == [path]
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("operation", ["replace", "fsync"])
def test_failed_write_preserves_file_and_cleans_temporary(monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    text = versioned_skill(monkeypatch)
    path = write_skill(text)

    def fail(*args: object) -> None:
        raise OSError("simulated failure")

    monkeypatch.setattr(skill.os, operation, fail)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert path.read_text(encoding="utf-8") == text
    assert list(path.parent.iterdir()) == [path]
    assert "simulated failure" in stderr.getvalue()


@pytest.mark.usefixtures("released")
@pytest.mark.parametrize("concurrent", ["newer", "altered", "unmanaged", "removed"])
def test_state_is_revalidated_after_staging(monkeypatch: pytest.MonkeyPatch, concurrent: str) -> None:
    text = versioned_skill(monkeypatch)
    replacement = versioned_skill(monkeypatch, "99") if concurrent == "newer" else "user content\n"
    if concurrent == "altered":
        replacement = text + "\nConcurrent edit\n"
    path = write_skill(text)
    original_read = skill._read_skill
    calls = 0

    def read(path: Path) -> skill._SkillState:
        nonlocal calls
        calls += 1
        if calls == 2:
            if concurrent == "removed":
                path.unlink()
            else:
                path.write_bytes(replacement.encode("utf-8"))
        return original_read(path)

    monkeypatch.setattr(skill, "_read_skill", read)
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr)
    assert calls == 2
    if concurrent == "removed":
        assert not path.exists()
    else:
        assert path.read_text(encoding="utf-8") == replacement
    assert list(path.parent.glob(".SKILL.*.tmp")) == []
    assert "changed during installation" in stderr.getvalue()


@pytest.mark.parametrize("legacy", [False, True])
def test_removal_accepts_new_metadata_and_legacy_marker(legacy: bool) -> None:
    path = write_skill(skill.MANAGED_MARKER if legacy else skill.render_skill())
    assert skill.remove_skill()["removed"] is True
    assert not path.parent.exists()
    assert skill.remove_skill()["reason"] == "not_installed"


def test_install_and_remove_preserve_unrelated_entries() -> None:
    path = write_skill(skill.render_skill())
    extra = path.parent / "user.txt"
    extra.write_text("keep", encoding="utf-8")
    assert skill.install_skill(force=True)["updated"] is False
    with pytest.raises(UsageError, match="unmanaged entries"):
        skill.remove_skill()
    assert extra.read_text(encoding="utf-8") == "keep"
    assert skill.remove_skill(force=True)["removed"] is True


def test_missing_skill_in_existing_directory_refuses_even_force() -> None:
    target = skill.skill_dir()
    target.mkdir(parents=True)
    (target / "user.txt").write_text("keep", encoding="utf-8")
    for force in (False, True):
        with pytest.raises(UsageError, match=r"no managed SKILL\.md"):
            skill.install_skill(force=force)
        with pytest.raises(UsageError, match=r"SKILL\.md is missing"):
            skill.remove_skill(force=force)


@pytest.mark.parametrize("directory_is_file", [False, True])
def test_unexpected_filesystem_entries_are_usage_errors(directory_is_file: bool) -> None:
    target = skill.skill_dir()
    if directory_is_file:
        target.parent.mkdir(parents=True)
        target.write_text("keep", encoding="utf-8")
    else:
        (target / "SKILL.md").mkdir(parents=True)
    with pytest.raises(UsageError, match="expected a"):
        skill.install_skill(force=True)


def test_removal_force_keeps_existing_unmanaged_semantics() -> None:
    path = write_skill("unmanaged\n")
    with pytest.raises(UsageError, match="not marked as managed"):
        skill.remove_skill()
    assert skill.remove_skill(force=True)["removed"] is True
    assert not path.parent.exists()

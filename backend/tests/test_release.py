"""The version is stated consistently, with a changelog entry and release notes."""

import json
import tomllib
from pathlib import Path

from ntip import __version__

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_versions_agree() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "backend" / "pyproject.toml").read_text("utf-8"))
    dashboard = json.loads((REPO_ROOT / "apps" / "dashboard" / "package.json").read_text("utf-8"))
    assert pyproject["project"]["version"] == __version__
    assert dashboard["version"] == __version__


def test_the_version_has_a_changelog_entry_and_release_notes() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text("utf-8")
    assert f"## [{__version__}] - " in changelog
    assert f"[{__version__}]: " in changelog  # the link target
    assert (REPO_ROOT / "docs" / "releases" / f"{__version__}.md").is_file()

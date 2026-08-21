"""version.py — computing {semver}-{label}-{shortSha} for one actor, ported from papeete-actor's
build.py (ADR-PA-0022, ADR-PA-0023). Every fixture commits the actor's folder to a fresh,
throwaway git repo and tags it `<name>/vX.Y.Z`, because there is no version to fabricate any
other way.
"""
import subprocess

import pytest

from papeete_version import version


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_actor_repo(folder, name, tag=None):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "marker.txt").write_text(f"{name}\n")
    _git("init", "-q", cwd=folder)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".", cwd=folder)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init", cwd=folder)
    if tag:
        _git("tag", f"{version.normalize_name(name)}/v{tag}", cwd=folder)


def test_normalize_name_is_dns_and_git_tag_safe():
    assert version.normalize_name("The Archivist") == "the-archivist"


def test_git_version_is_the_last_commit_touching_the_folder(tmp_path):
    folder = tmp_path / "archivist"
    _init_actor_repo(folder, "Archivist")
    expected = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=folder,
                               capture_output=True, text=True, check=True).stdout.strip()
    assert version.git_version(folder) == expected


def test_git_version_is_stable_across_uncommitted_edits(tmp_path):
    folder = tmp_path / "archivist"
    _init_actor_repo(folder, "Archivist")
    before = version.git_version(folder)
    (folder / "marker.txt").write_text("touched\n")
    assert version.git_version(folder) == before


def test_git_version_fails_clearly_with_no_git_history(tmp_path):
    folder = tmp_path / "archivist"
    folder.mkdir()
    with pytest.raises(ValueError, match="no git history"):
        version.git_version(folder)


def test_semver_base_reads_the_nearest_matching_tag(tmp_path):
    folder = tmp_path / "archivist"
    _init_actor_repo(folder, "Archivist", tag="2.2.0")
    assert version.semver_base(folder, "Archivist") == "2.2.0"


def test_semver_base_is_scoped_to_the_actors_own_namespaced_tag(tmp_path):
    """A monorepo may hold several actors. A `some-other-actor/v9.9.9` tag must never leak into
    this actor's semver — only `archivist/v*` counts."""
    folder = tmp_path / "archivist"
    _init_actor_repo(folder, "Archivist", tag="1.0.0")
    _git("tag", "some-other-actor/v9.9.9", cwd=folder)
    assert version.semver_base(folder, "Archivist") == "1.0.0"


def test_semver_base_fails_clearly_with_no_matching_tag(tmp_path):
    folder = tmp_path / "archivist"
    _init_actor_repo(folder, "Archivist")
    with pytest.raises(ValueError, match="no tag matching 'archivist/v\\*'"):
        version.semver_base(folder, "Archivist")


def test_compute_composes_semver_label_and_short_sha(tmp_path):
    folder = tmp_path / "archivist"
    _init_actor_repo(folder, "Archivist", tag="2.2.0")
    sha = version.git_version(folder)
    assert version.compute(folder, "Archivist", "dev") == f"2.2.0-dev-{sha}"

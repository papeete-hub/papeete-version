"""Computing one actor's version: `{semver}-{label}-{shortSha}`.

VERSION IS COMPUTED, NEVER DECLARED — nothing here reads or writes a declared `version:` field
anywhere. The semver core comes from the actor's own nearest matching git tag
(`<name>/vX.Y.Z` — GitVersion-style), the short SHA from the folder's own last touching commit,
and the label is an uninterpreted string the caller supplies — strict on the three-part shape,
silent on what a label MEANS, because that taxonomy (dev/rc/staging/GA/...) isn't decided yet.

Ported from `papeete-actor`'s `build.py` (`ADR-PA-0022`, `ADR-PA-0023`) — see this repo's own
`ADR-PV-0001` for why the computation lives here now, standalone, with nothing Docker-shaped
attached to it.
"""
import re
import subprocess
from pathlib import Path


def normalize_name(name: str) -> str:
    """An actor's name, normalized to a DNS-safe, git-tag-safe form."""
    return name.strip().lower().replace(" ", "-")


def git_version(folder: Path | str) -> str:
    """An actor's short SHA: the most recent commit that touched its folder.

    NEVER SELF-DECLARED, COMPUTED FRESH EVERY TIME. Scoped to the folder, not the whole repo's
    HEAD — an actor's version changes only when ITS OWN content changes, not when an unrelated
    sibling folder does.

    DETERMINISTIC ACROSS UNCOMMITTED EDITS. Only a COMMIT changes the answer — the ordinary local
    dev loop (edit, recompute, edit again, all before committing) computes the exact same version
    every time.
    """
    folder = Path(folder)
    result = subprocess.run(
        ["git", "log", "-1", "--format=%h", "--", "."],
        cwd=folder, capture_output=True, text=True,
    )
    sha = result.stdout.strip()
    if result.returncode != 0 or not sha:
        raise ValueError(
            f"{folder}: no git history for this folder — version is computed from the most "
            f"recent commit that touched it, so it must be committed at least once before a "
            f"version can be computed."
        )
    return sha


def semver_base(folder: Path | str, name: str) -> str:
    """The `X.Y.Z` an actor answers to right now — the semver core off the nearest tag matching
    `<name>/vX.Y.Z` reachable from HEAD, `<name>` being the normalized form `normalize_name()`
    produces.

    NAMESPACED PER ACTOR, ON PURPOSE. A plain `vX.Y.Z` tag is repo-wide — fine for a one-actor
    repo, wrong the moment a second actor's folder lives alongside the first, because then one
    tag would move both actors' semver together even though only one of them changed. Matching
    `<name>/v*` keeps each actor's semver its own, in a repo that may hold several.

    HARD FAILURE, NO FALLBACK. An actor with no matching tag yet has no semver to report, and a
    fabricated `0.1.0` would look identical to a real, decided one.
    """
    folder = Path(folder)
    prefix = normalize_name(name)
    pattern = f"{prefix}/v*"
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", pattern],
        cwd=folder, capture_output=True, text=True,
    )
    tag = result.stdout.strip()
    if result.returncode != 0 or not tag:
        raise ValueError(
            f"{folder}: no tag matching '{pattern}' reachable from HEAD — an actor's semver "
            f"core comes from its own tag, never a declared field; tag it once, e.g. "
            f"`git tag {prefix}/v0.1.0`, before a version can be computed."
        )

    core = tag.removeprefix(f"{prefix}/v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", core):
        raise ValueError(
            f"{folder}: tag '{tag}' does not carry a plain X.Y.Z semver core after '{prefix}/v'"
        )
    return core


def compute(folder: Path | str, name: str, label: str) -> str:
    """The full version string an actor answers to: `{semver}-{label}-{shortSha}` — semver core
    from `semver_base()`, short SHA from `git_version()`, label exactly as the caller supplied
    it, uninterpreted."""
    return f"{semver_base(folder, name)}-{label}-{git_version(folder)}"

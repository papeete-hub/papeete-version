"""Computing one actor's version: `{semver}-{label}-{shortSha}`.

VERSION IS COMPUTED, NEVER DECLARED — nothing here reads or writes a declared `version:` field
anywhere. The semver core comes from the actor's own nearest matching git tag
(`<name>/vX.Y.Z` — GitVersion-style), the short SHA from the folder's own last touching commit,
and the label is a ciType (`alpha`/`beta`/`prod`/`feature`, `ADR-PV-0002`) — `prod` IS GA and
drops the label and shortSha entirely, `feature` prints its own `--feature-name` instead of the
literal word `feature`, because the label is meant to be embodied, not just decorative:
`match_version()` treats a `current_version` whose label doesn't match the requested ciType (or
feature name) as not a candidate at all, regardless of what its semver core says.

Ported from `papeete-actor`'s `build.py` (`ADR-PA-0022`, `ADR-PA-0023`) — see this repo's own
`ADR-PV-0001` for why the computation lives here now, standalone, with nothing Docker-shaped
attached to it.
"""
import re
import subprocess
from pathlib import Path

from . import npm_range

CI_TYPES = ("alpha", "beta", "prod", "feature")
_SHORTSHA = re.compile(r"^[0-9a-f]{7,40}$")


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


def compute(folder: Path | str, name: str, label: str, feature_name: str | None = None) -> str:
    """The full version string an actor answers to.

    `label` is a ciType, not a free-form string anymore: `alpha`, `beta`, `feature` are
    pre-release and print `{semver}-{label}-{shortSha}` — `label` being the ciType itself, or
    `feature_name` (a named label, e.g. the feature branch's own name) when the ciType is
    `feature`. `prod` IS GA: semver-only, no label or shortSha suffix, just `{semver}` — see this
    package's own notes on the alpha/beta/feature/GA progression.
    """
    if label not in CI_TYPES:
        raise ValueError(f"'{label}' is not a ciType papeete-version knows — one of "
                          f"{', '.join(CI_TYPES)}")
    if label == "feature" and not feature_name:
        raise ValueError("ciType 'feature' requires a feature name (--feature-name)")

    base = semver_base(folder, name)
    if label == "prod":
        return base
    resolved_label = feature_name if label == "feature" else label
    return f"{base}-{resolved_label}-{git_version(folder)}"


def _semver_core_of(computed_version: str) -> npm_range.SemVer:
    """The `(major, minor, patch)` a full computed version string (or a bare `X.Y.Z`) leads with —
    `compute()`'s output always has the semver core first, dash-separated from the rest."""
    return npm_range.parse_semver(computed_version.split("-", 1)[0])


def _label_of(computed_version: str) -> str | None:
    """The label a full computed version string carries — everything between the semver core and
    the trailing shortSha, dashes and all (a feature name may itself contain dashes, but the
    shortSha never does, so splitting from the right is unambiguous). `None` for a bare `X.Y.Z`
    (the `prod`/GA shape) or anything else too short to carry a label."""
    parts = computed_version.split("-")
    if len(parts) < 3:
        return None
    return "-".join(parts[1:-1])


def _expected_label(label: str, feature_name: str | None) -> str | None:
    """What `_label_of()` must equal for a version to actually embody this ciType — `None` for
    `prod`, since GA carries no label at all."""
    if label == "prod":
        return None
    return feature_name if label == "feature" else label


def match_version(
    folder: Path | str, name: str, label: str, version: str,
    feature_name: str | None = None, current_version: str | None = None,
) -> str:
    """Fold a `version` query against what git says right now for this actor, `current_version`
    being the accumulator — whatever the caller already had from a previous call.

    `version` is one of:
      - `"latest"` — always the live version, freshly recomputed; `current_version` never matters.
      - a short SHA — the live version, if its own short SHA equals this one exactly.
      - an npm-style range (`^1.2.3`, `~1.2`, `1.x`, `1.2.3`, `>=1.0.0`, ...) — the live version if
        its semver core satisfies the range; otherwise `current_version`, carried forward
        unchanged, if THAT satisfies the range AND actually embodies this ciType — an `alpha`
        query never falls back to a `beta` (or `feature`-named) `current_version` just because its
        semver happens to fit, and a `feature` query requires `current_version`'s own label to be
        THIS feature's name exactly, not merely present.

    Anything else is a hard failure — same no-fallback discipline as `compute()`: a version this
    function can't stand behind is never fabricated or silently substituted.
    """
    live = compute(folder, name, label, feature_name)

    if version == "latest":
        return live

    if _SHORTSHA.match(version):
        sha = git_version(folder)
        if sha == version or sha.startswith(version):
            return live
        raise ValueError(
            f"{folder}: live short SHA '{sha}' does not match requested '{version}'"
        )

    if npm_range.satisfies(_semver_core_of(live), version):
        return live
    expected_label = _expected_label(label, feature_name)
    if (current_version is not None
            and _label_of(current_version) == expected_label
            and npm_range.satisfies(_semver_core_of(current_version), version)):
        return current_version
    raise ValueError(
        f"{folder}: neither the live version ('{live}') nor current_version "
        f"('{current_version}') satisfies '{version}' for ciType '{label}'"
    )

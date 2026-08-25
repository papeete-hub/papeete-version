# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`papeete-version` computes one actor's version string — a semver core read from a git tag, a
ciType-driven label, and a short SHA — for the Papeete ecosystem. It is a pure git computation:
no Docker, no manifest file read, no network call, no state persisted by the package itself.
Ported from `papeete-actor`'s `build.py` (see "Where this came from" in README.md); `papeete-actor`
is not yet wired to depend on this package.

## Commands

```bash
uv run --extra dev pytest -q        # full test suite (what CI runs)
uv run --extra dev pytest -q tests/test_version.py                        # one file
uv run --extra dev pytest -q tests/test_version.py::test_name_of_test     # one test
uv build                            # build sdist/wheel (hatchling)
uv run papeete-version compute path/to/actor --name NAME --label alpha    # run the CLI locally
```

There is no separate lint/format command configured in this repo.

## Architecture

Three modules under `src/papeete_version/`, each with a single responsibility:

- **`version.py`** — all the git/semver logic. `semver_base()` reads the actor's own nearest
  `<normalized-name>/vX.Y.Z` tag (namespaced per actor, since one repo can hold several).
  `git_version()` reads the short SHA of the most recent commit that touched the *folder*, not the
  repo's HEAD. `compute()` combines them per ciType. `match_version()` folds a `--version` query
  (`latest` / a short SHA / an npm-range) against the freshly recomputed live version, falling back
  to a caller-supplied `current_version` only when live doesn't satisfy the query *and* that
  fallback's own label actually embodies the requested ciType (see "label must be embodied" logic
  in `_label_of`/`_expected_label`— an `alpha` query never accepts a `beta`-labelled
  `current_version` even if its semver fits).
- **`npm_range.py`** — a minimal, standalone npm-style range matcher (`satisfies()`), independent of
  `version.py`'s git logic. Supports X-ranges, tilde, caret, single comparators, exact match. Does
  **not** support hyphen ranges, `||` unions, or multiple space-separated comparators — deliberately
  out of scope until a real need appears; don't add them speculatively.
  `README.md`'s "npm-range grammar" table is the normative spec for what this module must accept.
- **`cli.py`** — argparse wiring only, no logic of its own: `compute` and `match-version`
  subcommands both take `FOLDER...` (one or more), `--name`, `--label`. Errors raised as
  `ValueError` anywhere below are caught once in `main()` and reported as `  FAIL {message}` on
  stderr with exit code 2; `--label` outside `alpha/beta/prod/feature` is rejected by argparse
  itself (also exit code 2, different message format).

**Core invariants that any change must preserve** (see README.md "Rules" section for the full
normative spec — treat it as the source of truth over the prose above it, and update it if you
change behavior):

- Version is *computed*, never declared — nothing reads or writes a `version:` field in a
  manifest. The semver core always comes from a git tag.
- `prod` IS GA: semver-only output, no label, no shortSha, ever. The other three ciTypes
  (`alpha`, `beta`, `feature`) always print `{semver}-{label}-{shortSha}`.
- No fabricated fallback: an actor with no matching tag, no commit history, or a query neither
  `live` nor `current_version` can satisfy is a hard `ValueError`, never a guessed placeholder.
- `feature` requires `--feature-name`, which becomes the printed label in place of the literal
  word `feature`.

Design rationale for these invariants lives in `adr/ADR-PV-0001-*.md` (why this package is
standalone) and `adr/ADR-PV-0002-*.md` (ciType-driven labels, GA-is-semver-only, fold-based
`match-version`). Add a new ADR (copy `adr/template.md`) for any decision of similar weight rather
than only writing it into code comments.

## Releasing

Tag-triggered (`v*`) via `.github/workflows/release.yml`, publishing to PyPI through Trusted
Publishing (OIDC) — no stored token. The release job builds the wheel, installs it into a throwaway
venv, and runs a real `compute` against a scratch tagged git repo before publishing, so a broken
entry point fails the release rather than shipping. `ci.yml` runs the test suite and `uv build` on
every push/PR and reaches nothing outside its own checkout.

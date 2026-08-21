# papeete-version

Computes one actor's version — a semver core from its own git tag, a ciType-driven label, and a
short SHA — for the [Papeete](https://github.com/papeete-foundry) ecosystem.

```
papeete-version compute        FOLDER... --name NAME --label CITYPE [--feature-name F]
papeete-version match-version  FOLDER... --name NAME --label CITYPE --version Q
                                [--feature-name F] [--current-version V]
```

```bash
pip install papeete-version
```

## What it computes

```
{semver}-{label}-{shortSha}      # alpha, beta, feature
{semver}                         # prod — GA is semver-only, no suffix
```

| Part | Comes from |
|---|---|
| `semver` | the `X.Y.Z` core of the actor's own nearest `<name>/vX.Y.Z` git tag — namespaced per actor, since one repo can hold several |
| `label` | `--label`, a ciType: `alpha`, `beta`, `prod`, or `feature`. `alpha`/`beta` print themselves as the label; `feature` prints `--feature-name` instead (a named label per feature branch); `prod` IS GA and drops the label and shortSha entirely |
| `shortSha` | the most recent commit that touched the folder (omitted for `prod`) |

```bash
git tag archivist/v0.1.0        # once, before the first computation
papeete-version compute path/to/archivist --name archivist --label alpha
# 0.1.0-alpha-a1b2c3d

papeete-version compute path/to/archivist --name archivist --label feature --feature-name my-branch
# 0.1.0-my-branch-a1b2c3d

papeete-version compute path/to/archivist --name archivist --label prod
# 0.1.0
```

No Docker, no manifest file read, no network — `compute` is a pure git computation over the
folder you point it at. An actor with no matching tag yet, or no commit history at all, gets a
clear, fatal error rather than a fabricated placeholder — see
[ADR-PV-0001](./adr/ADR-PV-0001-a-standalone-version-computation-package.md) for why, and for
this package's own extraction story.

## `match-version` — folding a query against the live state

`match-version` is not a registry lookup — there's still nowhere this package persists a computed
version (see the open question below). Instead it's a pure fold: it recomputes the actor's live
version from git exactly like `compute` does, then resolves `--version` against it:

- `latest` — always the live version; `--current-version` is irrelevant.
- a short SHA — the live version, only if its own short SHA matches exactly.
- an npm-style range (`^1.2.3`, `~1.2`, `1.x`, `1.2.3`, `>=1.0.0`, ...) — the live version if its
  semver core satisfies the range; otherwise `--current-version`, carried forward unchanged, if
  *that* satisfies it instead. Neither satisfying is a hard failure, same as everywhere else in
  this package.

```bash
papeete-version match-version path/to/archivist --name archivist --label alpha \
  --version "^1.0.0" --current-version "1.5.0-alpha-abc0000"
# 1.5.0-alpha-abc0000  (live git state doesn't satisfy ^1.0.0, current-version does)
```

`--current-version` is the caller's own state, passed back in each call — there is still no
persisted history of computed versions inside this package itself. Enumerating every version
ever computed for an actor, or resolving one back to what it came from, remains the open question
below.

## Retrieving a version from a registry — not built yet

`match-version` folds a query against live git state and a caller-supplied prior result; it does
not read from anywhere that stores every version ever computed. Whether such a store should exist
at all, and if so what it looks like — enumerate every tagged version for an actor, resolve an
existing version string back to what it came from, or something else — is still real, wanted, and
deliberately undecided rather than bolted on here as an afterthought — see the open question in
[ADR-PV-0001](./adr/ADR-PV-0001-a-standalone-version-computation-package.md).

## Rules — a precise spec for programmatic/LLM callers

The sections above are the narrative explanation; this section is the exact, unambiguous
contract. Where the two ever disagree, this section is normative — file an issue, it means the
prose above went stale.

### Commands and arguments

| Command | Argument | Required | Values |
|---|---|---|---|
| `compute`, `match-version` | `FOLDER...` (positional, 1+) | yes | path(s) to a git working tree; one line of output per folder, in order |
| `compute`, `match-version` | `--name` | yes | any string; normalized via `normalize_name()` (lowercased, spaces → `-`) before being used to build the tag-match pattern `<normalized-name>/v*` |
| `compute`, `match-version` | `--label` | yes | exactly one of `alpha`, `beta`, `prod`, `feature` — any other value is a CLI-level error (argparse rejects it before any git or logic runs) |
| `compute`, `match-version` | `--feature-name` | conditionally | required if and only if `--label feature`; ignored (may be omitted) for every other `--label` value |
| `match-version` | `--version` | yes | one of: the literal string `latest`; a hex string of 7–40 characters (`[0-9a-f]{7,40}`), treated as a short SHA; or an npm-style range (grammar below) |
| `match-version` | `--current-version` | no | a previously computed version string (e.g. `1.5.0-alpha-abc0000`) or a bare `X.Y.Z`; default: none |

### `compute` algorithm

1. If `--label` is not one of `alpha`/`beta`/`prod`/`feature` → error (`ValueError`, caught by the CLI as exit code 2, message on stderr prefixed `  FAIL `).
2. If `--label feature` and `--feature-name` is empty/absent → error, same as above.
3. `semver = X.Y.Z` from the nearest git tag reachable from `HEAD` matching `<normalize_name(name)>/v*`, its `X.Y.Z` suffix taken verbatim. No matching tag, or a tag whose suffix isn't plain `\d+\.\d+\.\d+` → error.
4. If `--label prod` → print `semver` alone. Stop. (This is the GA case: no label, no shortSha, ever.)
5. Otherwise, `label_out = feature_name if label == "feature" else label`.
6. `shortSha` = the abbreviated hash (`git log -1 --format=%h -- .`) of the most recent commit touching `FOLDER` (not the whole repo's `HEAD`). No commit history for the folder → error.
7. Print `{semver}-{label_out}-{shortSha}`.

### `match-version` algorithm

Recomputes `live = compute(...)` (steps 1–7 above, non-fatal errors here still propagate as
normal `compute` errors), then:

```
if version == "latest":
    return live
if version matches [0-9a-f]{7,40}:
    return live if live's own shortSha == version or live's shortSha startswith(version)
           else ERROR
# otherwise `version` is an npm-style range
if npm_range.satisfies(semver_core(live), version):
    return live
elif (current_version is not None
      and label_of(current_version) == expected_label(label, feature_name)
      and npm_range.satisfies(semver_core(current_version), version)):
    return current_version
else:
    ERROR
```

`semver_core(v)` = the `X.Y.Z` before the first `-` in a version string (or the whole string if
there is no `-`). `label_of(v)` = everything between the semver core and the trailing shortSha
(a feature name may itself contain dashes, so this splits from the *right*, taking the last `-`
as the shortSha boundary — not the first); `None` for a bare `X.Y.Z` with no label at all.
`expected_label(label, feature_name)` = `None` for `prod`, `feature_name` for `feature`, `label`
itself otherwise.

**The label has to be embodied, not just the semver.** A `beta` query never falls back to a
`current_version` labelled `alpha` (or anything else), even if its semver satisfies the range
requested — and a `feature` query requires `current_version`'s label to be *this feature's name*
exactly, not merely present. `live` never has this problem — its label is always built from the
`label`/`feature_name` you passed in, so it inherently already embodies the right ciType. This
check exists purely to keep `current_version` from smuggling in a version that doesn't.

There is no other fallback: a version this algorithm can't stand behind (via `live` or
`current_version`) is never fabricated, averaged, or guessed.

### npm-range grammar accepted by `--version` (and nowhere else)

| Form | Example | Meaning |
|---|---|---|
| exact | `1.2.3` | `== 1.2.3` |
| X-range, major only | `1`, `1.x`, `1.X`, `1.*` | `>=1.0.0 <2.0.0` |
| X-range, major.minor | `1.2`, `1.2.x` | `>=1.2.0 <1.3.0` |
| any | `*`, `x`, `X` | always true |
| tilde | `~1.2.3` | `>=1.2.3 <1.3.0` |
| tilde, partial | `~1.2`, `~1` | `>=1.2.0 <1.3.0` / `>=1.0.0 <2.0.0` |
| caret | `^1.2.3` | `>=1.2.3 <2.0.0` |
| caret, `0.x` major | `^0.2.3` | `>=0.2.3 <0.3.0` |
| caret, `0.0.x` | `^0.0.3` | `>=0.0.3 <0.0.4` |
| comparator | `>=1.2.3`, `<=`, `>`, `<`, `=1.2.3` | as written, against one `X.Y.Z` |

**Not accepted, will raise an error:** hyphen ranges (`1.2.3 - 2.3.4`), `||` unions, multiple
space-separated comparators combined. See `src/papeete_version/npm_range.py` if one of these
becomes a real need — it isn't one yet, so it isn't implemented.

### Errors and exit codes

| Failure | Mechanism | Exit code | Where the message goes |
|---|---|---|---|
| `--label` not in `alpha`/`beta`/`prod`/`feature` | argparse `choices` rejection | 2 | stderr, argparse's own `invalid choice` format |
| Any other failure (`feature` with no `--feature-name`, no matching tag, no commit history, shortSha/range mismatch) | Python `ValueError` caught in `cli.main()` | 2 | stderr, format `  FAIL {message}` |
| Success | — | 0 | stdout, one computed/matched version string per folder, one per line |

### Invariants an LLM can rely on

- Output is **always** either a bare `X.Y.Z` (only for `--label prod`) or exactly
  `X.Y.Z-<label>-<shortSha>` — never any other shape, never partially filled in.
- `compute` and `match-version` are pure functions of git state (+ the caller-supplied
  `--current-version` for `match-version`) — no network calls, no files written, no state
  persisted between invocations by this package itself.
- Nothing here reads a declared `version:` field from any manifest — the semver core always comes
  from a git tag, never from a file.

## Where this came from

Ported from [`papeete-actor`](https://github.com/papeete-hub/papeete-actor)'s `build.py`
(`ADR-PA-0022`, `ADR-PA-0023`), which still carries its own copy of this logic for now —
`papeete-actor` is not yet wired to depend on this package. That cutover is a deliberate, later
decision, not part of standing this repo up.

## Versioning

The tool's own version (this package, on PyPI) and the version strings it *computes* for other
actors are unrelated numbers. `papeete-version --version` prints the former.

## Releasing

Tag-triggered, via [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC).
**No API token is stored anywhere** — GitHub mints a short-lived OIDC token per run and PyPI trades
it for an upload token. There is nothing to rotate and nothing to leak.

```bash
git tag v0.1.0 && git push origin v0.1.0     # .github/workflows/release.yml does the rest
```

### One-time setup — reused from `papeete-actor`'s recipe

**1. A pending publisher on PyPI** — not yet registered. The project doesn't exist on PyPI yet, so
it's registered from the publisher side rather than by a first manual upload. At
<https://pypi.org/manage/account/publishing/>, as a **GitHub** pending publisher:

| Field | Value |
|---|---|
| PyPI Project Name | `papeete-version` |
| Owner | `papeete-hub` |
| Repository name | `papeete-version` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

All five must match exactly — PyPI checks the OIDC claims against them and rejects the upload
otherwise. `release.yml` already declares `permissions: id-token: write` and
`environment: pypi`, which is what makes those claims present. This step needs a human with a PyPI
account and can't be done from the repo itself.

**2. The `pypi` GitHub environment.** No secrets in it — it exists so the OIDC claim carries an
environment name for PyPI to match. Protection rules are **not** set and are worth considering,
because a release is irreversible: PyPI never allows re-uploading a version, even after a delete.
Required reviewers, and restricting deployments to tags matching `v*`, are the two that earn their
keep.

**A private repo is fine.** Trusted Publishing authenticates the *workflow*, not the source, so
nothing here needs to be public for the package to be.

After the first successful release PyPI converts the pending publisher into a normal one
automatically; there is no second setup step.

**Nothing has been published yet.** `papeete-version` is unclaimed on PyPI and the release lane has
never run.

### What a release asserts

The workflow builds, installs the wheel into a clean venv, and computes a version for a throwaway
tagged git repo before publishing — so a build whose entry point is broken fails the release
instead of shipping something that can't actually compute anything.

## Licence

MIT.

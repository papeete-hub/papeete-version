# papeete-version

Computes one actor's version — a semver core from its own git tag, an uninterpreted label, and a
short SHA — for the [Papeete](https://github.com/papeete-foundry) ecosystem.

```
papeete-version compute   FOLDER... --name NAME --label L   print <semver>-<L>-<shortSha>
```

```bash
pip install papeete-version
```

## What it computes

```
{semver}-{label}-{shortSha}
```

| Part | Comes from |
|---|---|
| `semver` | the `X.Y.Z` core of the actor's own nearest `<name>/vX.Y.Z` git tag — namespaced per actor, since one repo can hold several |
| `label` | `--label`, yours, uninterpreted — the taxonomy (`dev`/`rc.1`/`staging`/GA-has-none/...) isn't decided yet |
| `shortSha` | the most recent commit that touched the folder |

```bash
git tag archivist/v0.1.0        # once, before the first computation
papeete-version compute path/to/archivist --name archivist --label dev
# 0.1.0-dev-a1b2c3d
```

No Docker, no manifest file read, no network — `compute` is a pure git computation over the
folder you point it at. An actor with no matching tag yet, or no commit history at all, gets a
clear, fatal error rather than a fabricated placeholder — see
[ADR-PV-0001](./adr/ADR-PV-0001-a-standalone-version-computation-package.md) for why, and for
this package's own extraction story.

## Retrieving a version — not built yet

This package computes a **new** version string from an actor's current git state. It does not
yet **retrieve** one — list what versions already exist for an actor, or resolve an existing
version string back to what it came from. That's real, wanted, and deliberately deferred to its
own design session rather than bolted on here as an afterthought — see the open question in
[ADR-PV-0001](./adr/ADR-PV-0001-a-standalone-version-computation-package.md).

## Where this came from

Ported from [`papeete-actor`](https://github.com/papeete-hub/papeete-actor)'s `build.py`
(`ADR-PA-0022`, `ADR-PA-0023`), which still carries its own copy of this logic for now —
`papeete-actor` is not yet wired to depend on this package. That cutover is a deliberate, later
decision, not part of standing this repo up.

## Versioning

The tool's own version (this package, on PyPI) and the version strings it *computes* for other
actors are unrelated numbers. `papeete-version --version` prints the former.

## Releasing

Not set up yet — this package has never been published. See `papeete-actor`'s own README for the
PyPI Trusted Publishing recipe this repo would reuse when that becomes worth doing.

## Licence

MIT.

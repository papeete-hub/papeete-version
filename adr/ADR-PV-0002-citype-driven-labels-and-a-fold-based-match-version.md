---
id: ADR-PV-0002
title: "ciType-driven labels, GA-is-semver-only, and a fold-based match-version"
status: Accepted
date: 2026-08-21
supersedes: []
references:
  - src/papeete_version/version.py
  - src/papeete_version/npm_range.py
  - src/papeete_version/cli.py
---

# ADR-PV-0002 — ciType-driven labels, GA-is-semver-only, and a fold-based match-version

## Context

`ADR-PV-0001` shipped `compute()` with `--label` as a free-form, uninterpreted string, explicitly
leaving the label taxonomy undecided, and left "retrieving an already-computed version" as
real, wanted, undesigned work.

Two decisions became concrete enough to make: the label taxonomy now has a shape (`alpha` →
`beta` → named labels per feature branch → GA), and GA specifically means a bare semver, no
qualifier. Separately, "retrieve" turned out to conflate two different things once examined:
enumerating/looking up versions from some persisted store (still genuinely undecided — no such
store exists anywhere in this ecosystem yet), and folding a version *query* against the live git
state plus whatever the caller already knew from a previous call (which needs no store at all).
Only the second is decided here.

## Decision

**`--label` becomes a ciType, not free-form.** `version.CI_TYPES = ("alpha", "beta", "prod",
"feature")`. `compute()` now rejects anything else. `alpha`/`beta` print themselves as the label;
`feature` requires `--feature-name` and prints that instead (a named label per feature branch,
not the literal word `feature`); `prod` IS GA and prints `{semver}` alone — no label, no
shortSha.

**A new `match-version` command, built as a fold, not a lookup.** `version.match_version(folder,
name, label, version, feature_name=None, current_version=None)` recomputes the live version
exactly like `compute()`, then resolves the `version` query against it:
- `"latest"` → the live version, always; `current_version` never matters.
- a short SHA → the live version, only if its own short SHA matches exactly.
- an npm-style range → the live version if it satisfies the range, else `current_version`
  (the fold's accumulator, supplied by the caller) if *that* satisfies it AND carries the same
  label the query asked for.

Anything satisfying neither is a hard failure — same no-fallback discipline as the rest of this
package.

**`current_version` must embody the requested ciType, not just fit the semver range.** A `beta`
query never accepts a `current_version` labelled `alpha` (or anything else) as its fallback, even
if the semver satisfies the range — and a `feature` query requires `current_version`'s label to
be *this feature's name* exactly. `live` never has this problem, since it's always built from the
`label`/`feature_name` the caller passed in; the check exists solely to stop `current_version`
from smuggling in a version that doesn't actually match the ciType being asked for.

**A minimal, hand-rolled npm-range subset (`npm_range.py`), no new dependency.** Supports X-ranges
(`1`, `1.2`, `1.2.x`, `*`), tilde, caret, single comparators (`>=`/`<=`/`>`/`<`/`=`), and exact
`X.Y.Z`. Deliberately NOT supported: hyphen ranges, `||` unions, multiple space-separated
comparators — none were asked for, and each is real parsing surface with no concrete need yet.

## Rationale

**Folding beats fetching when there is nothing to fetch from.** The original ask was framed as
"fetch a version" / "fetch all versions that cope with a query," which presumes a store to query.
None exists — `compute()` has only ever printed a string, never persisted one. Rather than invent
a store to justify the verb, `match-version` takes the caller's own prior result as an argument
(`current_version`) and folds the live git truth against it. This is strictly less than a real
retrieval design would need (see Consequences) but is honest about what data actually exists
right now, and needs no new infrastructure to ship.

**A hand-rolled range subset over a dependency.** `dependencies = []` is a deliberate stance this
package has held since `ADR-PV-0001`. Full npm range syntax (hyphen ranges, `||`, pre-release
tags) is real parsing surface this package has no concrete need for yet; the covered subset is
small enough to own directly and test exhaustively (`tests/test_npm_range.py`).

## Consequences

- **Breaking change to `compute()`'s signature and contract.** `--label` no longer accepts
  arbitrary strings (e.g. the old `dev` example throughout the README and tests). Any caller
  relying on a free-form label breaks; there are none outside this repo yet, so no migration is
  needed today.
- **Open — a real persisted registry.** `match-version` still answers nothing about versions this
  package itself never computed and nobody handed it back as `current_version`. Enumerating every
  version ever computed for an actor, or resolving a version string back to the commit/tag it
  came from, remains exactly as undecided as `ADR-PV-0001` left it — this ADR narrows the open
  question, it doesn't close it.
- **The npm-range subset will need to grow, or won't — watch real call sites.** If a caller
  eventually needs hyphen ranges or `||` unions, extend `npm_range.py` deliberately then, rather
  than speculatively now.

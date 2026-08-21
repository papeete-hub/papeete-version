---
id: ADR-PV-0001
title: "A standalone package for computing an actor's version, extracted from papeete-actor"
status: Accepted
date: 2026-08-21
supersedes: []
references:
  - src/papeete_version/version.py
  - src/papeete_version/cli.py
---

# ADR-PV-0001 — A standalone package for computing an actor's version, extracted from papeete-actor

## Context

`papeete-actor`'s `build.py` grew the version-computation logic this repo now carries:
`git_version()` (the short SHA of the last commit touching an actor's folder), `semver_base()`
(the semver core off the actor's own namespaced `<name>/vX.Y.Z` git tag), and their composition
into `{semver}-{label}-{shortSha}` (`ADR-PA-0022`, `ADR-PA-0023` — both in `papeete-actor`).

That logic has nothing Docker-shaped in it — no `docker build`, no image tag, no local image
store. It was living in `papeete-actor` only because that's where the need first showed up. The
intuition driving this split: computing a version, and one day *retrieving* one already computed,
are both going to matter beyond a single actor-building tool, and deserve to evolve on their own
schedule rather than be pulled along by `papeete-actor`'s own Docker-build concerns.

## Decision

**A new, standalone package: `papeete-version`.** `src/papeete_version/version.py` carries
`normalize_name()`, `git_version()`, `semver_base()`, and `compute()` — ported directly from
`papeete-actor`'s `build.py`, same behavior, same tag convention (`<name>/vX.Y.Z`, namespaced per
actor), same hard-fail-no-fallback discipline. `src/papeete_version/cli.py` exposes exactly one
command: `papeete-version compute FOLDER... --name NAME --label L`.

**No dependency on `papeete-actor`'s manifest contract.** `compute()` takes `name` as a plain
argument rather than reading `actor.yaml` — this package doesn't know `papeete-actor-manifest/v0`
exists. It computes a version for *any* git-tracked folder given a name, whether or not that
folder happens to be a papeete actor.

**`papeete-actor` is NOT updated to depend on this package as part of this decision.** Its
`build.py` keeps its own copy of the same logic for now. Cutting `papeete-actor` over — removing
the duplication, importing `papeete_version` instead — is a deliberate, later decision, made once
this package has stood on its own for a while.

## Rationale

**Extraction now, cutover later, as two separate acts.** Standing up a new package and migrating
an existing consumer onto it are different amounts of risk — the first is purely additive, the
second touches something already shipping (`ADR-PA-0021`, `ADR-PA-0023`). Bundling them would
make the extraction's own soundness harder to evaluate on its own, and there is no requirement
that they happen in the same session, or even close together in time.

**No manifest dependency, so this package stays usable by more than papeete actors.** The moment
`compute()` read `actor.yaml` for its `name`, this package would only be usable by things that
already conform to `papeete-actor-manifest/v0` — a much narrower audience than "anything with a
git-tracked folder and a name."

## Consequences

- **Two copies of the same logic exist right now**, in `papeete-actor/src/papeete_actor/build.py`
  and here. This is accepted, temporary duplication — not a defect to fix by reflex, since the
  whole point of this ADR was to decouple the *timing* of extraction from the *timing* of
  cutover.
- **Open — retrieving an already-computed version.** The original ask that motivated this
  package was "build a version number, but also retrieve them." Only the "build" (compute) half
  is designed and built here. What "retrieve" means — enumerate every tagged version for an
  actor, resolve a specific version string back to what it came from, or something else — is
  explicitly undecided, and is real, wanted work for its own session, not something to bolt onto
  `compute` as an afterthought.
- **Open — publishing.** No PyPI registration exists for `papeete-version` yet; `papeete-actor`'s
  README documents the Trusted Publishing recipe this repo would reuse when that becomes worth
  doing.
- **Open — the eventual `papeete-actor` cutover itself.** Not scoped here at all; a future
  decision, likely its own ADR in `papeete-actor`, once this package has proven itself standalone.

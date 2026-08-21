"""papeete-version — computes one actor's version: a semver core (from its own git tag), an
uninterpreted label, and a short SHA.

EXTRACTED FROM papeete-actor (ADR-PA-0022, ADR-PA-0023), STANDALONE FROM DAY ONE (ADR-PV-0001).
`papeete-actor`'s own `build.py` still carries its own copy of this logic for now — this package
is not yet a dependency of it; that cutover is a deliberately separate, later decision.

Retrieving a version already computed for an actor — as opposed to computing a new one — is
future work, not yet designed (ADR-PV-0001's open question).
"""
from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("papeete-version")
except PackageNotFoundError:      # running from a source tree that was never installed
    __version__ = "0.0.0+source"

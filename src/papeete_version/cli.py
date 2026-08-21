"""papeete-version — the CLI. Computes one actor's version, nothing else.

    papeete-version compute        FOLDER... --name NAME --label CITYPE [--feature-name F]
    papeete-version match-version  FOLDER... --name NAME --label CITYPE --version Q
                                    [--feature-name F] [--current-version V]

Both are pure git computations — no Docker, no manifest file read, no network. `--name`
namespaces the git tag looked for (`<name>/vX.Y.Z`). `--label` is a ciType — `alpha`, `beta`,
`feature`, or `prod` — not a free-form string: `alpha`/`beta`/`feature` print
`<semver>-<label>-<shortSha>`, `prod` IS GA and prints `<semver>` alone. `--feature-name` supplies
the named label a feature branch prints instead of the literal word `feature`; required, and only
used, when `--label feature`.

`match-version` folds `--version` (`latest`, a short SHA, or an npm-style range like `^1.2.3`)
against the live git state, falling back to `--current-version` — the caller's own previous
result — only when the live state itself doesn't satisfy the query.
"""
import argparse
import sys
from pathlib import Path

from . import __version__
from . import version as version_mod


def cmd_compute(args) -> int:
    for folder in args.folders:
        print(version_mod.compute(folder, args.name, args.label, args.feature_name))
    return 0


def cmd_match_version(args) -> int:
    for folder in args.folders:
        print(version_mod.match_version(
            folder, args.name, args.label, args.version,
            feature_name=args.feature_name, current_version=args.current_version,
        ))
    return 0


def _add_common_args(p) -> None:
    p.add_argument("folders", nargs="+", type=Path, help="actor folder(s) — each a git working tree")
    p.add_argument("--name", required=True,
                   help="the actor's name — namespaces the git tag looked up (<name>/vX.Y.Z)")
    p.add_argument("--label", required=True, choices=version_mod.CI_TYPES,
                   help="ciType: alpha/beta/feature are pre-release, prod is GA (semver-only)")
    p.add_argument("--feature-name", dest="feature_name", default=None,
                   help="the feature branch's own name — required, and only used, when --label feature")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="papeete-version", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"papeete-version {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("compute", help="compute one actor's <semver>-<label>-<shortSha>")
    _add_common_args(p)
    p.set_defaults(fn=cmd_compute)

    m = sub.add_parser("match-version",
                        help="fold a version query against git's live state")
    _add_common_args(m)
    m.add_argument("--version", dest="version", required=True,
                   help="'latest', a short SHA, or an npm-style range (^1.2.3, ~1.2, 1.x, 1.2.3, >=1.0.0, ...)")
    m.add_argument("--current-version", dest="current_version", default=None,
                   help="the caller's previous result — the fold's accumulator")
    m.set_defaults(fn=cmd_match_version)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except ValueError as e:
        print(f"  FAIL {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""papeete-version — the CLI. Computes one actor's version, nothing else.

    papeete-version compute   FOLDER... --name NAME --label L   print <semver>-<L>-<shortSha>

`compute` is a pure git computation — no Docker, no manifest file read, no network. `--name`
namespaces the git tag it looks for (`<name>/vX.Y.Z`); `--label` is yours, uninterpreted.

Retrieving a version already computed for an actor, rather than computing a new one, is not a
command here yet — left to a future session that designs it deliberately (`ADR-PV-0001`).
"""
import argparse
import sys
from pathlib import Path

from . import __version__
from . import version as version_mod


def cmd_compute(args) -> int:
    for folder in args.folders:
        print(version_mod.compute(folder, args.name, args.label))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="papeete-version", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"papeete-version {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("compute", help="compute one actor's <semver>-<label>-<shortSha>")
    p.add_argument("folders", nargs="+", type=Path, help="actor folder(s) — each a git working tree")
    p.add_argument("--name", required=True,
                   help="the actor's name — namespaces the git tag looked up (<name>/vX.Y.Z)")
    p.add_argument("--label", required=True,
                   help="uninterpreted qualifier (e.g. dev, rc.1, staging) — taxonomy not yet decided")
    p.set_defaults(fn=cmd_compute)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except ValueError as e:
        print(f"  FAIL {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

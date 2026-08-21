"""Minimal npm-style semver range matching, for `match_version`'s `version` query.

Supports what node-semver calls X-ranges (`1`, `1.2`, `1.2.x`, `*`), tilde ranges (`~1.2.3`),
caret ranges (`^1.2.3`), single comparators (`>=`, `<=`, `>`, `<`, `=`), and a bare `X.Y.Z` for an
exact match. NOT supported: hyphen ranges (`1.2.3 - 2.3.4`), `||` unions, or several
space-separated comparators together — none of these were asked for, and each is real parsing
surface with no concrete need yet.
"""
import re

SemVer = tuple[int, int, int]

_EXACT = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_PARTIAL_X = re.compile(r"^(\d+)(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?$")
_TILDE = re.compile(r"^~(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
_CARET = re.compile(r"^\^(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
_COMPARATOR = re.compile(r"^(>=|<=|>|<|=)(\d+)\.(\d+)\.(\d+)$")


def parse_semver(core: str) -> SemVer:
    """A plain `X.Y.Z` string as a comparable `(major, minor, patch)` tuple."""
    m = _EXACT.fullmatch(core)
    if not m:
        raise ValueError(f"'{core}' is not a plain X.Y.Z semver core")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def satisfies(v: SemVer, range_spec: str) -> bool:
    """Whether `v` falls inside the npm-style `range_spec`."""
    range_spec = range_spec.strip()
    if range_spec in ("*", "x", "X"):
        return True

    m = _COMPARATOR.match(range_spec)
    if m:
        op, maj, minor, patch = m.groups()
        target = (int(maj), int(minor), int(patch))
        return {
            ">=": v >= target, "<=": v <= target,
            ">": v > target, "<": v < target, "=": v == target,
        }[op]

    m = _TILDE.match(range_spec)
    if m:
        maj = int(m.group(1))
        minor = int(m.group(2)) if m.group(2) is not None else 0
        patch = int(m.group(3)) if m.group(3) is not None else 0
        lower = (maj, minor, patch)
        upper = (maj, minor + 1, 0) if m.group(2) is not None else (maj + 1, 0, 0)
        return lower <= v < upper

    m = _CARET.match(range_spec)
    if m:
        maj = int(m.group(1))
        minor = int(m.group(2)) if m.group(2) is not None else 0
        patch = int(m.group(3)) if m.group(3) is not None else 0
        lower = (maj, minor, patch)
        if maj > 0:
            upper = (maj + 1, 0, 0)
        elif minor > 0:
            upper = (0, minor + 1, 0)
        else:
            upper = (0, 0, patch + 1)
        return lower <= v < upper

    m = _EXACT.match(range_spec)
    if m:
        return v == (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = _PARTIAL_X.match(range_spec)
    if m:
        maj = int(m.group(1))
        minor_raw, patch_raw = m.group(2), m.group(3)
        if minor_raw is None or minor_raw in ("x", "X", "*"):
            return (maj, 0, 0) <= v < (maj + 1, 0, 0)
        minor = int(minor_raw)
        if patch_raw is None or patch_raw in ("x", "X", "*"):
            return (maj, minor, 0) <= v < (maj, minor + 1, 0)
        return v == (maj, minor, int(patch_raw))

    raise ValueError(f"'{range_spec}' is not a supported npm-style range")

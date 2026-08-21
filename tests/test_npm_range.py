"""npm_range.py — the subset of npm-style semver ranges match_version() understands."""
import pytest

from papeete_version import npm_range


def test_parse_semver_reads_a_plain_core():
    assert npm_range.parse_semver("1.2.3") == (1, 2, 3)


def test_parse_semver_rejects_anything_else():
    with pytest.raises(ValueError, match="not a plain X.Y.Z"):
        npm_range.parse_semver("1.2.3-alpha")


@pytest.mark.parametrize("v,spec", [
    ((1, 2, 3), "1.2.3"),
    ((1, 2, 3), "*"),
    ((1, 2, 3), "1"),
    ((1, 2, 3), "1.2"),
    ((1, 2, 3), "1.2.x"),
    ((1, 2, 3), "1.x"),
    ((1, 2, 3), "^1.2.0"),
    ((1, 9, 9), "^1.2.0"),
    ((1, 2, 3), "~1.2.0"),
    ((1, 2, 9), "~1.2.0"),
    ((0, 2, 3), "^0.2.0"),
    ((0, 0, 3), "^0.0.3"),
    ((1, 2, 3), ">=1.0.0"),
    ((1, 2, 3), "<2.0.0"),
    ((1, 2, 3), "=1.2.3"),
])
def test_satisfies_true_cases(v, spec):
    assert npm_range.satisfies(v, spec) is True


@pytest.mark.parametrize("v,spec", [
    ((2, 0, 0), "1.2.3"),
    ((2, 0, 0), "1.2"),
    ((1, 3, 0), "1.2.x"),
    ((2, 0, 0), "1.x"),
    ((2, 0, 0), "^1.2.0"),
    ((1, 3, 0), "~1.2.0"),
    ((0, 3, 0), "^0.2.0"),
    ((0, 0, 4), "^0.0.3"),
    ((0, 9, 9), ">=1.0.0"),
    ((2, 0, 0), "<2.0.0"),
    ((1, 2, 4), "=1.2.3"),
])
def test_satisfies_false_cases(v, spec):
    assert npm_range.satisfies(v, spec) is False


def test_satisfies_rejects_unsupported_syntax():
    with pytest.raises(ValueError, match="not a supported npm-style range"):
        npm_range.satisfies((1, 0, 0), "1.2.3 - 2.3.4")

"""Tests for _find_repo_root and _check_markers — core traversal logic.

Uses pytest tmp_path to create real directory trees.
"""

import pytest

from odu.bootstrap import _find_repo_root, _check_markers
from odu.exceptions import RepoRootNotFoundError


# ---------------------------------------------------------------------------
# _find_repo_root tests
# ---------------------------------------------------------------------------


class TestFindRepoRootHappyPath:
    """Tests where the repo root IS found."""

    def test_finds_root_at_start_path(self, tmp_path):
        """start_path itself has a marker → returns it."""
        (tmp_path / "src").mkdir()
        result = _find_repo_root(
            str(tmp_path), ["src", "notebooks", "requirements.txt"],
            "at least one", k=1, max_depth=10,
        )
        assert result == str(tmp_path)

    def test_finds_root_one_level_up(self, tmp_path):
        """Marker is in the parent directory of start_path."""
        (tmp_path / "src").mkdir()
        child = tmp_path / "notebooks" / "subfolder"
        child.mkdir(parents=True)
        result = _find_repo_root(
            str(child), ["src"], "at least one", k=1, max_depth=10,
        )
        assert result == str(tmp_path)

    def test_finds_root_multiple_levels_up(self, tmp_path):
        """Marker is several levels above start_path."""
        (tmp_path / "requirements.txt").touch()
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        result = _find_repo_root(
            str(deep), ["requirements.txt"], "at least one", k=1, max_depth=10,
        )
        assert result == str(tmp_path)

    def test_any_single_marker_sufficient(self, tmp_path):
        """Default strategy matches when only one of several markers is present."""
        (tmp_path / "notebooks").mkdir()
        child = tmp_path / "sub"
        child.mkdir()
        result = _find_repo_root(
            str(child), ["src", "notebooks", "requirements.txt"],
            "at least one", k=1, max_depth=10,
        )
        assert result == str(tmp_path)

    def test_custom_markers(self, tmp_path):
        """User-provided custom marker list works."""
        (tmp_path / "pyproject.toml").touch()
        child = tmp_path / "inner"
        child.mkdir()
        result = _find_repo_root(
            str(child), ["pyproject.toml", "setup.cfg"],
            "at least one", k=1, max_depth=10,
        )
        assert result == str(tmp_path)


class TestFindRepoRootStrategies:
    """Tests for different match strategies."""

    def test_at_least_k_strategy_passes(self, tmp_path):
        """At least k markers present → match."""
        (tmp_path / "src").mkdir()
        (tmp_path / "notebooks").mkdir()
        (tmp_path / "requirements.txt").touch()
        child = tmp_path / "sub"
        child.mkdir()
        result = _find_repo_root(
            str(child), ["src", "notebooks", "requirements.txt"],
            "at least k", k=2, max_depth=10,
        )
        assert result == str(tmp_path)

    def test_at_least_k_strategy_fails_insufficient(self, tmp_path):
        """Fewer than k markers in any ancestor → RepoRootNotFoundError.

        Only 1 marker present but k=2 required.
        """
        (tmp_path / "src").mkdir()
        child = tmp_path / "sub"
        child.mkdir()
        with pytest.raises(RepoRootNotFoundError):
            _find_repo_root(
                str(child), ["src", "notebooks", "requirements.txt"],
                "at least k", k=2, max_depth=10,
            )

    def test_all_strategy_passes(self, tmp_path):
        """Every marker present → match."""
        (tmp_path / "src").mkdir()
        (tmp_path / "notebooks").mkdir()
        child = tmp_path / "sub"
        child.mkdir()
        result = _find_repo_root(
            str(child), ["src", "notebooks"],
            "all", k=1, max_depth=10,
        )
        assert result == str(tmp_path)

    def test_all_strategy_partial_fails(self, tmp_path):
        """Only some markers present with 'all' strategy → no match."""
        (tmp_path / "src").mkdir()
        # "notebooks" is missing
        child = tmp_path / "sub"
        child.mkdir()
        with pytest.raises(RepoRootNotFoundError):
            _find_repo_root(
                str(child), ["src", "notebooks"],
                "all", k=1, max_depth=10,
            )


class TestFindRepoRootFailures:
    """Tests where the repo root is NOT found."""

    def test_max_depth_exceeded(self, tmp_path):
        """Raises RepoRootNotFoundError when max_depth is exhausted."""
        # Create a deep tree with no markers anywhere
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        with pytest.raises(RepoRootNotFoundError):
            _find_repo_root(
                str(deep), ["src"], "at least one", k=1, max_depth=2,
            )

    def test_filesystem_root_reached(self):
        """Raises RepoRootNotFoundError when reaching filesystem root.

        Starting from root itself with a marker that doesn't exist there.
        """
        with pytest.raises(RepoRootNotFoundError):
            _find_repo_root(
                "/", ["this_marker_certainly_does_not_exist_xyz123"],
                "at least one", k=1, max_depth=100,
            )

    def test_no_markers_in_any_ancestor(self, tmp_path):
        """No markers exist anywhere in the tree → RepoRootNotFoundError."""
        child = tmp_path / "empty_child"
        child.mkdir()
        with pytest.raises(RepoRootNotFoundError):
            _find_repo_root(
                str(child), ["src", "notebooks"],
                "at least one", k=1, max_depth=10,
            )


class TestFindRepoRootValidation:
    """Tests for input validation."""

    def test_invalid_strategy_raises(self, tmp_path):
        """Unknown strategy string → ValueError."""
        with pytest.raises(ValueError, match="match_strategy"):
            _find_repo_root(
                str(tmp_path), ["src"], "bogus strategy", k=1, max_depth=10,
            )

    def test_invalid_k_too_low(self, tmp_path):
        """k=0 → ValueError."""
        with pytest.raises(ValueError, match="k"):
            _find_repo_root(
                str(tmp_path), ["src"], "at least k", k=0, max_depth=10,
            )

    def test_invalid_k_too_high(self, tmp_path):
        """k > len(markers) → ValueError."""
        with pytest.raises(ValueError, match="k"):
            _find_repo_root(
                str(tmp_path), ["src"], "at least k", k=5, max_depth=10,
            )


# ---------------------------------------------------------------------------
# _check_markers tests
# ---------------------------------------------------------------------------


class TestCheckMarkers:
    """Direct tests for _check_markers."""

    def test_at_least_one_with_one_present(self, tmp_path):
        (tmp_path / "src").mkdir()
        assert _check_markers(str(tmp_path), ["src", "notebooks"], "at least one", k=1) is True

    def test_at_least_one_with_none_present(self, tmp_path):
        assert _check_markers(str(tmp_path), ["src", "notebooks"], "at least one", k=1) is False

    def test_at_least_k_exact(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "notebooks").mkdir()
        assert _check_markers(str(tmp_path), ["src", "notebooks", "requirements.txt"], "at least k", k=2) is True

    def test_at_least_k_insufficient(self, tmp_path):
        (tmp_path / "src").mkdir()
        assert _check_markers(str(tmp_path), ["src", "notebooks", "requirements.txt"], "at least k", k=2) is False

    def test_all_with_all_present(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "notebooks").mkdir()
        assert _check_markers(str(tmp_path), ["src", "notebooks"], "all", k=1) is True

    def test_all_with_one_missing(self, tmp_path):
        (tmp_path / "src").mkdir()
        assert _check_markers(str(tmp_path), ["src", "notebooks"], "all", k=1) is False

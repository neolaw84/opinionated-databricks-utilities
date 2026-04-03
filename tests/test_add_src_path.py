"""Tests for add_src_path_to_sys_path — sys.path management.

Uses a mock sys_module to avoid polluting the real sys.path.
"""

import os
import types

import pytest

from odu.bootstrap import add_src_path_to_sys_path


def _make_sys_module(initial_path: list[str] | None = None) -> types.SimpleNamespace:
    """Create a mock sys module with a mutable path list."""
    return types.SimpleNamespace(path=list(initial_path or []))


class TestAddSrcPathFromString:
    """Tests when fs is a string (repo root)."""

    def test_adds_src_from_string(self, tmp_path):
        """str input → adds repo_root/src to sys.path."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        mock_sys = _make_sys_module()

        add_src_path_to_sys_path(str(tmp_path), mock_sys)

        assert str(src_dir) in mock_sys.path

    def test_idempotent_no_duplicate(self, tmp_path):
        """Calling twice doesn't duplicate the entry."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        mock_sys = _make_sys_module()

        add_src_path_to_sys_path(str(tmp_path), mock_sys)
        add_src_path_to_sys_path(str(tmp_path), mock_sys)

        assert mock_sys.path.count(str(src_dir)) == 1

    def test_nonexistent_src_path_raises(self, tmp_path):
        """src/ doesn't exist on disk → FileNotFoundError."""
        mock_sys = _make_sys_module()
        # tmp_path exists but tmp_path/src does not
        with pytest.raises(FileNotFoundError):
            add_src_path_to_sys_path(str(tmp_path), mock_sys)


class TestAddSrcPathFromDict:
    """Tests when fs is a dict (from repo_root_finder with returns=)."""

    def test_adds_src_from_dict(self, tmp_path):
        """dict input → uses src_path value."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        mock_sys = _make_sys_module()

        fs = {"repo_root": str(tmp_path), "src_path": str(src_dir)}
        add_src_path_to_sys_path(fs, mock_sys)

        assert str(src_dir) in mock_sys.path

    def test_dict_missing_src_path_raises(self, tmp_path):
        """dict without src_path key → ValueError."""
        mock_sys = _make_sys_module()
        fs = {"repo_root": str(tmp_path)}

        with pytest.raises(ValueError, match="src_path"):
            add_src_path_to_sys_path(fs, mock_sys)

    def test_dict_none_src_path_raises(self, tmp_path):
        """dict with src_path=None → ValueError."""
        mock_sys = _make_sys_module()
        fs = {"repo_root": str(tmp_path), "src_path": None}

        with pytest.raises(ValueError, match="src_path"):
            add_src_path_to_sys_path(fs, mock_sys)


class TestAddSrcPathTypeErrors:
    """Tests for unexpected input types."""

    def test_unexpected_type_raises(self):
        """Non-str/dict → TypeError."""
        mock_sys = _make_sys_module()
        with pytest.raises(TypeError):
            add_src_path_to_sys_path(12345, mock_sys)

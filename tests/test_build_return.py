"""Tests for _build_return_value — return value construction.

Uses tmp_path to verify existence checks.
"""

import pytest

from odu.bootstrap import _build_return_value, KNOWN_PATH_KEYS


class TestBuildReturnNone:
    """Tests when returns=None."""

    def test_none_returns_string(self, tmp_path):
        """returns=None → plain str (the repo root)."""
        result = _build_return_value(str(tmp_path), returns=None)
        assert result == str(tmp_path)
        assert isinstance(result, str)


class TestBuildReturnAll:
    """Tests when returns='all'."""

    def test_all_returns_full_dict(self, tmp_path):
        """returns='all' → dict with all known keys."""
        (tmp_path / "src").mkdir()
        (tmp_path / "requirements.txt").touch()
        result = _build_return_value(str(tmp_path), returns="all")

        assert isinstance(result, dict)
        assert "repo_root" in result
        assert "notebook_path" in result
        assert "src_path" in result
        assert "requirements_path" in result
        assert "notebooks_dir_path" in result
        assert "configs_path" in result
        assert "resources_path" in result
        assert "databricks_resources_path" in result

    def test_existing_paths_populated(self, tmp_path):
        """Existing dirs/files get their full path as value."""
        (tmp_path / "src").mkdir()
        (tmp_path / "requirements.txt").touch()
        result = _build_return_value(str(tmp_path), returns="all")

        assert result["repo_root"] == str(tmp_path)
        assert result["src_path"] == str(tmp_path / "src")
        assert result["requirements_path"] == str(tmp_path / "requirements.txt")

    def test_missing_paths_none(self, tmp_path):
        """Non-existent dirs/files → None."""
        # Don't create any markers
        result = _build_return_value(str(tmp_path), returns="all")

        assert result["repo_root"] == str(tmp_path)
        assert result["src_path"] is None
        assert result["notebooks_dir_path"] is None
        assert result["requirements_path"] is None
        assert result["databricks_resources_path"] is None
        # notebook_path is None when not provided
        assert result["notebook_path"] is None


class TestBuildReturnList:
    """Tests when returns is a list of keys."""

    def test_list_returns_selective_dict(self, tmp_path):
        """returns=['src_path'] → dict with repo_root + requested key only."""
        (tmp_path / "src").mkdir()
        result = _build_return_value(str(tmp_path), returns=["src_path"])

        assert isinstance(result, dict)
        assert "repo_root" in result
        assert "src_path" in result
        assert "notebooks_dir_path" not in result
        assert "configs_path" not in result

    def test_notebook_path_populated_from_arg(self, tmp_path):
        """notebook_path in dict comes from the notebook_path arg, not filesystem."""
        nb_path = "/Workspace/Repos/user/repo/notebooks/my_nb"
        result = _build_return_value(
            str(tmp_path), returns="all", notebook_path=nb_path
        )
        assert result["notebook_path"] == nb_path

    def test_databricks_resources_path_populated(self, tmp_path):
        """databricks-resources dir → databricks_resources_path key."""
        (tmp_path / "databricks-resources").mkdir()
        result = _build_return_value(str(tmp_path), returns="all")
        assert result["databricks_resources_path"] == str(tmp_path / "databricks-resources")

    def test_repo_root_always_included(self, tmp_path):
        """Dict always contains repo_root key, even if not in the list."""
        result = _build_return_value(str(tmp_path), returns=["configs_path"])
        assert "repo_root" in result

    def test_invalid_key_in_list_raises(self, tmp_path):
        """Unknown key in returns list → ValueError."""
        with pytest.raises(ValueError, match="unknown_key"):
            _build_return_value(str(tmp_path), returns=["unknown_key"])

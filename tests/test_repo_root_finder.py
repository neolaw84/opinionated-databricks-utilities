"""Tests for repo_root_finder — the public API orchestration.

Uses mock dbutils + tmp_path.
"""

import pytest
from unittest.mock import MagicMock, patch

from odu.bootstrap import repo_root_finder
from odu.exceptions import RepoRootNotFoundError, NotebookPathError


def _make_mock_dbutils(notebook_path: str) -> MagicMock:
    """Create a mock dbutils that returns the given notebook path.

    The real call chain is:
        dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
    """
    mock = MagicMock()
    (
        mock.notebook.entry_point
        .getDbutils.return_value
        .notebook.return_value
        .getContext.return_value
        .notebookPath.return_value
        .get.return_value
    ) = notebook_path
    return mock


class TestRepoRootFinderReturns:
    """Tests for the returns parameter."""

    def test_default_returns_string(self, tmp_path):
        """returns=None → returns repo root as str."""
        (tmp_path / "src").mkdir()
        # Simulate notebook at tmp_path/notebooks/my_notebook
        nb_dir = tmp_path / "notebooks"
        nb_dir.mkdir()
        nb_file = nb_dir / "my_notebook"
        nb_file.touch()

        # dbutils returns path WITHOUT /Workspace/ — the function prepends it.
        # But since /Workspace/ won't exist on the test machine, we mock
        # _get_notebook_dir to return the real tmp path.
        with patch("odu.bootstrap._get_notebook_dir", return_value=str(nb_dir)):
            result = repo_root_finder(
                _make_mock_dbutils(str(nb_file)),
            )
        assert result == str(tmp_path)
        assert isinstance(result, str)

    def test_returns_all_dict(self, tmp_path):
        """returns='all' → dict with all keys."""
        (tmp_path / "src").mkdir()
        (tmp_path / "notebooks").mkdir()
        (tmp_path / "requirements.txt").touch()
        child = tmp_path / "notebooks"

        with patch("odu.bootstrap._get_notebook_dir", return_value=str(child)):
            result = repo_root_finder(
                _make_mock_dbutils("dummy"),
                returns="all",
            )
        assert isinstance(result, dict)
        assert result["repo_root"] == str(tmp_path)
        assert result["src_path"] == str(tmp_path / "src")
        assert result["requirements_path"] == str(tmp_path / "requirements.txt")
        assert result["notebooks_dir_path"] == str(tmp_path / "notebooks")

    def test_returns_selective_list(self, tmp_path):
        """returns=["src_path"] → dict with repo_root + src_path."""
        (tmp_path / "src").mkdir()
        child = tmp_path / "sub"
        child.mkdir()

        with patch("odu.bootstrap._get_notebook_dir", return_value=str(child)):
            result = repo_root_finder(
                _make_mock_dbutils("dummy"),
                returns=["src_path"],
            )
        assert isinstance(result, dict)
        assert "repo_root" in result
        assert "src_path" in result
        # Keys not requested should not be present
        assert "notebooks_dir_path" not in result

    def test_dict_values_none_for_missing(self, tmp_path):
        """Non-existent paths have None values in the returned dict."""
        (tmp_path / "src").mkdir()  # only src exists
        child = tmp_path / "sub"
        child.mkdir()

        with patch("odu.bootstrap._get_notebook_dir", return_value=str(child)):
            result = repo_root_finder(
                _make_mock_dbutils("dummy"),
                returns="all",
            )
        assert result["repo_root"] == str(tmp_path)
        assert result["src_path"] == str(tmp_path / "src")
        assert result["notebooks_dir_path"] is None  # doesn't exist
        assert result["requirements_path"] is None
        assert result["databricks_resources_path"] is None

    def test_repo_root_always_in_dict(self, tmp_path):
        """repo_root key is always present even with selective returns."""
        (tmp_path / "src").mkdir()
        child = tmp_path / "sub"
        child.mkdir()

        with patch("odu.bootstrap._get_notebook_dir", return_value=str(child)):
            result = repo_root_finder(
                _make_mock_dbutils("dummy"),
                returns=["configs_path"],
            )
        assert "repo_root" in result


class TestRepoRootFinderIntegration:
    """Tests for dbutils interaction and strategy forwarding."""

    def test_workspace_prefix_applied(self, tmp_path):
        """Notebook path gets /Workspace/ prepended in _get_notebook_dir.

        We test that _get_notebook_dir is called (not directly testing the
        prefix here since we mock _get_notebook_dir for filesystem reasons).
        """
        (tmp_path / "src").mkdir()
        child = tmp_path / "sub"
        child.mkdir()

        with patch("odu.bootstrap._get_notebook_dir", return_value=str(child)) as mock_get:
            repo_root_finder(_make_mock_dbutils("dummy"))
        mock_get.assert_called_once()

    def test_dbutils_error_raises_notebook_path_error(self):
        """dbutils exception → NotebookPathError."""
        mock_dbutils = MagicMock()
        mock_dbutils.notebook.entry_point.getDbutils.side_effect = Exception("no context")

        # Don't mock _get_notebook_dir — let it call dbutils and fail
        with pytest.raises(NotebookPathError):
            repo_root_finder(mock_dbutils)

    def test_match_strategy_forwarded(self, tmp_path):
        """Strategy param reaches _find_repo_root correctly."""
        # Only 1 marker present, but require 2 → should fail
        (tmp_path / "src").mkdir()
        child = tmp_path / "sub"
        child.mkdir()

        with patch("odu.bootstrap._get_notebook_dir", return_value=str(child)):
            with pytest.raises(RepoRootNotFoundError):
                repo_root_finder(
                    _make_mock_dbutils("dummy"),
                    match_strategy="at least k",
                    k=2,
                )

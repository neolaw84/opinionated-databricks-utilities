"""Bootstrap utilities for Databricks notebook workspace setup.

Public API:
    - repo_root_finder(dbutils, ...) -> str | dict
    - add_src_path_to_sys_path(fs, sys_module) -> None
"""

from __future__ import annotations

import os
import types
from typing import Any

from odu.exceptions import NotebookPathError, RepoRootNotFoundError

DEFAULT_MARKERS = ["src", "notebooks", "requirements.txt"]

KNOWN_PATH_KEYS = {
    "repo_root",
    "notebook_path",              # the notebook file itself
    "src_path",
    "requirements_path",
    "notebooks_dir_path",         # renamed from notebooks_path
    "configs_path",
    "resources_path",
    "databricks_resources_path",
}

# Map from dict key to the relative path segment within repo root.
# notebook_path is special — it comes from dbutils, not from repo root.
_KEY_TO_RELATIVE = {
    "src_path": "src",
    "requirements_path": "requirements.txt",
    "notebooks_dir_path": "notebooks",
    "configs_path": "configs",
    "resources_path": "resources",
    "databricks_resources_path": "databricks-resources",
}

_VALID_STRATEGIES = {"at least one", "at least k", "all"}


def repo_root_finder(
    dbutils: Any,
    match_strategy: str = "at least one",
    *,
    markers: list[str] | None = None,
    k: int = 1,
    max_depth: int = 10,
    returns: str | list[str] | None = None,
) -> str | dict[str, str | None]:
    """Find the repository root from a Databricks notebook context.

    Args:
        dbutils: Databricks dbutils object.
        match_strategy: "at least one" | "at least k" | "all".
        markers: Marker files/dirs to identify repo root.
                 Default: ["src", "notebooks", "requirements.txt"].
        k: Minimum markers required for "at least k" strategy.
        max_depth: Max directories to traverse upward.
        returns: None -> repo_root str.
                 "all" -> dict of all discovered paths.
                 list[str] -> dict of requested path keys only.

                 Available dict keys:
                   repo_root                 — the discovered repo root
                   notebook_path             — the notebook file path (from dbutils)
                   src_path                  — repo_root/src
                   requirements_path         — repo_root/requirements.txt
                   notebooks_dir_path        — repo_root/notebooks
                   configs_path              — repo_root/configs
                   resources_path            — repo_root/resources
                   databricks_resources_path — repo_root/databricks-resources

    Returns:
        Repo root path (str) or dict of paths (None values for non-existent
        paths, except notebook_path which comes from dbutils).

    Raises:
        RepoRootNotFoundError: If repo root cannot be found.
        NotebookPathError: If notebook path cannot be retrieved from dbutils.
        ValueError: If match_strategy or k is invalid.
    """
    resolved_markers = markers if markers is not None else DEFAULT_MARKERS

    # Get notebook directory via helper (raises NotebookPathError on failure).
    # Using _get_notebook_dir so tests can patch it cleanly.
    notebook_dir = _get_notebook_dir(dbutils)

    # Also retrieve the full notebook path for the return dict.
    # If returns=None we skip this to avoid a second dbutils call.
    if returns is not None:
        try:
            notebook_path = _get_notebook_path(dbutils)
        except NotebookPathError:
            notebook_path = None
    else:
        notebook_path = None

    repo_root = _find_repo_root(
        notebook_dir, resolved_markers, match_strategy, k, max_depth
    )

    return _build_return_value(repo_root, returns, notebook_path=notebook_path)


def add_src_path_to_sys_path(fs: str | dict[str, str | None], sys_module: types.ModuleType) -> None:
    """Add the src directory to sys.path.

    Args:
        fs: Either a str (repo_root) or dict (from repo_root_finder with returns=).
            If str: constructs src path as fs + "/src".
            If dict: uses fs["src_path"].
        sys_module: The sys module (injected for testability).

    Raises:
        ValueError: If fs is a dict but "src_path" key is missing or None.
        FileNotFoundError: If the src path does not exist on the filesystem.
        TypeError: If fs is neither str nor dict.
    """
    if isinstance(fs, str):
        src_path = os.path.join(fs, "src")
    elif isinstance(fs, dict):
        if "src_path" not in fs or fs["src_path"] is None:
            raise ValueError(
                "'src_path' key is missing or None in the provided dict. "
                "Call repo_root_finder with returns='all' or returns=['src_path'] "
                "to populate it."
            )
        src_path = fs["src_path"]
    else:
        raise TypeError(
            f"fs must be a str (repo root) or dict (from repo_root_finder), "
            f"got {type(fs).__name__!r}"
        )

    if not os.path.exists(src_path):
        raise FileNotFoundError(
            f"src directory does not exist: {src_path!r}"
        )

    if src_path not in sys_module.path:
        sys_module.path.insert(0, src_path)


def _get_notebook_path(dbutils) -> str:
    """Extract the full notebook file path from dbutils, with /Workspace/ prefix.

    Returns:
        Full notebook path, e.g. "/Workspace/Repos/user/repo/notebooks/my_nb"

    Raises:
        NotebookPathError: If dbutils raises any exception.
    """
    try:
        raw_path = (
            dbutils.notebook.entry_point
            .getDbutils()
            .notebook()
            .getContext()
            .notebookPath()
            .get()
        )
    except Exception as exc:
        raise NotebookPathError(
            f"Failed to retrieve notebook path from dbutils: {exc}"
        ) from exc

    # Databricks returns paths like "/Repos/user/repo/notebooks/nb"
    # For filesystem operations, /Workspace/ must be prepended.
    if not raw_path.startswith("/Workspace"):
        return "/Workspace" + raw_path
    return raw_path


def _get_notebook_dir(dbutils) -> str:
    """Return the directory containing the notebook (with /Workspace/ prefix).

    This thin wrapper exists so tests can patch it without touching dbutils.
    """
    return os.path.dirname(_get_notebook_path(dbutils))


def _find_repo_root(
    start_path: str,
    markers: list[str],
    match_strategy: str,
    k: int,
    max_depth: int,
) -> str:
    """Walk upward from start_path to find repo root. Pure filesystem logic.

    Args:
        start_path: Directory to begin traversal from.
        markers: Files/dirs used to identify the repo root.
        match_strategy: "at least one" | "at least k" | "all".
        k: Required marker count for "at least k".
        max_depth: Maximum number of directories to check (including start).

    Returns:
        Absolute path of the repo root directory.

    Raises:
        ValueError: If match_strategy is invalid or k is out of range.
        RepoRootNotFoundError: If no matching directory is found.
    """
    # Validate strategy and k up-front
    if match_strategy not in _VALID_STRATEGIES:
        raise ValueError(
            f"Invalid match_strategy {match_strategy!r}. "
            f"Must be one of: {sorted(_VALID_STRATEGIES)}"
        )
    if match_strategy == "at least k":
        if k < 1 or k > len(markers):
            raise ValueError(
                f"k={k} is out of range for match_strategy='at least k'. "
                f"Must satisfy 1 <= k <= len(markers) (={len(markers)})."
            )

    current = os.path.abspath(start_path)
    for _ in range(max_depth):
        if _check_markers(current, markers, match_strategy, k):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    raise RepoRootNotFoundError(
        f"Could not find repository root starting from {start_path!r}. "
        f"Searched up to {max_depth} levels. "
        f"Markers: {markers}, strategy: {match_strategy!r}."
    )


def _check_markers(
    directory: str,
    markers: list[str],
    match_strategy: str,
    k: int,
) -> bool:
    """Check if directory matches the marker criteria.

    Args:
        directory: Absolute path to check.
        markers: The marker file/dir names to look for.
        match_strategy: "at least one" | "at least k" | "all".
        k: Required count for "at least k".

    Returns:
        True if the directory satisfies the marker criteria.
    """
    try:
        contents = set(os.listdir(directory))
    except PermissionError:
        return False

    found = sum(1 for m in markers if m in contents)

    if match_strategy == "at least one":
        return found >= 1
    elif match_strategy == "at least k":
        return found >= k
    elif match_strategy == "all":
        return found == len(markers)
    return False  # unreachable if validated upstream


def _build_return_value(
    repo_root: str,
    returns: str | list[str] | None,
    notebook_path: str | None = None,
) -> str | dict[str, str | None]:
    """Build the return value based on the returns parameter.

    Args:
        repo_root: The discovered repository root path.
        returns: None | "all" | list of key names.
        notebook_path: Full notebook file path (from dbutils). Populated in
                       the dict when "notebook_path" is requested.
    """
    if returns is None:
        return repo_root

    if returns == "all":
        keys = list(KNOWN_PATH_KEYS - {"repo_root"})
    elif isinstance(returns, list):
        unknown = [k for k in returns if k not in KNOWN_PATH_KEYS]
        if unknown:
            raise ValueError(
                f"Unknown key(s) in returns: {unknown}. "
                f"Valid keys are: {sorted(KNOWN_PATH_KEYS)}"
            )
        keys = returns
    else:
        raise ValueError(
            f"returns must be None, 'all', or a list of key names, got {returns!r}"
        )

    result: dict[str, str | None] = {"repo_root": repo_root}

    for key in keys:
        if key == "repo_root":
            continue  # already set
        if key == "notebook_path":
            result[key] = notebook_path
        else:
            relative = _KEY_TO_RELATIVE[key]
            full_path = os.path.join(repo_root, relative)
            result[key] = full_path if os.path.exists(full_path) else None

    return result

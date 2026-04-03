# User Guide

## Background

Most Databricks repositories have a structure similar to:

```
my-repo/
├── configs/
├── resources/
├── databricks-resources/
├── notebooks/
├── src/
├── pyproject.toml
├── requirements.txt
└── README.md
```

When a notebook runs **interactively**, the current working directory is the notebook's
own directory, so relative paths and `pip install -r requirements.txt` work normally.

When the same notebook runs **as a Databricks workflow task**, the current working
directory is a random location on the cluster. Imports break, and you cannot find
`requirements.txt`.

ODU provides two utilities to fix this:

- **`repo_root_finder`** — walks up from the notebook's location to find the repository root.
- **`add_src_path_to_sys_path`** — adds `src/` to `sys.path` so your packages are importable.

---

## Installation

```bash
pip install odu
```

---

## Usage

### The Two-Cell Pattern

Because `dbutils.library.restartPython()` wipes the Python context, you need two cells.

**Cell 1 — Install requirements (runs once, then triggers a restart)**

```python
import sys
from odu.bootstrap import repo_root_finder, add_src_path_to_sys_path

# Find repository root (returns repo root as a string by default)
repo_root = repo_root_finder(dbutils)
print(f"Repo root: {repo_root}")

# Install dependencies
%pip install -r {repo_root}/requirements.txt

# Restart Python to make new packages available
dbutils.library.restartPython()
```

**Cell 2 — Set up sys.path (after restart)**

```python
import sys
from odu.bootstrap import repo_root_finder, add_src_path_to_sys_path

repo_root = repo_root_finder(dbutils)
add_src_path_to_sys_path(repo_root, sys)

# Now import from src/ as normal
from my_package import my_module
```

---

## `repo_root_finder` Reference

```python
repo_root_finder(
    dbutils,
    match_strategy="at least one",
    *,
    markers=None,
    k=1,
    max_depth=10,
    returns=None,
)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dbutils` | object | *required* | The Databricks `dbutils` object. |
| `match_strategy` | `str` | `"at least one"` | How many markers must be present to identify the repo root. One of `"at least one"`, `"at least k"`, `"all"`. |
| `markers` | `list[str]` | `["src", "notebooks", "requirements.txt"]` | File/directory names that identify the repository root. |
| `k` | `int` | `1` | Minimum number of markers required when using `"at least k"` strategy. |
| `max_depth` | `int` | `10` | Maximum number of parent directories to check. |
| `returns` | `None \| "all" \| list[str]` | `None` | Controls the return type. See below. |

### Return Value

| `returns` value | Return type | Description |
|---|---|---|
| `None` (default) | `str` | Repository root path. |
| `"all"` | `dict` | All discovered paths (see keys below). |
| `list[str]` | `dict` | Only the requested keys (plus `repo_root` always). |

### Dict Keys (when `returns="all"` or a list)

| Key | Path |
|---|---|
| `repo_root` | The discovered repository root (always present) |
| `notebook_path` | The notebook file itself (from `dbutils`) |
| `src_path` | `repo_root/src` |
| `requirements_path` | `repo_root/requirements.txt` |
| `notebooks_dir_path` | `repo_root/notebooks` |
| `configs_path` | `repo_root/configs` |
| `resources_path` | `repo_root/resources` |
| `databricks_resources_path` | `repo_root/databricks-resources` |

!!! note
    Dict values are `None` when the corresponding path does not exist on disk.

### Examples

```python
# Default: returns repo root as a string
repo_root = repo_root_finder(dbutils)

# All paths as a dict
fs = repo_root_finder(dbutils, returns="all")
print(fs["src_path"])           # /Workspace/Repos/.../src
print(fs["requirements_path"])  # /Workspace/Repos/.../requirements.txt

# Selective keys
fs = repo_root_finder(dbutils, returns=["src_path", "requirements_path"])

# Custom markers, require at least 2
repo_root = repo_root_finder(
    dbutils,
    match_strategy="at least k",
    k=2,
    markers=["src", "notebooks", "requirements.txt", "pyproject.toml"],
)
```

---

## `add_src_path_to_sys_path` Reference

```python
add_src_path_to_sys_path(fs, sys_module)
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `fs` | `str \| dict` | Either a repo root string or a dict from `repo_root_finder`. |
| `sys_module` | module | The `sys` module. Always pass `sys` explicitly. |

- If `fs` is a **`str`**, the function adds `fs + "/src"` to `sys.path`.
- If `fs` is a **`dict`**, the function uses `fs["src_path"]`. Raises `ValueError` if `src_path` is missing or `None`.

### Errors

| Exception | Cause |
|---|---|
| `FileNotFoundError` | The `src/` directory does not exist on disk. |
| `ValueError` | `fs` is a dict but `src_path` is missing or `None`. |
| `TypeError` | `fs` is not a `str` or `dict`. |

---

## Exceptions

Both functions may raise the following ODU-specific exceptions:

| Exception | When raised |
|---|---|
| `odu.exceptions.RepoRootNotFoundError` | No repo root found within `max_depth` levels. |
| `odu.exceptions.NotebookPathError` | `dbutils` call failed (e.g., running outside Databricks). |
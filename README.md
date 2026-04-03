# Opinionated Databricks Utilities (ODU)

[![PyPI version](https://badge.fury.io/py/odu.svg)](https://badge.fury.io/py/odu)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

ODU is a collection of opinionated utilities for working on the Databricks platform.

## The Problem

When Databricks notebooks run as workflow tasks, the current working directory is a random location on the cluster — **not** the directory where your notebook lives. This breaks relative imports and `pip install -r requirements.txt`.

ODU solves this by providing utilities to:
1. Locate your repository root from inside a running notebook.
2. Add your `src/` directory to `sys.path`.

## Installation

```bash
pip install odu
```

## Quick Start

Add these two cells at the top of every notebook that runs as a workflow task.

**Cell 1 — Before restart:**
```python
import sys
from odu.bootstrap import repo_root_finder, add_src_path_to_sys_path

repo_root = repo_root_finder(dbutils)

# Install requirements and restart Python to make them effective
%pip install -r {repo_root}/requirements.txt
dbutils.library.restartPython()
```

**Cell 2 — After restart:**
```python
import sys
from odu.bootstrap import repo_root_finder, add_src_path_to_sys_path

repo_root = repo_root_finder(dbutils)
add_src_path_to_sys_path(repo_root, sys)

# Now your src/ packages are importable
from my_package import my_module
```

## Advanced Usage

```python
# Get all repo paths as a dict
fs = repo_root_finder(dbutils, returns="all")
# {
#   "repo_root":                 "/Workspace/Repos/user/my-repo",
#   "notebook_path":             "/Workspace/Repos/user/my-repo/notebooks/my_nb",
#   "src_path":                  "/Workspace/Repos/user/my-repo/src",
#   "requirements_path":         "/Workspace/Repos/user/my-repo/requirements.txt",
#   "notebooks_dir_path":        "/Workspace/Repos/user/my-repo/notebooks",
#   "configs_path":              None,  # (doesn't exist)
#   "resources_path":            None,
#   "databricks_resources_path": None,
# }

add_src_path_to_sys_path(fs, sys)  # works with both str and dict

# Custom markers and matching strategy
repo_root = repo_root_finder(
    dbutils,
    match_strategy="at least k",
    k=2,
    markers=["src", "notebooks", "requirements.txt", "pyproject.toml"],
)
```

## Documentation

Full documentation is available at the [GitHub Pages site](https://neolaw84.github.io/opinionated-databricks-utilities/).

## License

[MIT](LICENSE)

# Developer Guide

## Development Setup

1. Clone the repository:

```bash
git clone https://github.com/neolaw84/opinionated-databricks-utilities.git
cd opinionated-databricks-utilities
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate       # Linux/macOS
.\venv\Scripts\activate        # Windows
```

3. Install the package in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

---

## Running Tests

The project uses **pytest** for testing, following a strict **TDD** approach (tests are
written before implementation). A custom script `scripts/run_tests.py` runs tests and
enforces quality thresholds.

```bash
python scripts/run_tests.py
```

Or run pytest directly (without the threshold enforcement):

```bash
pytest tests/ -v --no-cov
```

### Thresholds

| Metric | Threshold |
|---|---|
| Test failure rate | Must be **≤ 20%** |
| Coverage (codebase < 1000 lines) | Must be **≥ 60%** |
| Coverage (codebase ≥ 1000 lines) | Must be **≥ 80%** |

### Test Layout

| File | What it tests |
|---|---|
| `tests/test_find_repo_root.py` | `_find_repo_root` and `_check_markers` — core traversal logic |
| `tests/test_repo_root_finder.py` | `repo_root_finder` — public API integration |
| `tests/test_add_src_path.py` | `add_src_path_to_sys_path` — sys.path management |
| `tests/test_build_return.py` | `_build_return_value` — return value construction |

All tests run without a Databricks environment — `dbutils` is mocked and filesystem
operations use `pytest`'s `tmp_path` fixture.

---

## Project Architecture

The utility module lives entirely under `src/odu/`:

```
src/odu/
├── __init__.py       - Public exports
├── bootstrap.py      - All public and internal functions
└── exceptions.py     - RepoRootNotFoundError, NotebookPathError
```

### Public API (`bootstrap.py`)

| Symbol | Type | Description |
|---|---|---|
| `repo_root_finder` | function | Locates the repository root using `dbutils` |
| `add_src_path_to_sys_path` | function | Adds `src/` to `sys.path` |

### Internal Helpers (`bootstrap.py`)

| Symbol | Description |
|---|---|
| `_get_notebook_path(dbutils)` | Retrieves notebook path from `dbutils`, prepends `/Workspace/` |
| `_get_notebook_dir(dbutils)` | Returns the directory of the notebook (parent of `_get_notebook_path`) |
| `_find_repo_root(start, markers, strategy, k, max_depth)` | Walks upward finding the repo root |
| `_check_markers(directory, markers, strategy, k)` | Tests if a directory matches the marker criteria |
| `_build_return_value(repo_root, returns, notebook_path)` | Constructs the return value (str or dict) |

### Design Principles

The module applies SOLID principles through **parameter injection** rather than class hierarchies:

- `dbutils` is always injected — makes the code testable without a Databricks runtime.
- `sys` is always injected — makes `add_src_path_to_sys_path` testable without polluting the real `sys.path`.
- All filesystem logic uses `os.path` — pure and mockable.

---

## Branch & PR Workflow

```
feature/* → dev → main
```

- **Feature branches** must target `dev`.
- **PRs to `main`** must come from `dev`.
- Merging to `main` triggers the release workflow automatically.

## Release Workflow

Releases are fully automated via GitHub Actions:

1. Open a PR from `dev` → `main`.
2. Label the PR with `bump:major`, `bump:patch`, or leave unlabelled (defaults to `minor`).
3. Merge the PR.
4. GitHub Actions will:
    - Bump the version in `pyproject.toml`.
    - Create a tagged GitHub Release.
    - Publish to PyPI via Trusted Publishing (OIDC).
    - Deploy updated documentation to GitHub Pages.

See the [Publishing Guide](https://neolaw84.github.io/opinionated-databricks-utilities/) for
first-time PyPI setup (Trusted Publishing configuration).
# Opinionated Databricks Utilities (ODU)

ODU is a collection of opinionated utilities for working on the Databricks platform.

## The Problem

When Databricks notebooks run as workflow tasks, the current working directory is a
random location on the cluster — **not** the directory where your notebook lives.
This breaks relative imports and `pip install -r requirements.txt`.

ODU solves this by providing utilities to locate your repository root and set up
your Python path correctly, regardless of where the cluster places the working
directory.

## Installation

```bash
pip install odu
```

## Quick Start

See the [User Guide](user_guide.md) for full usage instructions.

```python
import sys
from odu.bootstrap import repo_root_finder, add_src_path_to_sys_path

repo_root = repo_root_finder(dbutils)
add_src_path_to_sys_path(repo_root, sys)
```

## Links

- [User Guide](user_guide.md)
- [Developer Guide](dev_guide.md)
- [API Reference](reference/bootstrap.md)
- [License](license.md)

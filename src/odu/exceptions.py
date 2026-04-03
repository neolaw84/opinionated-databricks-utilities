"""Custom exceptions for ODU bootstrap utilities."""


class RepoRootNotFoundError(Exception):
    """Raised when upward traversal exhausts without finding repo root markers."""


class NotebookPathError(Exception):
    """Raised when the notebook path cannot be retrieved from dbutils."""

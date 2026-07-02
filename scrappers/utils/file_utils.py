"""
Utility helpers for file and directory operations.
"""

from __future__ import annotations

from pathlib import Path


def ensure_directory_exists(path: Path) -> None:
    """
    Ensure that a directory exists.

    Args:
        path: Directory path.
    """

    path.mkdir(parents=True, exist_ok=True)


def ensure_parent_directory_exists(file_path: Path) -> None:
    """
    Ensure that the parent directory of a file exists.

    Args:
        file_path: File path.
    """

    if file_path.parent:
        file_path.parent.mkdir(parents=True, exist_ok=True)


def file_exists(path: Path) -> bool:
    """
    Check if a file exists.

    Args:
        path: File path.

    Returns:
        bool: True if exists, False otherwise.
    """

    return path.exists() and path.is_file()

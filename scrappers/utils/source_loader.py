"""
Utility for loading source URLs from input files.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from config import BASE_DIR


INPUT_URLS_DIR_NAME = "input_urls"


def get_input_file_path(source_name: str) -> Path:
    """
    Build path to the input file for a given source.

    Args:
        source_name: Normalized source name (e.g. dnes_bg)

    Returns:
        Path: Path to input file
    """

    return BASE_DIR / INPUT_URLS_DIR_NAME / f"{source_name}.txt"


def load_source_urls(source_name: str) -> List[str]:
    """
    Load URLs for a given source from its input file.

    Args:
        source_name: Normalized source name

    Returns:
        List[str]: List of URLs

    Raises:
        FileNotFoundError: If input file does not exist
        ValueError: If no valid URLs are found
    """

    file_path = get_input_file_path(source_name)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Input file not found for source: {source_name} | Path: {file_path}"
        )

    urls: List[str] = []

    with file_path.open("r", encoding="utf-8") as file:
        for line in file:
            url = line.strip()

            if not url:
                continue

            urls.append(url)

    if not urls:
        raise ValueError(
            f"No URLs found in input file for source: {source_name}"
        )

    return urls

"""
Utility helpers for URL normalization and manipulation.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse


def build_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Build absolute URL from base and relative URL.

    Args:
        base_url: Base URL.
        relative_url: Relative or absolute URL.

    Returns:
        str: Absolute URL.
    """

    if not relative_url:
        return ""

    return urljoin(base_url, relative_url)


def get_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: Full URL.

    Returns:
        str: Domain (netloc).
    """

    if not url:
        return ""

    parsed = urlparse(url)
    return parsed.netloc


def normalize_url(url: str) -> str:
    """
    Normalize URL by removing trailing slash.

    Args:
        url: URL string.

    Returns:
        str: Normalized URL.
    """

    if not url:
        return ""

    return url.rstrip("/")

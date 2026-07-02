"""
Utility helpers for session timestamps and scraped_at values.
"""

from __future__ import annotations

from datetime import datetime

from config import SCRAPED_AT_FORMAT, SESSION_TIMESTAMP_FORMAT


def get_session_timestamp() -> str:
    """
    Generate a session timestamp for file naming.

    Returns:
        str: Session timestamp in YYYY-MM-DD_HH-MM-SS format.
    """

    return datetime.now().strftime(SESSION_TIMESTAMP_FORMAT)


def get_scraped_at_timestamp() -> str:
    """
    Generate a row-level scraped_at timestamp.

    Returns:
        str: Timestamp in YYYY-MM-DD HH:MM:SS format.
    """

    return datetime.now().strftime(SCRAPED_AT_FORMAT)

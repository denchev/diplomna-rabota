"""
Utility helpers for text normalization and cleanup.
"""

from __future__ import annotations

import html
import re
from typing import Optional

from bs4 import Tag


def clean_text(value: str) -> str:
    """
    Clean and normalize text extracted from HTML.

    Args:
        value: Raw text string to clean.

    Returns:
        str: Cleaned and normalized text.
    """

    if not value:
        return ""

    value = html.unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def safe_get_text(element: Optional[Tag]) -> str:
    """
    Safely extract text from a BeautifulSoup element.

    Args:
        element: BeautifulSoup Tag element, or None.

    Returns:
        str: Extracted and cleaned text, or empty string if element is None.
    """

    if element is None:
        return ""

    try:
        raw_text = element.get_text()
        return clean_text(raw_text)

    except AttributeError:
        return ""


def safe_get_attribute(element: Optional[Tag], attribute_name: str) -> str:
    """
    Safely extract an attribute from a BeautifulSoup element.

    Args:
        element: BeautifulSoup Tag element, or None.
        attribute_name: Name of the HTML attribute to extract.

    Returns:
        str: Attribute value, or empty string if element is None or attribute
            is missing.
    """

    if element is None:
        return ""

    try:
        value = element.get(attribute_name)
        return clean_text(value) if value else ""

    except AttributeError:
        return ""

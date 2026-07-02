"""
Data model for a single comment record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final


OUTPUT_FIELD_NAMES: Final[list[str]] = [
    "source_site",
    "category_url",
    "article_url",
    "article_title",
    "article_published_at",
    "article_views",
    "comment_index",
    "comment",
    "author",
    "comment_date",
    "likes",
    "dislikes",
    "scraped_at",
]


@dataclass
class CommentRecord:
    """
    Represents a single scraped comment record.
    """

    source_site: str
    category_url: str
    article_url: str
    article_title: str
    article_published_at: str
    article_views: str = ""
    comment_index: str = ""
    comment: str = ""
    author: str = ""
    comment_date: str = ""
    likes: str = ""
    dislikes: str = ""
    scraped_at: str = ""

    def to_output_dict(self) -> dict[str, str]:
        """
        Convert the record into an ordered dictionary aligned with
        OUTPUT_FIELD_NAMES.

        Returns:
            dict[str, str]: Ordered dictionary suitable for output writers.
        """

        raw_data = asdict(self)

        cleaned_data: dict[str, str] = {
            key: ("" if value is None else str(value))
            for key, value in raw_data.items()
        }

        ordered_data: dict[str, str] = {
            field_name: cleaned_data.get(field_name, "")
            for field_name in OUTPUT_FIELD_NAMES
        }

        return ordered_data

    def validate(self) -> None:
        """
        Validate minimal required fields.

        Raises:
            ValueError: If a required field is missing.
        """

        if not self.source_site:
            raise ValueError("source_site is required")

        if not self.category_url:
            raise ValueError("category_url is required")

        if not self.article_url:
            raise ValueError("article_url is required")

        if not self.article_title:
            raise ValueError("article_title is required")

        if not self.article_published_at:
            raise ValueError("article_published_at is required")

        if not self.comment:
            raise ValueError("comment is required")

        if not self.scraped_at:
            raise ValueError("scraped_at is required")

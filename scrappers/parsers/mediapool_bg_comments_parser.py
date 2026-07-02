"""
Parser helpers for mediapool.bg article comments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bs4 import BeautifulSoup

from services.logging_service import log_debug, log_warning
from utils.text_utils import clean_text, safe_get_attribute, safe_get_text


@dataclass
class MediapoolBgParsedComment:
    """
    Parsed comment data from a mediapool.bg article page.
    """

    comment_index: str
    comment: str
    author: str
    comment_date: str
    likes: str
    dislikes: str


def parse_comments(
    html: str,
    article_url: str,
    logger: logging.Logger,
) -> list[MediapoolBgParsedComment]:
    """
    Parse all comments from a mediapool.bg article page.

    Args:
        html: Raw HTML of the fully loaded article page.
        article_url: Article URL used for logging context.
        logger: Logger instance.

    Returns:
        list[MediapoolBgParsedComment]: Parsed comments from the article.
    """

    soup = BeautifulSoup(html, "html.parser")

    comments: list[MediapoolBgParsedComment] = []

    for node in soup.select("ol.c-comments__list > li"):
        if "c-comments__item-deleted" in node.get("class", []):
            index = clean_text(
                safe_get_text(
                    node.select_one("a.c-comments__anchor")
                )
            ).lstrip("#")
            log_debug(
                logger,
                (
                    f"Skipping deleted comment | index={index} "
                    f"| url={article_url}"
                ),
            )
            continue

        index = clean_text(
            safe_get_text(
                node.select_one("a.c-comments__anchor")
            )
        ).lstrip("#")

        author = clean_text(
            safe_get_text(
                node.select_one(
                    "div.c-comments__header a.c-comments__author"
                )
            )
        )
        comment_date = safe_get_attribute(
            node.select_one("div.c-comments__header time"),
            "datetime",
        ).strip()

        likes = clean_text(
            safe_get_text(
                node.select_one(
                    "button.c-button_icon_thumbs-up span:first-child"
                )
            )
        )
        dislikes = clean_text(
            safe_get_text(
                node.select_one(
                    "button.c-button_icon_thumbs-down span:first-child"
                )
            )
        )
        content = clean_text(
            safe_get_text(
                node.select_one("p.c-comments__text")
            )
        )

        if not content:
            log_warning(
                logger,
                (
                    f"Skipping comment with empty content | index={index} "
                    f"| url={article_url}"
                ),
            )
            continue

        comments.append(
            MediapoolBgParsedComment(
                comment_index=index,
                comment=content,
                author=author,
                comment_date=comment_date,
                likes=likes,
                dislikes=dislikes,
            )
        )

    log_debug(
        logger,
        (
            f"Parsed comments | article_url={article_url} "
            f"| comments_found={len(comments)}"
        ),
    )

    return comments


def extract_total_comment_count(
    html: str,
    logger: logging.Logger,
) -> int:
    """
    Extract the total comment count from a mediapool.bg article page.

    Args:
        html: Raw HTML of the article page.
        logger: Logger instance.

    Returns:
        int: Total comment count, or 0 if not found.
    """

    soup = BeautifulSoup(html, "html.parser")

    heading = soup.select_one("h2#comments")

    if not heading:
        log_debug(
            logger,
            "No comments heading found on article page",
        )
        return 0

    raw_text = clean_text(safe_get_text(heading))

    digits_only = "".join(char for char in raw_text if char.isdigit())

    if not digits_only:
        log_debug(
            logger,
            f"Could not extract comment count from heading | raw={raw_text}",
        )
        return 0

    try:
        return int(digits_only)
    except ValueError:
        return 0

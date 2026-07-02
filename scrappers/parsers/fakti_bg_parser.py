"""
Parser helpers for fakti.bg category and article pages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag

from services.logging_service import log_debug, log_info, log_warning
from utils.text_utils import clean_text, safe_get_attribute, safe_get_text
from utils.url_utils import build_absolute_url, normalize_url


@dataclass
class FaktiBgCategoryArticle:
    """
    Parsed article metadata from a fakti.bg category page.
    """

    article_url: str
    article_title: str
    article_published_at: str
    article_views: str
    comment_count: int


@dataclass
class FaktiBgParsedComment:
    """
    Parsed comment data from a fakti.bg article page.
    """

    comment_index: str
    comment: str
    author: str
    comment_date: str
    likes: str
    dislikes: str


def parse_category_page(
    html: str,
    category_url: str,
    logger: logging.Logger,
) -> list[FaktiBgCategoryArticle]:
    """
    Parse a fakti.bg category page and extract article metadata.

    Args:
        html: Raw HTML of the category page.
        category_url: Current category page URL.
        logger: Logger instance.

    Returns:
        list[FaktiBgCategoryArticle]: Parsed articles from the page.
    """

    soup = BeautifulSoup(html, "html.parser")

    results: list[FaktiBgCategoryArticle] = []

    for item in soup.select("#main > div.list > ul > li"):
        link_element = item.select_one("a")

        if not link_element:
            log_warning(
                logger,
                f"Skipping list item with no anchor element | url={category_url}",
            )
            continue

        article_url = normalize_url(
            build_absolute_url(
                category_url,
                safe_get_attribute(link_element, "href"),
            )
        )

        if not article_url:
            log_warning(
                logger,
                f"Skipping list item with empty href | url={category_url}",
            )
            continue

        title = clean_text(
            safe_get_text(
                link_element.select_one("div.list-info div.list-title span.post-title")
            )
        )
        date = _parse_date(
            clean_text(
                safe_get_text(
                    link_element.select_one("div.list-info div.ndt")
                )
            )
        )
        views = clean_text(
            safe_get_text(
                link_element.select_one("div.list-info div.nv")
            )
        )
        comment_count = _parse_int(
            safe_get_text(
                link_element.select_one("div.list-info div.nc")
            )
        )

        results.append(
            FaktiBgCategoryArticle(
                article_url=article_url,
                article_title=title,
                article_published_at=date,
                article_views=views,
                comment_count=comment_count,
            )
        )

    log_info(
        logger,
        f"Parsed category page | url={category_url} | articles_found={len(results)}",
    )

    return results


def get_next_page_url(
    html: str,
    category_url: str,
    logger: logging.Logger,
) -> Optional[str]:
    """
    Extract the next category page URL from the current page.

    Args:
        html: Raw HTML of the current category page.
        category_url: Current category page URL used as base for relative links.
        logger: Logger instance.

    Returns:
        Optional[str]: Absolute URL of the next page, or None if no next page exists.
    """

    soup = BeautifulSoup(html, "html.parser")

    next_element = soup.select_one("#main a.next-link")

    if not next_element:
        log_debug(
            logger,
            f"No next page link found | url={category_url}",
        )
        return None

    next_url = normalize_url(
        build_absolute_url(
            category_url,
            safe_get_attribute(next_element, "href"),
        )
    )

    if not next_url:
        log_warning(
            logger,
            f"Next page link found but href is empty | url={category_url}",
        )
        return None

    log_debug(
        logger,
        f"Next page found | url={next_url}",
    )

    return next_url


def parse_comments(
    html: str,
    article_url: str,
    logger: logging.Logger,
) -> list[FaktiBgParsedComment]:
    """
    Parse all comments from a fakti.bg article page.

    Args:
        html: Raw HTML of the article page.
        article_url: Article URL used for logging context.
        logger: Logger instance.

    Returns:
        list[FaktiBgParsedComment]: Parsed comments from the article.
    """

    soup = BeautifulSoup(html, "html.parser")

    comments: list[FaktiBgParsedComment] = []

    for node in soup.select("#comments > ul > li"):
        if node.select_one("div.discussion-comment-header span.removed"):
            removed_index = clean_text(
                safe_get_text(
                    node.select_one("div.discussion-comment-header span.num")
                )
            )
            log_debug(
                logger,
                (
                    f"Skipping removed comment | index={removed_index} "
                    f"| url={article_url}"
                ),
            )
            continue

        index = clean_text(
            safe_get_text(
                node.select_one("div.discussion-comment-header span.num")
            )
        )
        author = clean_text(
            safe_get_text(
                node.select_one("div.discussion-comment-header span.user")
            )
        )
        comment_time = clean_text(
            safe_get_text(
                node.select_one("div.discussion-comment-footer p span:first-child")
            )
        )
        comment_date = clean_text(
            safe_get_text(
                node.select_one("div.discussion-comment-footer p span:last-child")
            )
        )
        likes = clean_text(
            safe_get_text(
                node.select_one(
                    "div.discussion-comment-header div.votes a.VotePlus"
                )
            )
        )
        dislikes = clean_text(
            safe_get_text(
                node.select_one(
                    "div.discussion-comment-header div.votes a.VoteMinus"
                )
            )
        )
        content = _extract_comment_text(node)

        if not content:
            log_warning(
                logger,
                f"Skipping comment with empty content | index={index} | url={article_url}",
            )
            continue

        combined_date = _combine_date_time(comment_date, comment_time)

        comments.append(
            FaktiBgParsedComment(
                comment_index=index,
                comment=content,
                author=author,
                comment_date=combined_date,
                likes=likes,
                dislikes=dislikes,
            )
        )

    log_debug(
        logger,
        f"Parsed comments | article_url={article_url} | comments_found={len(comments)}",
    )

    return comments


def _extract_comment_text(comment_node: Tag) -> str:
    """
    Extract clean comment text from the comment content block.

    Args:
        comment_node: The full comment DOM node.

    Returns:
        str: Clean comment text.
    """

    content_div = comment_node.select_one("div.discussion-comment-text")

    if content_div is None:
        return ""

    return clean_text(content_div.get_text(" ", strip=True))


def _combine_date_time(date: str, time: str) -> str:
    """
    Combine separate date and time strings into a single value.

    Args:
        date: Date string extracted from the page.
        time: Time string extracted from the page.

    Returns:
        str: Combined date and time string.
    """

    date = date.strip()
    time = time.strip()

    if date and time:
        return f"{date} {time}"

    return date or time


def _parse_date(raw: str) -> str:
    """
    Normalize article date from fakti.bg listing pages.

    Args:
        raw: Raw date text from the page.

    Returns:
        str: Normalized date string in YYYY-MM-DD format, or the original
            value if parsing fails.
    """

    if not raw:
        return ""

    try:
        parsed_date = datetime.strptime(raw, "%d.%m.%Y")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        return raw


def _parse_int(text: str) -> int:
    """
    Parse an integer from a text value.

    Args:
        text: Raw text that may contain digits.

    Returns:
        int: Parsed integer, or 0 if parsing fails.
    """

    if not text:
        return 0

    digits_only = "".join(char for char in text if char.isdigit())

    if not digits_only:
        return 0

    try:
        return int(digits_only)
    except ValueError:
        return 0

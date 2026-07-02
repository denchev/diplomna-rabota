"""
Parser helpers for dnes.bg category and comments pages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from services.logging_service import log_debug, log_info, log_warning
from utils.text_utils import clean_text, safe_get_attribute, safe_get_text
from utils.url_utils import build_absolute_url, normalize_url


@dataclass
class DnesBgCategoryArticle:
    """
    Parsed article metadata from a dnes.bg category page.
    """

    article_url: str
    article_title: str
    article_published_at: str
    comment_count: int


@dataclass
class DnesBgParsedComment:
    """
    Parsed comment data from a dnes.bg comments page.
    """

    comment_index: str
    comment: str
    author: str
    comment_date: str
    likes: str
    dislikes: str


def build_comments_url(article_url: str) -> str:
    """
    Build the comments page URL for a dnes.bg article.

    Args:
        article_url: Article URL.

    Returns:
        str: Comments page URL.
    """

    normalized = normalize_url(article_url)

    if not normalized:
        return ""

    return f"{normalized}/comments"


def parse_category_page(
    html: str,
    category_url: str,
    logger: logging.Logger,
) -> list[DnesBgCategoryArticle]:
    """
    Parse a dnes.bg category page.

    Args:
        html: Raw HTML of the category page.
        category_url: Current category URL.
        logger: Logger instance.

    Returns:
        list[DnesBgCategoryArticle]: Parsed top article and list articles.
    """

    soup = BeautifulSoup(html, "html.parser")

    results: list[DnesBgCategoryArticle] = []

    top_block = soup.select_one("div.top-article-header")

    if top_block:
        title_element = top_block.select_one(
            "div.article-title h2 a"
        )
        date_element = top_block.select_one(
            "div.article-meta span.article-date"
        )
        comments_element = top_block.select_one(
            "div.article-meta span.article-comment"
        )

        if title_element:
            url = build_absolute_url(
                category_url,
                safe_get_attribute(title_element, "href"),
            )
            title = clean_text(safe_get_text(title_element))
            date = _parse_date(
                clean_text(safe_get_text(date_element))
            )
            comments = _parse_int(
                safe_get_text(comments_element)
            )

            results.append(
                DnesBgCategoryArticle(
                    article_url=normalize_url(url),
                    article_title=title,
                    article_published_at=date,
                    comment_count=comments,
                )
            )
        else:
            log_debug(
                logger,
                f"No title element in top-article-header | url={category_url}",
            )
    else:
        log_debug(
            logger,
            f"No top-article-header block found | url={category_url}",
        )

    for item in soup.select("div.article-listing ul li"):
        title_element = item.select_one("div.article-title h2 a")
        date_element = item.select_one(
            "div.article-meta span.article-date"
        )
        comments_element = item.select_one(
            "div.article-meta span.article-comment"
        )

        if not title_element:
            log_warning(
                logger,
                f"Skipping list item with no title element | url={category_url}",
            )
            continue

        url = build_absolute_url(
            category_url,
            safe_get_attribute(title_element, "href"),
        )
        title = clean_text(safe_get_text(title_element))
        date = _parse_date(
            clean_text(safe_get_text(date_element))
        )
        comments = _parse_int(
            safe_get_text(comments_element)
        )

        results.append(
            DnesBgCategoryArticle(
                article_url=normalize_url(url),
                article_title=title,
                article_published_at=date,
                comment_count=comments,
            )
        )

    log_info(
        logger,
        f"Parsed category page | url={category_url} | articles_found={len(results)}",
    )

    return results


def generate_category_page_urls(
    html: str,
    category_url: str,
    logger: logging.Logger,
) -> list[str]:
    """
    Generate all category page URLs from page 1 to the last page.

    Args:
        html: Raw HTML of the first category page.
        category_url: Base category URL.
        logger: Logger instance.

    Returns:
        list[str]: All category page URLs in order.
    """

    soup = BeautifulSoup(html, "html.parser")

    last_element = soup.select_one("div.pagination ul li.last-page a")

    if not last_element:
        log_debug(
            logger,
            f"No pagination found, treating as single page | url={category_url}",
        )
        return [category_url]

    last_url = build_absolute_url(
        category_url,
        safe_get_attribute(last_element, "href"),
    )
    last_page = _extract_current_page_number(last_url, "page")

    log_debug(
        logger,
        f"Category pagination detected | total_pages={last_page} | url={category_url}",
    )

    urls: list[str] = []

    for page_number in range(1, last_page + 1):
        if page_number == 1:
            urls.append(category_url)
        else:
            urls.append(
                _set_query_parameter(
                    category_url,
                    "page",
                    str(page_number),
                )
            )

    return urls


def parse_comments_page(
    html: str,
    logger: logging.Logger,
) -> list[DnesBgParsedComment]:
    """
    Parse one dnes.bg comments page using DOM selectors only.

    Args:
        html: Raw HTML of the comments page.
        logger: Logger instance.

    Returns:
        list[DnesBgParsedComment]: Parsed comments from the page.
    """

    soup = BeautifulSoup(html, "html.parser")

    comments: list[DnesBgParsedComment] = []

    for node in soup.select("#commentslist > div.comment"):
        index = clean_text(
            safe_get_text(
                node.select_one("div.comment-header span.num")
            )
        )
        author = clean_text(
            safe_get_text(
                node.select_one(
                    "div.comment-header div.comment-info span.author"
                )
            )
        )
        date = clean_text(
            safe_get_text(
                node.select_one(
                    "div.comment-header div.comment-info span.date"
                )
            )
        )
        likes = clean_text(
            safe_get_text(
                node.select_one(
                    "div.comment-header div.rating span.rate-up span.up"
                )
            )
        )
        dislikes = clean_text(
            safe_get_text(
                node.select_one(
                    "div.comment-header div.rating span.rate-down span.down"
                )
            )
        )
        content = _extract_comment_text(node)

        if not content:
            log_warning(
                logger,
                f"Skipping comment with empty content | index={index}",
            )
            continue

        comments.append(
            DnesBgParsedComment(
                comment_index=index,
                comment=content,
                author=author,
                comment_date=date,
                likes=likes,
                dislikes=dislikes,
            )
        )

    log_debug(
        logger,
        f"Parsed comments page | comments_found={len(comments)}",
    )

    return comments


def generate_comments_page_urls(
    html: str,
    comments_url: str,
    logger: logging.Logger,
) -> list[str]:
    """
    Generate all comments page URLs from page 1 to the last page.

    Args:
        html: Raw HTML of the first comments page.
        comments_url: Base comments URL.
        logger: Logger instance.

    Returns:
        list[str]: All comments page URLs in order.
    """

    soup = BeautifulSoup(html, "html.parser")

    last_element = soup.select_one("div.pagination span.last a")

    if not last_element:
        log_debug(
            logger,
            f"No comments pagination found, treating as single page | url={comments_url}",
        )
        return [comments_url]

    last_url = build_absolute_url(
        comments_url,
        safe_get_attribute(last_element, "href"),
    )
    last_page = _extract_current_page_number(last_url, "cp")

    log_debug(
        logger,
        (
            f"Comments pagination detected | total_pages={last_page} "
            f"| url={comments_url}"
        ),
    )

    urls: list[str] = []

    for page_number in range(1, last_page + 1):
        if page_number == 1:
            urls.append(comments_url)
        else:
            urls.append(
                _set_query_parameter(
                    comments_url,
                    "cp",
                    str(page_number),
                )
            )

    return urls


def _extract_comment_text(comment_node: Tag) -> str:
    """
    Extract only the actual comment text from the comment content block.

    Removes UI elements such as reply and report controls before reading text.

    Args:
        comment_node: The full comment DOM node.

    Returns:
        str: Clean comment text.
    """

    content_div = comment_node.select_one("div.comment-content")

    if content_div is None:
        return ""

    content_copy = BeautifulSoup(
        str(content_div),
        "html.parser",
    ).select_one("div.comment-content")

    if content_copy is None:
        return ""

    for link in content_copy.select("a"):
        link.decompose()

    for clear_div in content_copy.select("div.clear"):
        clear_div.decompose()

    for report_span in content_copy.select("span.report-comment"):
        report_span.decompose()

    return clean_text(content_copy.get_text(" ", strip=True))


def _parse_date(raw: str) -> str:
    """
    Normalize article date from dnes.bg listing pages.

    Args:
        raw: Raw date text from the page.

    Returns:
        str: Normalized datetime string, or the original value if parsing fails.
    """

    if not raw:
        return ""

    try:
        parsed_datetime = datetime.strptime(raw, "%d.%m.%Y %H:%M")
        return parsed_datetime.strftime("%Y-%m-%d %H:%M:%S")
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


def _extract_current_page_number(url: str, param: str) -> int:
    """
    Extract the current page number from a query parameter.

    Args:
        url: Target URL.
        param: Query parameter name.

    Returns:
        int: Current page number, defaulting to 1.
    """

    parsed = urlsplit(url)
    query_string = parse_qs(parsed.query)
    values = query_string.get(param, [])

    if not values:
        return 1

    try:
        return int(values[0])
    except ValueError:
        return 1


def _set_query_parameter(url: str, key: str, value: str) -> str:
    """
    Set or replace a single query parameter in a URL.

    Args:
        url: Original URL.
        key: Query parameter name.
        value: Query parameter value.

    Returns:
        str: Updated URL.
    """

    parsed = urlsplit(url)
    query_string = parse_qs(parsed.query)
    query_string[key] = [value]

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query_string, doseq=True),
            parsed.fragment,
        )
    )

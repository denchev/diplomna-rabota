"""
Parser helpers for mediapool.bg category pages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup

from services.logging_service import log_debug, log_info, log_warning
from utils.text_utils import clean_text, safe_get_attribute, safe_get_text
from utils.url_utils import build_absolute_url, normalize_url


@dataclass
class MediapoolBgCategoryArticle:
    """
    Parsed article metadata from a mediapool.bg category page.
    """

    article_id: str
    article_url: str
    article_title: str
    article_published_at: str


def parse_category_page(
    html: str,
    category_url: str,
    logger: logging.Logger,
) -> list[MediapoolBgCategoryArticle]:
    """
    Parse a mediapool.bg category page and extract article metadata.

    Args:
        html: Raw HTML of the category page.
        category_url: Current category page URL.
        logger: Logger instance.

    Returns:
        list[MediapoolBgCategoryArticle]: Parsed articles from the page.
    """

    soup = BeautifulSoup(html, "html.parser")

    results: list[MediapoolBgCategoryArticle] = []

    for item in soup.select("ul.l-grid__container > li > article"):
        link_element = item.select_one("a.c-article-item")

        if not link_element:
            log_warning(
                logger,
                f"Skipping article with no anchor element | url={category_url}",
            )
            continue

        raw_href = safe_get_attribute(link_element, "href").strip()

        article_url = normalize_url(
            build_absolute_url(category_url, raw_href)
        )

        if not article_url:
            log_warning(
                logger,
                f"Skipping article with empty href | url={category_url}",
            )
            continue

        article_id = _extract_article_id(article_url)

        if not article_id:
            log_warning(
                logger,
                f"Could not extract article ID | article_url={article_url}",
            )
            continue

        title = clean_text(
            safe_get_text(
                item.select_one("h2.c-article-item__title")
            )
        )
        published_at = _parse_datetime(
            safe_get_attribute(
                item.select_one("time.c-article-item__date"),
                "datetime",
            )
        )

        results.append(
            MediapoolBgCategoryArticle(
                article_id=article_id,
                article_url=article_url,
                article_title=title,
                article_published_at=published_at,
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
) -> str | None:
    """
    Extract the last category page URL from pagination and generate the next page URL.

    Args:
        html: Raw HTML of the current category page.
        category_url: Current category page URL.
        logger: Logger instance.

    Returns:
        str | None: Absolute URL of the next page, or None if no next page exists.
    """

    soup = BeautifulSoup(html, "html.parser")

    last_element = soup.select_one("div.c-pages a.c-button:last-child")

    if not last_element:
        log_debug(
            logger,
            f"No pagination found, treating as single page | url={category_url}",
        )
        return None

    last_url = normalize_url(
        build_absolute_url(
            category_url,
            safe_get_attribute(last_element, "href"),
        )
    )

    last_page = _extract_page_number(last_url)
    current_page = _extract_page_number(category_url)

    if current_page >= last_page:
        log_debug(
            logger,
            f"Reached last page | page={current_page} | url={category_url}",
        )
        return None

    next_page = current_page + 1
    next_url = _set_page_parameter(category_url, next_page)

    log_debug(
        logger,
        f"Next page found | page={next_page} | url={next_url}",
    )

    return next_url


def _extract_article_id(article_url: str) -> str:
    """
    Extract the article ID from a mediapool.bg article URL.

    Args:
        article_url: Full article URL.

    Returns:
        str: Article ID, or empty string if extraction fails.
    """

    if not article_url or "news" not in article_url:
        return ""

    try:
        return article_url.split("news")[-1].replace(".html", "").strip()
    except (IndexError, AttributeError):
        return ""


def _extract_page_number(url: str) -> int:
    """
    Extract the page number from a mediapool.bg pagination URL.

    Args:
        url: Pagination URL.

    Returns:
        int: Page number, defaulting to 1 if not found.
    """

    if not url or "page=" not in url:
        return 1

    try:
        return int(url.split("page=")[-1].strip())
    except (ValueError, IndexError):
        return 1


def _set_page_parameter(url: str, page: int) -> str:
    """
    Set or replace the page number in a mediapool.bg category URL.

    Args:
        url: Base category URL.
        page: Target page number.

    Returns:
        str: URL with updated page parameter.
    """

    base = url.split("?")[0]
    return f"{base}?page={page}"


def _parse_datetime(raw: str) -> str:
    """
    Normalize article datetime from mediapool.bg ISO format.

    Args:
        raw: Raw datetime string from the datetime attribute.

    Returns:
        str: Normalized datetime string in YYYY-MM-DD HH:MM:SS format,
            or the original value if parsing fails.
    """

    if not raw:
        return ""

    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return raw

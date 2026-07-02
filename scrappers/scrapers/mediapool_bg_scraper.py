"""
Scraper implementation for mediapool.bg.

Uses Playwright to browse category pages, collect article metadata,
expand all comments on each article page and write results to CSV.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from config import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_USER_AGENT,
    PLAYWRIGHT_HEADLESS,
    SOURCE_NAME_MEDIAPOOL_BG,
)
from models.comment_record import CommentRecord
from parsers.mediapool_bg_comments_parser import (
    MediapoolBgParsedComment,
    extract_total_comment_count,
    parse_comments,
)
from parsers.mediapool_bg_parser import (
    MediapoolBgCategoryArticle,
    get_next_page_url,
    parse_category_page,
)
from services.csv_service import CsvWriter
from services.logging_service import (
    configure_logger,
    log_debug,
    log_error,
    log_info,
    log_warning,
)
from utils.date_utils import get_scraped_at_timestamp
from utils.source_loader import load_source_urls


LOAD_MORE_BUTTON_SELECTOR: str = "#load-comments"
PAGE_LOAD_TIMEOUT_MS: int = 30_000
BUTTON_CLICK_TIMEOUT_MS: int = 10_000
BUTTON_REAPPEAR_TIMEOUT_MS: int = 15_000


@dataclass
class MediapoolBgScraperStats:
    """
    Runtime statistics for a mediapool.bg scraper run.
    """

    category_pages_processed: int = 0
    articles_discovered: int = 0
    articles_skipped_zero_comments: int = 0
    articles_processed: int = 0
    articles_failed: int = 0
    comments_written: int = 0


class MediapoolBgScraper:
    """
    Playwright scraper for mediapool.bg category pages and article comments.
    """

    def __init__(self, session_timestamp: str, log_level: str) -> None:
        """
        Initialize the scraper.

        Args:
            session_timestamp: Session timestamp for the current run.
            log_level: Requested log level.
        """

        self.source_name = SOURCE_NAME_MEDIAPOOL_BG
        self.session_timestamp = session_timestamp
        self.logger = configure_logger(
            source_name=self.source_name,
            session_timestamp=self.session_timestamp,
            log_level=log_level,
        )
        self.stats = MediapoolBgScraperStats()

    def run(self) -> None:
        """
        Run the scraper for all configured mediapool.bg category URLs.

        Raises:
            FileNotFoundError: If the source input file does not exist.
            ValueError: If the source input file contains no URLs.
        """

        category_urls = load_source_urls(source_name=self.source_name)

        log_info(
            self.logger,
            f"Loaded {len(category_urls)} category URL(s) for {self.source_name}",
        )

        with CsvWriter(
            source_name=self.source_name,
            session_timestamp=self.session_timestamp,
        ) as csv_writer:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
                context = browser.new_context(
                    user_agent=DEFAULT_USER_AGENT,
                )
                page = context.new_page()

                for category_url in category_urls:
                    self._process_category_chain(
                        start_category_url=category_url,
                        page=page,
                        csv_writer=csv_writer,
                    )

                context.close()
                browser.close()

        self._log_summary()

    def _process_category_chain(
        self,
        start_category_url: str,
        page: Page,
        csv_writer: CsvWriter,
    ) -> None:
        """
        Process all pages of one category by following pagination.

        Args:
            start_category_url: First category page URL.
            page: Active Playwright page.
            csv_writer: Active CSV writer.
        """

        current_url: str = start_category_url
        page_number: int = 0

        while current_url:
            page_number += 1

            log_debug(
                self.logger,
                f"Fetching category page {page_number} | url={current_url}",
            )

            html = self._fetch_page(page=page, url=current_url)

            if html is None:
                log_error(
                    self.logger,
                    f"Failed to fetch category page | url={current_url}",
                )
                break

            articles = parse_category_page(
                html=html,
                category_url=current_url,
                logger=self.logger,
            )

            self.stats.category_pages_processed += 1
            self.stats.articles_discovered += len(articles)

            for article in articles:
                self._process_article(
                    category_url=current_url,
                    article=article,
                    page=page,
                    csv_writer=csv_writer,
                )

            current_url = get_next_page_url(
                html=html,
                category_url=current_url,
                logger=self.logger,
            )

    def _process_article(
        self,
        category_url: str,
        article: MediapoolBgCategoryArticle,
        page: Page,
        csv_writer: CsvWriter,
    ) -> None:
        """
        Visit one article page, expand all comments and write them to CSV.

        Args:
            category_url: Source category URL.
            article: Parsed article metadata.
            page: Active Playwright page.
            csv_writer: Active CSV writer.
        """

        log_info(
            self.logger,
            f"Processing article | url={article.article_url}",
        )

        html = self._fetch_page(page=page, url=article.article_url)

        if html is None:
            log_error(
                self.logger,
                f"Failed to fetch article page | url={article.article_url}",
            )
            self.stats.articles_failed += 1
            return

        total_comments = extract_total_comment_count(
            html=html,
            logger=self.logger,
        )

        if total_comments <= 0:
            log_info(
                self.logger,
                f"Skipping article with zero comments | url={article.article_url}",
            )
            self.stats.articles_skipped_zero_comments += 1
            return

        log_info(
            self.logger,
            (
                f"Expanding comments | url={article.article_url} "
                f"| total_comments={total_comments}"
            ),
        )

        self._expand_all_comments(
            page=page,
            article_url=article.article_url,
        )

        html = page.content()

        parsed_comments = parse_comments(
            html=html,
            article_url=article.article_url,
            logger=self.logger,
        )

        if not parsed_comments:
            log_warning(
                self.logger,
                (
                    f"No comments parsed despite expected count "
                    f"| url={article.article_url} "
                    f"| expected={total_comments}"
                ),
            )
            self.stats.articles_failed += 1
            return

        for parsed_comment in parsed_comments:
            self._write_comment_record(
                category_url=category_url,
                article=article,
                parsed_comment=parsed_comment,
                csv_writer=csv_writer,
            )

        self.stats.articles_processed += 1

        log_info(
            self.logger,
            (
                f"Comments written | url={article.article_url} "
                f"| parsed={len(parsed_comments)} "
                f"| expected={total_comments}"
            ),
        )

    def _expand_all_comments(
        self,
        page: Page,
        article_url: str,
    ) -> None:
        """
        Click the load-more button repeatedly until all comments are loaded.

        Args:
            page: Active Playwright page.
            article_url: Article URL used for logging context.
        """

        click_count = 0

        while True:
            try:
                button = page.query_selector(LOAD_MORE_BUTTON_SELECTOR)

                if not button:
                    log_debug(
                        self.logger,
                        (
                            f"Load-more button not found, all comments loaded "
                            f"| clicks={click_count} | url={article_url}"
                        ),
                    )
                    break

                if not button.is_enabled():
                    log_debug(
                        self.logger,
                        (
                            f"Load-more button disabled, all comments loaded "
                            f"| clicks={click_count} | url={article_url}"
                        ),
                    )
                    break

                button.scroll_into_view_if_needed()
                button.click(timeout=BUTTON_CLICK_TIMEOUT_MS)
                click_count += 1

                log_debug(
                    self.logger,
                    (
                        f"Clicked load-more | click={click_count} "
                        f"| url={article_url}"
                    ),
                )

                page.wait_for_selector(
                    LOAD_MORE_BUTTON_SELECTOR,
                    state="visible",
                    timeout=BUTTON_REAPPEAR_TIMEOUT_MS,
                )

            except PlaywrightTimeoutError:
                log_debug(
                    self.logger,
                    (
                        f"Load-more button did not reappear, all comments loaded "
                        f"| clicks={click_count} | url={article_url}"
                    ),
                )
                break

            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_error(
                    self.logger,
                    (
                        f"Unexpected error clicking load-more button "
                        f"| click={click_count} | url={article_url} "
                        f"| error={exc}"
                    ),
                )
                break

    def _fetch_page(
        self,
        page: Page,
        url: str,
    ) -> str | None:
        """
        Navigate to a URL and return the page HTML content.

        Args:
            page: Active Playwright page.
            url: Target URL.

        Returns:
            str | None: Page HTML content, or None if loading failed.
        """

        try:
            page.goto(url, timeout=PAGE_LOAD_TIMEOUT_MS)
            page.wait_for_load_state("domcontentloaded")
            return page.content()

        except PlaywrightTimeoutError:
            log_error(
                self.logger,
                f"Timeout loading page | url={url}",
            )
            return None

        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_error(
                self.logger,
                f"Failed to load page | url={url} | error={exc}",
            )
            return None

    def _write_comment_record(
        self,
        category_url: str,
        article: MediapoolBgCategoryArticle,
        parsed_comment: MediapoolBgParsedComment,
        csv_writer: CsvWriter,
    ) -> None:
        """
        Convert one parsed comment into a CommentRecord and write it.

        Args:
            category_url: Source category URL.
            article: Parsed article metadata.
            parsed_comment: Parsed comment data.
            csv_writer: Active CSV writer.
        """

        record = CommentRecord(
            source_site="mediapool.bg",
            category_url=category_url,
            article_url=article.article_url,
            article_title=article.article_title,
            article_published_at=article.article_published_at,
            article_views="",
            comment_index=parsed_comment.comment_index,
            comment=parsed_comment.comment,
            author=parsed_comment.author,
            comment_date=parsed_comment.comment_date,
            likes=parsed_comment.likes,
            dislikes=parsed_comment.dislikes,
            scraped_at=get_scraped_at_timestamp(),
        )

        record.validate()
        csv_writer.write_record(record)

        self.stats.comments_written += 1

    def _log_summary(self) -> None:
        """
        Log final scraper summary.
        """

        log_info(
            self.logger,
            (
                f"mediapool.bg scraper finished "
                f"| category_pages_processed={self.stats.category_pages_processed} "
                f"| articles_discovered={self.stats.articles_discovered} "
                f"| articles_skipped_zero_comments="
                f"{self.stats.articles_skipped_zero_comments} "
                f"| articles_processed={self.stats.articles_processed} "
                f"| articles_failed={self.stats.articles_failed} "
                f"| comments_written={self.stats.comments_written}"
            ),
        )


def run_mediapool_bg_scraper(
    session_timestamp: str,
    log_level: str = DEFAULT_LOG_LEVEL,
) -> None:
    """
    Run the mediapool.bg scraper.

    Args:
        session_timestamp: Session timestamp for the current run.
        log_level: Requested log level.
    """

    scraper = MediapoolBgScraper(
        session_timestamp=session_timestamp,
        log_level=log_level,
    )
    scraper.run()

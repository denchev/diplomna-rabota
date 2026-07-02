"""
Scraper implementation for fakti.bg.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import DEFAULT_LOG_LEVEL, SOURCE_NAME_FAKTI_BG
from models.comment_record import CommentRecord
from parsers.fakti_bg_parser import (
    FaktiBgCategoryArticle,
    FaktiBgParsedComment,
    get_next_page_url,
    parse_category_page,
    parse_comments,
)
from services.csv_service import CsvWriter
from services.logging_service import (
    configure_logger,
    log_debug,
    log_error,
    log_info,
    log_warning,
)
from services.request_service import RequestService
from utils.date_utils import get_scraped_at_timestamp
from utils.source_loader import load_source_urls


@dataclass
class FaktiBgScraperStats:
    """
    Runtime statistics for a fakti.bg scraper run.
    """

    category_pages_processed: int = 0
    articles_discovered: int = 0
    articles_skipped_zero_comments: int = 0
    articles_processed: int = 0
    comments_written: int = 0


class FaktiBgScraper:
    """
    Scraper for fakti.bg category pages and article comments.
    """

    def __init__(self, session_timestamp: str, log_level: str) -> None:
        """
        Initialize the scraper.

        Args:
            session_timestamp: Session timestamp for the current run.
            log_level: Requested log level.
        """

        self.source_name = SOURCE_NAME_FAKTI_BG
        self.session_timestamp = session_timestamp
        self.logger = configure_logger(
            source_name=self.source_name,
            session_timestamp=self.session_timestamp,
            log_level=log_level,
        )
        self.request_service = RequestService(logger=self.logger)
        self.stats = FaktiBgScraperStats()

    def run(self) -> None:
        """
        Run the scraper for all configured fakti.bg category URLs.

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
            for category_url in category_urls:
                self._process_category_chain(
                    start_category_url=category_url,
                    csv_writer=csv_writer,
                )

        self._log_summary()

    def _process_category_chain(
        self,
        start_category_url: str,
        csv_writer: CsvWriter,
    ) -> None:
        """
        Process all pages of one category by following next-page links.

        Args:
            start_category_url: First category page URL.
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

            response = self.request_service.get(current_url)

            if response is None:
                log_error(
                    self.logger,
                    f"Failed to fetch category page | url={current_url}",
                )
                break

            html = response.text

            self._process_single_category_page(
                category_url=current_url,
                html=html,
                csv_writer=csv_writer,
            )

            current_url = get_next_page_url(
                html=html,
                category_url=current_url,
                logger=self.logger,
            )

    def _process_single_category_page(
        self,
        category_url: str,
        html: str,
        csv_writer: CsvWriter,
    ) -> None:
        """
        Process a single category page.

        Args:
            category_url: Category page URL.
            html: Raw category page HTML.
            csv_writer: Active CSV writer.
        """

        log_info(
            self.logger,
            f"Processing category page | url={category_url}",
        )

        articles = parse_category_page(
            html=html,
            category_url=category_url,
            logger=self.logger,
        )

        self.stats.category_pages_processed += 1
        self.stats.articles_discovered += len(articles)

        for article in articles:
            self._process_article(
                category_url=category_url,
                article=article,
                csv_writer=csv_writer,
            )

    def _process_article(
        self,
        category_url: str,
        article: FaktiBgCategoryArticle,
        csv_writer: CsvWriter,
    ) -> None:
        """
        Fetch an article page and process its comments.

        Args:
            category_url: Source category URL.
            article: Parsed article metadata.
            csv_writer: Active CSV writer.
        """

        if article.comment_count <= 0:
            self.stats.articles_skipped_zero_comments += 1

            log_info(
                self.logger,
                (
                    f"Skipping article with zero comments "
                    f"| article_url={article.article_url}"
                ),
            )
            return

        log_info(
            self.logger,
            (
                f"Fetching article | article_url={article.article_url} "
                f"| expected_comments={article.comment_count}"
            ),
        )

        response = self.request_service.get(article.article_url)

        if response is None:
            log_error(
                self.logger,
                f"Failed to fetch article page | article_url={article.article_url}",
            )
            return

        self.stats.articles_processed += 1

        parsed_comments = parse_comments(
            html=response.text,
            article_url=article.article_url,
            logger=self.logger,
        )

        if not parsed_comments:
            log_warning(
                self.logger,
                (
                    f"No comments parsed despite expected count "
                    f"| article_url={article.article_url} "
                    f"| expected_comments={article.comment_count}"
                ),
            )
            return

        for parsed_comment in parsed_comments:
            self._write_comment_record(
                category_url=category_url,
                article=article,
                parsed_comment=parsed_comment,
                csv_writer=csv_writer,
            )

        log_info(
            self.logger,
            (
                f"Comments written | article_url={article.article_url} "
                f"| parsed_comments={len(parsed_comments)} "
                f"| expected_comments={article.comment_count}"
            ),
        )

    def _write_comment_record(
        self,
        category_url: str,
        article: FaktiBgCategoryArticle,
        parsed_comment: FaktiBgParsedComment,
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
            source_site="fakti.bg",
            category_url=category_url,
            article_url=article.article_url,
            article_title=article.article_title,
            article_published_at=article.article_published_at,
            article_views=article.article_views,
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
                f"fakti.bg scraper finished "
                f"| category_pages_processed={self.stats.category_pages_processed} "
                f"| articles_discovered={self.stats.articles_discovered} "
                f"| articles_skipped_zero_comments="
                f"{self.stats.articles_skipped_zero_comments} "
                f"| articles_processed={self.stats.articles_processed} "
                f"| comments_written={self.stats.comments_written}"
            ),
        )


def run_fakti_bg_scraper(
    session_timestamp: str,
    log_level: str = DEFAULT_LOG_LEVEL,
) -> None:
    """
    Run the fakti.bg scraper.

    Args:
        session_timestamp: Session timestamp for the current run.
        log_level: Requested log level.
    """

    scraper = FaktiBgScraper(
        session_timestamp=session_timestamp,
        log_level=log_level,
    )
    scraper.run()

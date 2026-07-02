"""
Scraper implementation for dnes.bg.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import DEFAULT_LOG_LEVEL, SOURCE_NAME_DNES_BG
from models.comment_record import CommentRecord
from parsers.dnes_bg_parser import (
    DnesBgCategoryArticle,
    DnesBgParsedComment,
    build_comments_url,
    generate_category_page_urls,
    generate_comments_page_urls,
    parse_category_page,
    parse_comments_page,
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
class DnesBgScraperStats:
    """
    Runtime statistics for a dnes.bg scraper run.
    """

    category_pages_processed: int = 0
    articles_discovered: int = 0
    articles_skipped_zero_comments: int = 0
    comments_pages_processed: int = 0
    comments_written: int = 0


class DnesBgScraper:
    """
    Scraper for dnes.bg category pages and comments pages.
    """

    def __init__(self, session_timestamp: str, log_level: str) -> None:
        """
        Initialize the scraper.

        Args:
            session_timestamp: Session timestamp for the current run.
            log_level: Requested log level.
        """

        self.source_name = SOURCE_NAME_DNES_BG
        self.session_timestamp = session_timestamp
        self.logger = configure_logger(
            source_name=self.source_name,
            session_timestamp=self.session_timestamp,
            log_level=log_level,
        )
        self.request_service = RequestService(logger=self.logger)
        self.stats = DnesBgScraperStats()

    def run(self) -> None:
        """
        Run the scraper for all configured dnes.bg category URLs.

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
        Process one category and all of its pages.

        Args:
            start_category_url: First category page URL.
            csv_writer: Active CSV writer.
        """

        first_response = self.request_service.get(start_category_url)

        if first_response is None:
            log_error(
                self.logger,
                f"Failed to fetch initial category page | url={start_category_url}",
            )
            return

        category_page_urls = generate_category_page_urls(
            html=first_response.text,
            category_url=start_category_url,
            logger=self.logger,
        )

        total_category_pages = len(category_page_urls)

        for page_index, category_page_url in enumerate(
            category_page_urls,
            start=1,
        ):
            log_debug(
                self.logger,
                (
                    f"Parsing category page {page_index} of {total_category_pages} "
                    f"| url={category_page_url}"
                ),
            )

            if page_index == 1:
                html = first_response.text
            else:
                response = self.request_service.get(category_page_url)

                if response is None:
                    log_error(
                        self.logger,
                        (
                            f"Failed to fetch category page "
                            f"| url={category_page_url}"
                        ),
                    )
                    continue

                html = response.text

            self._process_single_category_page(
                category_url=category_page_url,
                html=html,
                csv_writer=csv_writer,
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

        log_info(
            self.logger,
            (
                f"Parsed category page | url={category_url} "
                f"| articles_found={len(articles)}"
            ),
        )

        for article in articles:
            self._process_category_article(
                category_url=category_url,
                article=article,
                csv_writer=csv_writer,
            )

    def _process_category_article(
        self,
        category_url: str,
        article: DnesBgCategoryArticle,
        csv_writer: CsvWriter,
    ) -> None:
        """
        Process one article discovered in a category page.

        Args:
            category_url: Source category URL.
            article: Parsed category article metadata.
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

        comments_url = build_comments_url(article.article_url)

        if not comments_url:
            log_warning(
                self.logger,
                (
                    f"Could not build comments URL "
                    f"| article_url={article.article_url}"
                ),
            )
            return

        log_info(
            self.logger,
            (
                f"Processing comments page | article_url={article.article_url} "
                f"| comments_url={comments_url} "
                f"| expected_comment_count={article.comment_count}"
            ),
        )

        first_response = self.request_service.get(comments_url)

        if first_response is None:
            log_error(
                self.logger,
                (
                    f"Failed to fetch comments page "
                    f"| article_url={article.article_url} "
                    f"| comments_url={comments_url}"
                ),
            )
            return

        comments_page_urls = generate_comments_page_urls(
            html=first_response.text,
            comments_url=comments_url,
            logger=self.logger,
        )

        total_comments_pages = len(comments_page_urls)
        total_parsed_comments = 0

        for page_index, comments_page_url in enumerate(
            comments_page_urls,
            start=1,
        ):
            log_debug(
                self.logger,
                (
                    f"Parsing comments page {page_index} of {total_comments_pages} "
                    f"| url={comments_page_url}"
                ),
            )

            if page_index == 1:
                html = first_response.text
            else:
                response = self.request_service.get(comments_page_url)

                if response is None:
                    log_error(
                        self.logger,
                        (
                            f"Failed to fetch comments pagination page "
                            f"| article_url={article.article_url} "
                            f"| comments_url={comments_page_url}"
                        ),
                    )
                    continue

                html = response.text

            parsed_comments = parse_comments_page(
                html=html,
                logger=self.logger,
            )
            self.stats.comments_pages_processed += 1
            total_parsed_comments += len(parsed_comments)

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
                f"Parsed comments pages | article_url={article.article_url} "
                f"| parsed_comments={total_parsed_comments} "
                f"| expected_comments={article.comment_count} "
                f"| comments_pages={total_comments_pages}"
            ),
        )

    def _write_comment_record(
        self,
        category_url: str,
        article: DnesBgCategoryArticle,
        parsed_comment: DnesBgParsedComment,
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
            source_site="dnes.bg",
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
                f"dnes.bg scraper finished "
                f"| category_pages_processed={self.stats.category_pages_processed} "
                f"| articles_discovered={self.stats.articles_discovered} "
                f"| articles_skipped_zero_comments="
                f"{self.stats.articles_skipped_zero_comments} "
                f"| comments_pages_processed={self.stats.comments_pages_processed} "
                f"| comments_written={self.stats.comments_written}"
            ),
        )


def run_dnes_bg_scraper(
    session_timestamp: str,
    log_level: str = DEFAULT_LOG_LEVEL,
) -> None:
    """
    Run the dnes.bg scraper.

    Args:
        session_timestamp: Session timestamp for the current run.
        log_level: Requested log level.
    """

    scraper = DnesBgScraper(
        session_timestamp=session_timestamp,
        log_level=log_level,
    )
    scraper.run()

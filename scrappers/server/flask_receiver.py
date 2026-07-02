"""
Flask receiver server for dir.bg comments scraping via Tampermonkey.

Responsibilities:
- Serve task instructions to the Tampermonkey browser script.
- Accept scraped results (articles and comments) from Tampermonkey.
- Write comment records to a CSV file via CsvWriter.
- Automatically shut down after a configurable inactivity timeout.

Task lifecycle:
  1. Category page URLs are loaded from input_urls/dir_bg.txt on startup.
  2. Tampermonkey polls GET /api/task → receives a scrape_category or
     scrape_comments instruction (or noop when queues are empty).
  3. Tampermonkey POSTs results to POST /api/task/complete.
  4. Flask processes results: enqueues discovered articles or writes
     comment records to CSV, then optionally enqueues a next-page task.
  5. If no POST is received for DIR_BG_INACTIVITY_TIMEOUT_SECONDS, the
     server shuts itself down automatically.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from typing import Any

from flask import Flask, Response, jsonify, request

from config import (
    DIR_BG_INACTIVITY_TIMEOUT_SECONDS,
    FLASK_DEBUG,
    FLASK_HOST,
    FLASK_PORT,
    SOURCE_NAME_DIR_BG,
)
from models.comment_record import CommentRecord
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


# ---------------------------------------------------------------------------
# Task type constants
# ---------------------------------------------------------------------------

TASK_SCRAPE_CATEGORY: str = "scrape_category"
TASK_SCRAPE_COMMENTS: str = "scrape_comments"
TASK_NOOP: str = "noop"


# ---------------------------------------------------------------------------
# Server state
# ---------------------------------------------------------------------------

_category_page_queue: deque[str] = deque()
_comments_task_queue: deque[dict[str, str]] = deque()
_queue_lock: threading.Lock = threading.Lock()
_csv_writer: CsvWriter | None = None
_logger: logging.Logger | None = None

# Timestamp of the last POST received from Tampermonkey.
# Updated on every /api/task/complete request.
# Used by the inactivity watchdog to decide when to shut down.
_last_activity_time: float = 0.0
_activity_lock: threading.Lock = threading.Lock()


def _get_logger() -> logging.Logger:
    """
    Return the active module logger.

    Returns:
        logging.Logger: Configured logger instance.

    Raises:
        RuntimeError: If the logger has not been initialised yet.
    """

    if _logger is None:
        raise RuntimeError(
            "Flask receiver logger has not been initialised. "
            "Call run_dir_bg_server() to start the server."
        )
    return _logger


# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------

app = Flask(__name__)


def _cors_response(payload: dict[str, Any], status: int = 200) -> Response:
    """
    Build a JSON response with CORS headers required by the Tampermonkey
    script running in the browser.

    Args:
        payload: Dictionary to serialise as JSON.
        status: HTTP status code.

    Returns:
        Response: Flask response with CORS headers.
    """

    response = jsonify(payload)
    response.status_code = status
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/task", methods=["GET", "OPTIONS"])
def get_task() -> Response:
    """
    Return the next pending task for the Tampermonkey script.

    The priority order is:
      1. scrape_category — if any category page URL is queued.
      2. scrape_comments — if any comments task is queued.
      3. noop            — when both queues are empty.

    Returns:
        Response: JSON task description.
    """

    if request.method == "OPTIONS":
        return _cors_response({})

    logger = _get_logger()

    with _queue_lock:
        if _category_page_queue:
            url = _category_page_queue.popleft()
            log_debug(
                logger,
                f"Dispatching scrape_category task | url={url}",
            )
            return _cors_response(
                {
                    "task": TASK_SCRAPE_CATEGORY,
                    "url": url,
                }
            )

        if _comments_task_queue:
            task_data = _comments_task_queue.popleft()
            log_debug(
                logger,
                (
                    f"Dispatching scrape_comments task "
                    f"| comments_url={task_data.get('comments_url')}"
                ),
            )
            return _cors_response(
                {
                    "task": TASK_SCRAPE_COMMENTS,
                    **task_data,
                }
            )

    log_debug(logger, "No pending tasks — returning noop")
    return _cors_response({"task": TASK_NOOP})


@app.route("/api/task/complete", methods=["POST", "OPTIONS"])
def complete_task() -> Response:
    """
    Accept the result of a completed Tampermonkey task.

    For scrape_category results:
      - Enqueues the next category page URL if present.
      - Enqueues a scrape_comments task for each discovered article.

    For scrape_comments results:
      - Enqueues the next comments page URL if present.
      - Writes each received comment as a CommentRecord to CSV.

    Returns:
        Response: JSON acknowledgement.
    """

    if request.method == "OPTIONS":
        return _cors_response({})

    logger = _get_logger()

    # Record the time of this incoming POST for the inactivity watchdog.
    global _last_activity_time  # noqa: PLW0603
    with _activity_lock:
        _last_activity_time = time.monotonic()

    try:
        body = request.get_json(force=True, silent=True)
    except Exception:  # pylint: disable=broad-exception-caught
        body = None

    if not body or not isinstance(body, dict):
        log_warning(logger, "Received malformed or empty POST body")
        return _cors_response({"error": "invalid body"}, status=400)

    task_type = body.get("task")

    if task_type == TASK_SCRAPE_CATEGORY:
        return _handle_category_result(body, logger)

    if task_type == TASK_SCRAPE_COMMENTS:
        return _handle_comments_result(body, logger)

    log_warning(logger, f"Unknown task type in POST body | task={task_type}")
    return _cors_response({"error": "unknown task"}, status=400)


# ---------------------------------------------------------------------------
# Result handlers
# ---------------------------------------------------------------------------

def _handle_category_result(
    body: dict[str, Any],
    logger: logging.Logger,
) -> Response:
    """
    Process a scrape_category POST result.

    Enqueues the next category page and all discovered articles for
    comment scraping.

    Args:
        body: Parsed JSON request body.
        logger: Logger instance.

    Returns:
        Response: JSON acknowledgement.
    """

    source_url: str = body.get("source_url", "")
    next_page_url: str | None = body.get("next_page_url") or None
    articles: list[dict[str, str]] = body.get("articles", [])

    if not isinstance(articles, list):
        log_warning(
            logger,
            (
                f"scrape_category result has no articles list "
                f"| source_url={source_url}"
            ),
        )
        articles = []

    with _queue_lock:
        if next_page_url:
            _category_page_queue.appendleft(next_page_url)
            log_info(
                logger,
                (
                    f"Enqueued next category page "
                    f"| url={next_page_url}"
                ),
            )

        for article in articles:
            article_url = article.get("article_url", "").strip()
            comments_url = article.get("comments_url", "").strip()

            if not article_url or not comments_url:
                log_warning(
                    logger,
                    (
                        f"Skipping article with missing URL fields "
                        f"| article_url={article_url!r} "
                        f"| comments_url={comments_url!r}"
                    ),
                )
                continue

            _comments_task_queue.append(
                {
                    "comments_url": comments_url,
                    "article_url": article_url,
                    "article_title": article.get("article_title", ""),
                    "article_date": article.get("article_date", ""),
                    "article_views": article.get("article_views", ""),
                    "category_url": source_url,
                }
            )

    log_info(
        logger,
        (
            f"scrape_category result processed "
            f"| source_url={source_url} "
            f"| articles_enqueued={len(articles)} "
            f"| has_next_page={next_page_url is not None}"
        ),
    )
    return _cors_response({"status": "ok"})


def _handle_comments_result(
    body: dict[str, Any],
    logger: logging.Logger,
) -> Response:
    """
    Process a scrape_comments POST result.

    Enqueues the next comments page if present, then writes each
    received comment to the CSV output file.

    Args:
        body: Parsed JSON request body.
        logger: Logger instance.

    Returns:
        Response: JSON acknowledgement.
    """

    source_url: str = body.get("source_url", "")
    article_url: str = body.get("article_url", "")
    article_title: str = body.get("article_title", "")
    article_date: str = body.get("article_date", "")
    article_views: str = body.get("article_views", "")
    category_url: str = body.get("category_url", "")
    next_page_url: str | None = body.get("next_page_url") or None
    comments: list[dict[str, Any]] = body.get("comments", [])

    if not isinstance(comments, list):
        log_warning(
            logger,
            (
                f"scrape_comments result has no comments list "
                f"| source_url={source_url}"
            ),
        )
        comments = []

    with _queue_lock:
        if next_page_url:
            _comments_task_queue.appendleft(
                {
                    "comments_url": next_page_url,
                    "article_url": article_url,
                    "article_title": article_title,
                    "article_date": article_date,
                    "article_views": article_views,
                    "category_url": category_url,
                }
            )
            log_info(
                logger,
                (
                    f"Enqueued next comments page "
                    f"| url={next_page_url}"
                ),
            )

    written_count = 0
    skipped_count = 0

    for raw_comment in comments:
        try:
            comment_id = str(raw_comment.get("comment_id", "")).strip()
            comment_text = str(raw_comment.get("comment_text", "")).strip()
            username = str(raw_comment.get("username", "")).strip()
            comment_date = str(raw_comment.get("timestamp", "")).strip()
            vote_up = str(raw_comment.get("vote_up", "0")).strip()
            vote_down = str(raw_comment.get("vote_down", "0")).strip()

            if not comment_id or not comment_text:
                log_debug(
                    logger,
                    (
                        f"Skipping comment with empty required fields "
                        f"| comment_id={comment_id!r} "
                        f"| source_url={source_url}"
                    ),
                )
                skipped_count += 1
                continue

            record = CommentRecord(
                source_site="dir.bg",
                category_url=category_url,
                article_url=article_url,
                article_title=article_title,
                article_published_at=article_date,
                article_views=article_views,
                comment_index=comment_id,
                comment=comment_text,
                author=username,
                comment_date=comment_date,
                likes=vote_up,
                dislikes=vote_down,
                scraped_at=get_scraped_at_timestamp(),
            )

            record.validate()

            if _csv_writer is not None:
                _csv_writer.write_record(record)
                written_count += 1
            else:
                log_error(
                    logger,
                    "CSV writer is not initialised — cannot write record",
                )

        except (KeyError, TypeError, ValueError) as exc:
            log_error(
                logger,
                (
                    f"Failed to write comment record "
                    f"| comment_id={raw_comment.get('comment_id')!r} "
                    f"| error={exc}"
                ),
            )

        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_error(
                logger,
                (
                    f"Unexpected error while writing comment record "
                    f"| comment_id={raw_comment.get('comment_id')!r} "
                    f"| error={exc}"
                ),
            )

    log_info(
        logger,
        (
            f"scrape_comments result processed "
            f"| source_url={source_url} "
            f"| written={written_count} "
            f"| skipped={skipped_count} "
            f"| has_next_page={next_page_url is not None}"
        ),
    )
    return _cors_response({"status": "ok"})


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

def _start_inactivity_watchdog(logger: logging.Logger) -> None:
    """
    Start a background daemon thread that monitors Tampermonkey activity.

    If no POST request is received within DIR_BG_INACTIVITY_TIMEOUT_SECONDS,
    the thread logs a shutdown message and terminates the process.

    Args:
        logger: Logger instance for shutdown messages.

    Returns:
        None
    """

    def _watchdog() -> None:
        """Background loop that checks inactivity every 30 seconds."""

        check_interval_seconds: int = 30

        while True:
            time.sleep(check_interval_seconds)

            with _activity_lock:
                elapsed = time.monotonic() - _last_activity_time

            if elapsed >= DIR_BG_INACTIVITY_TIMEOUT_SECONDS:
                log_info(
                    logger,
                    (
                        f"No activity from Tampermonkey for "
                        f"{elapsed:.0f}s "
                        f"(timeout={DIR_BG_INACTIVITY_TIMEOUT_SECONDS}s) "
                        f"— shutting down automatically"
                    ),
                )
                if _csv_writer is not None:
                    _csv_writer.close()
                    log_info(logger, "CSV writer closed by watchdog")
                os._exit(0)  # Hard exit — bypasses Flask's blocking serve loop

    thread = threading.Thread(target=_watchdog, daemon=True, name="inactivity-watchdog")
    thread.start()
    log_info(
        logger,
        (
            f"Inactivity watchdog started "
            f"| timeout={DIR_BG_INACTIVITY_TIMEOUT_SECONDS}s"
        ),
    )


def run_dir_bg_server(
    session_timestamp: str,
    log_level: str,
) -> None:
    """
    Initialise state and start the Flask receiver server.

    Loads category URLs from input_urls/dir_bg.txt, opens the CSV writer,
    starts the inactivity watchdog thread, and starts the blocking Flask
    HTTP server on the configured host/port.

    The server shuts down automatically when no POST from Tampermonkey is
    received for DIR_BG_INACTIVITY_TIMEOUT_SECONDS consecutive seconds.

    Args:
        session_timestamp: Session timestamp for file naming.
        log_level: Logging level for this run.

    Returns:
        None
    """

    global _logger, _csv_writer, _last_activity_time  # noqa: PLW0603

    _logger = configure_logger(
        source_name=SOURCE_NAME_DIR_BG,
        session_timestamp=session_timestamp,
        log_level=log_level,
    )

    log_info(
        _logger,
        (
            f"Initialising dir.bg receiver server "
            f"| session={session_timestamp} "
            f"| host={FLASK_HOST} "
            f"| port={FLASK_PORT}"
        ),
    )

    try:
        source_urls = load_source_urls(SOURCE_NAME_DIR_BG)
    except (FileNotFoundError, OSError) as exc:
        log_error(
            _logger,
            f"Failed to load dir.bg source URLs | error={exc}",
        )
        return

    if not source_urls:
        log_warning(
            _logger,
            "No source URLs found in input_urls/dir_bg.txt — nothing to do",
        )
        return

    with _queue_lock:
        _category_page_queue.clear()
        _comments_task_queue.clear()
        for url in source_urls:
            _category_page_queue.append(url)

    log_info(
        _logger,
        f"Loaded {len(source_urls)} category URL(s) into queue",
    )

    _csv_writer = CsvWriter(
        source_name=SOURCE_NAME_DIR_BG,
        session_timestamp=session_timestamp,
    )

    log_info(
        _logger,
        f"CSV writer opened | path={_csv_writer.file_path}",
    )

    # Reset the activity clock and start the watchdog.
    with _activity_lock:
        _last_activity_time = time.monotonic()

    _start_inactivity_watchdog(_logger)

    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=FLASK_DEBUG,
            use_reloader=False,
        )

    except OSError as exc:
        log_error(
            _logger,
            (
                f"Failed to start Flask server "
                f"| host={FLASK_HOST} "
                f"| port={FLASK_PORT} "
                f"| error={exc}"
            ),
        )

    except Exception as exc:  # pylint: disable=broad-exception-caught
        log_error(
            _logger,
            f"Unexpected Flask server error | error={exc}",
        )

    finally:
        if _csv_writer is not None:
            _csv_writer.close()
            log_info(_logger, "CSV writer closed")

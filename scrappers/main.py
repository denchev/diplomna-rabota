"""
Main entry point for the marush_denchev_comments_scraper project.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from config import (
    CREATE_OUTPUT_DIRECTORIES_ON_STARTUP,
    DEFAULT_LOG_LEVEL,
    LOGS_DIR,
    OUTPUT_DIR,
    SOURCE_NAME_DNES_BG,
    SOURCE_NAME_DIR_BG,
    SOURCE_NAME_FAKTI_BG,
    SOURCE_NAME_MEDIAPOOL_BG,
    SUPPORTED_SOURCE_NAMES,
)
from scrapers.dnes_bg_scraper import run_dnes_bg_scraper
from scrapers.fakti_bg_scraper import run_fakti_bg_scraper
from scrapers.mediapool_bg_scraper import run_mediapool_bg_scraper
from server.flask_receiver import run_dir_bg_server as _run_dir_bg_server
from services.logging_service import configure_logger, log_error, log_info
from utils.date_utils import get_session_timestamp
from utils.file_utils import ensure_directory_exists


def ensure_runtime_directories_exist() -> None:
    """
    Ensure that required runtime directories exist.

    Creates output and logs directories when startup directory creation
    is enabled in configuration.
    """

    if not CREATE_OUTPUT_DIRECTORIES_ON_STARTUP:
        return

    ensure_directory_exists(OUTPUT_DIR)
    ensure_directory_exists(LOGS_DIR)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Run a source scraper or start the dir.bg receiver mode "
            "for marush_denchev_comments_scraper."
        )
    )

    parser.add_argument(
        "mode",
        choices=("scrape", "server"),
        help="Execution mode: scrape a source or start server mode.",
    )

    parser.add_argument(
        "--source",
        choices=SUPPORTED_SOURCE_NAMES,
        help=(
            "Source name to run in scrape mode. Required for scrape mode. "
            "Ignored in server mode."
        ),
    )

    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        help="Log level to use for the current run.",
    )

    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate parsed command-line arguments.

    Args:
        args: Parsed command-line arguments.

    Raises:
        ValueError: If the provided arguments are invalid.
    """

    if args.mode == "scrape" and not args.source:
        raise ValueError("--source is required when mode is 'scrape'")

    if args.mode == "server" and args.source:
        raise ValueError("--source must not be used when mode is 'server'")


def run_dir_bg_server(
    session_timestamp: str,
    log_level: str,
) -> None:
    """
    Start the dir.bg Flask receiver server.

    Delegates to the flask_receiver module which manages the task queue,
    CSV writer and HTTP endpoints for the Tampermonkey integration.

    Args:
        session_timestamp: Session timestamp for file naming.
        log_level: Logging level for this run.

    Returns:
        None
    """

    _run_dir_bg_server(
        session_timestamp=session_timestamp,
        log_level=log_level,
    )


def get_scraper_runner(
    source_name: str,
    session_timestamp: str,
    log_level: str,
) -> Callable[[], None]:
    """
    Resolve the scraper runner function for a given source.

    Args:
        source_name: Normalized source name.
        session_timestamp: Session timestamp for the current run.
        log_level: Requested log level.

    Returns:
        Callable[[], None]: Source-specific runner function.

    Raises:
        ValueError: If the source is unsupported.
    """

    runner_map: dict[str, Callable[[], None]] = {
        SOURCE_NAME_DNES_BG: lambda: run_dnes_bg_scraper(
            session_timestamp=session_timestamp,
            log_level=log_level,
        ),
        SOURCE_NAME_FAKTI_BG: lambda: run_fakti_bg_scraper(
            session_timestamp=session_timestamp,
            log_level=log_level,
        ),
        SOURCE_NAME_MEDIAPOOL_BG: lambda: run_mediapool_bg_scraper(
            session_timestamp=session_timestamp,
            log_level=log_level,
        ),
        SOURCE_NAME_DIR_BG: lambda: run_dir_bg_server(
            session_timestamp=session_timestamp,
            log_level=log_level,
        ),
    }

    if source_name not in runner_map:
        raise ValueError(f"Unsupported source: {source_name}")

    return runner_map[source_name]


def run_scrape_mode(
    source_name: str,
    session_timestamp: str,
    log_level: str,
) -> int:
    """
    Run scraper mode for a selected source.

    Args:
        source_name: Source to scrape.
        session_timestamp: Session timestamp for this run.
        log_level: Requested log level.

    Returns:
        int: Process exit code.
    """

    logger = configure_logger(
        source_name=source_name,
        session_timestamp=session_timestamp,
        log_level=log_level,
    )

    log_info(
        logger,
        (
            f"Starting scrape mode | source={source_name} "
            f"| session={session_timestamp}"
        ),
    )

    try:
        runner = get_scraper_runner(
            source_name=source_name,
            session_timestamp=session_timestamp,
            log_level=log_level,
        )
        runner()

        log_info(
            logger,
            (
                f"Scrape mode finished successfully | source={source_name} "
                f"| session={session_timestamp}"
            ),
        )
        return 0

    except NotImplementedError as exc:
        log_error(
            logger,
            (
                f"Scrape mode not implemented yet | source={source_name} "
                f"| error={exc}"
            ),
        )
        return 1

    except ValueError as exc:
        log_error(
            logger,
            (
                f"Invalid scrape mode configuration | source={source_name} "
                f"| error={exc}"
            ),
        )
        return 1

    except Exception as exc:  # pylint: disable=broad-exception-caught
        log_error(
            logger,
            (
                f"Unexpected error in scrape mode | source={source_name} "
                f"| error={exc}"
            ),
        )
        return 1


def run_server_mode(
    session_timestamp: str,
    log_level: str,
) -> int:
    """
    Run server mode for dir.bg receiver integration.

    Args:
        session_timestamp: Session timestamp for this run.
        log_level: Requested log level.

    Returns:
        int: Process exit code.
    """

    logger = configure_logger(
        source_name=SOURCE_NAME_DIR_BG,
        session_timestamp=session_timestamp,
        log_level=log_level,
    )

    log_info(
        logger,
        f"Starting server mode | session={session_timestamp}",
    )

    try:
        run_dir_bg_server(
            session_timestamp=session_timestamp,
            log_level=log_level,
        )

        log_info(
            logger,
            f"Server mode finished successfully | session={session_timestamp}",
        )
        return 0

    except NotImplementedError as exc:
        log_error(
            logger,
            f"Server mode not implemented yet | error={exc}",
        )
        return 1

    except Exception as exc:  # pylint: disable=broad-exception-caught
        log_error(
            logger,
            f"Unexpected error in server mode | error={exc}",
        )
        return 1


def main() -> int:
    """
    Main application entry point.

    Returns:
        int: Process exit code.
    """

    try:
        ensure_runtime_directories_exist()

        args = parse_arguments()
        validate_arguments(args)

        session_timestamp = get_session_timestamp()

        if args.mode == "scrape":
            return run_scrape_mode(
                source_name=args.source,
                session_timestamp=session_timestamp,
                log_level=args.log_level,
            )

        return run_server_mode(
            session_timestamp=session_timestamp,
            log_level=args.log_level,
        )

    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Fatal startup error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Logging service for scraper runs.

This module provides per-source loggers that write to dedicated log files
and mirror messages to stdout according to the configured log level.
"""

from __future__ import annotations

import logging
from pathlib import Path

from config import (
    DEFAULT_LOG_LEVEL,
    LOG_FILE_TEMPLATE,
    LOGS_DIR,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
)


SUPPORTED_LOG_LEVELS: dict[str, int] = {
    LOG_LEVEL_DEBUG: logging.DEBUG,
    LOG_LEVEL_INFO: logging.INFO,
    LOG_LEVEL_WARNING: logging.WARNING,
    LOG_LEVEL_ERROR: logging.ERROR,
}


def ensure_logs_directory_exists() -> None:
    """
    Ensure that the logs directory exists.

    Raises:
        OSError: If the directory cannot be created.
    """

    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file_path(source_name: str, session_timestamp: str) -> Path:
    """
    Build the log file path for a source and session.

    Args:
        source_name: Normalized source name such as 'dnes_bg'.
        session_timestamp: Session timestamp in YYYY-MM-DD_HH-MM-SS format.

    Returns:
        Path: Full path to the log file.
    """

    log_filename = LOG_FILE_TEMPLATE.format(
        source_name=source_name,
        session_timestamp=session_timestamp,
    )
    return LOGS_DIR / log_filename


def resolve_log_level(log_level: str) -> int:
    """
    Resolve a string log level to a logging module constant.

    Args:
        log_level: Requested log level string.

    Returns:
        int: Logging module log level.

    Raises:
        ValueError: If the log level is unsupported.
    """

    normalized_log_level = log_level.strip().upper()

    if normalized_log_level not in SUPPORTED_LOG_LEVELS:
        raise ValueError(f"Unsupported log level: {log_level}")

    return SUPPORTED_LOG_LEVELS[normalized_log_level]


def get_logger_name(source_name: str, session_timestamp: str) -> str:
    """
    Build a unique logger name for a source and session.

    Args:
        source_name: Normalized source name such as 'dnes_bg'.
        session_timestamp: Session timestamp in YYYY-MM-DD_HH-MM-SS format.

    Returns:
        str: Unique logger name.
    """

    return f"{source_name}_{session_timestamp}"


def configure_logger(
    source_name: str,
    session_timestamp: str,
    log_level: str = DEFAULT_LOG_LEVEL,
) -> logging.Logger:
    """
    Configure and return a per-source, per-session logger.

    The logger writes to a dedicated log file and to stdout.

    Args:
        source_name: Normalized source name such as 'dnes_bg'.
        session_timestamp: Session timestamp in YYYY-MM-DD_HH-MM-SS format.
        log_level: Desired log level string.

    Returns:
        logging.Logger: Configured logger.

    Raises:
        ValueError: If the log level is unsupported.
        OSError: If the log directory cannot be created.
    """

    ensure_logs_directory_exists()

    logger_name = get_logger_name(
        source_name=source_name,
        session_timestamp=session_timestamp,
    )
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger

    resolved_log_level = resolve_log_level(log_level=log_level)
    logger.setLevel(resolved_log_level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_file_path = get_log_file_path(
        source_name=source_name,
        session_timestamp=session_timestamp,
    )

    file_handler = logging.FileHandler(
        filename=log_file_path,
        encoding="utf-8",
    )
    file_handler.setLevel(resolved_log_level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(resolved_log_level)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def log_debug(logger: logging.Logger, message: str) -> None:
    """
    Log and print a debug message.

    Args:
        logger: Configured logger.
        message: Message to log.
    """

    logger.debug(message)


def log_info(logger: logging.Logger, message: str) -> None:
    """
    Log and print an info message.

    Args:
        logger: Configured logger.
        message: Message to log.
    """

    logger.info(message)


def log_warning(logger: logging.Logger, message: str) -> None:
    """
    Log and print a warning message.

    Args:
        logger: Configured logger.
        message: Message to log.
    """

    logger.warning(message)


def log_error(logger: logging.Logger, message: str) -> None:
    """
    Log and print an error message.

    Args:
        logger: Configured logger.
        message: Message to log.
    """

    logger.error(message)

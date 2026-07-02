"""
Central configuration for the marush_denchev_comments_scraper project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final


PROJECT_NAME: Final[str] = "marush_denchev_comments_scraper"
BASE_DIR: Final[Path] = Path(__file__).resolve().parent

OUTPUT_DIR: Final[Path] = BASE_DIR / "output"
LOGS_DIR: Final[Path] = BASE_DIR / "logs"
BROWSER_SCRIPTS_DIR: Final[Path] = BASE_DIR / "browser_scripts"

SESSION_TIMESTAMP_FORMAT: Final[str] = "%Y-%m-%d_%H-%M-%S"
SCRAPED_AT_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

DEFAULT_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,bg;q=0.8",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT_SECONDS: Final[int] = 20
REQUEST_MAX_RETRIES: Final[int] = 3
REQUEST_RETRY_SLEEP_SECONDS: Final[float] = 3.0

REQUEST_DELAY_MIN_SECONDS: Final[float] = 1.0
REQUEST_DELAY_MAX_SECONDS: Final[float] = 2.5

DEBUG_REQUEST_DELAY_MIN_SECONDS: Final[float] = 0.5
DEBUG_REQUEST_DELAY_MAX_SECONDS: Final[float] = 1.0

LOG_LEVEL_DEBUG: Final[str] = "DEBUG"
LOG_LEVEL_INFO: Final[str] = "INFO"
LOG_LEVEL_WARNING: Final[str] = "WARNING"
LOG_LEVEL_ERROR: Final[str] = "ERROR"

DEFAULT_LOG_LEVEL: Final[str] = LOG_LEVEL_INFO

OUTPUT_FILE_EXTENSION: Final[str] = "csv"
OUTPUT_FILE_TEMPLATE: Final[str] = "{source_name}_data_{session_timestamp}.{extension}"
LOG_FILE_TEMPLATE: Final[str] = "{source_name}_{session_timestamp}.log"

SOURCE_NAME_DNES_BG: Final[str] = "dnes_bg"
SOURCE_NAME_MEDIAPOOL_BG: Final[str] = "mediapool_bg"
SOURCE_NAME_FAKTI_BG: Final[str] = "fakti_bg"
SOURCE_NAME_DIR_BG: Final[str] = "dir_bg"

SUPPORTED_SOURCE_NAMES: Final[tuple[str, ...]] = (
    SOURCE_NAME_DNES_BG,
    SOURCE_NAME_MEDIAPOOL_BG,
    SOURCE_NAME_FAKTI_BG,
    SOURCE_NAME_DIR_BG,
)

# Set to False during development to see the browser window.
# Set to True for production to run Playwright in the background.
PLAYWRIGHT_HEADLESS: Final[bool] = True

FLASK_HOST: Final[str] = "127.0.0.1"
FLASK_PORT: Final[int] = 5000
FLASK_DEBUG: Final[bool] = False

DIR_BG_RECEIVER_ENDPOINT: Final[str] = "/api/dir-bg/comment-records"

# Inactivity timeout for the dir.bg Flask receiver server.
# If no POST from Tampermonkey is received within this many seconds,
# the server shuts down automatically.
DIR_BG_INACTIVITY_TIMEOUT_SECONDS: Final[int] = 300  # 5 minutes

CREATE_OUTPUT_DIRECTORIES_ON_STARTUP: Final[bool] = True

"""
HTTP request service with retry, timeout and delay support.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import requests
from requests import Response, Session
from requests.exceptions import RequestException, Timeout

from config import (
    DEFAULT_HEADERS,
    REQUEST_MAX_RETRIES,
    REQUEST_RETRY_SLEEP_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
)
from services.delay_service import apply_delay


class RequestService:
    """
    Service responsible for making HTTP requests with retry and delay logic.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """
        Initialize the request service.

        Args:
            logger: Logger instance used for warnings and errors.
        """

        self.session: Session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.logger = logger

    def get(self, url: str) -> Optional[Response]:
        """
        Perform an HTTP GET request with retry logic.

        Args:
            url: Target URL.

        Returns:
            Optional[Response]: Successful response object, otherwise None.
        """

        for attempt in range(1, REQUEST_MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )

                if response.status_code == 200:
                    apply_delay()
                    return response

                self.logger.warning(
                    f"Attempt {attempt} failed with status "
                    f"{response.status_code} | URL: {url}"
                )
                time.sleep(REQUEST_RETRY_SLEEP_SECONDS)

            except Timeout:
                self.logger.warning(
                    f"Attempt {attempt} timeout | URL: {url}"
                )
                time.sleep(REQUEST_RETRY_SLEEP_SECONDS)

            except RequestException as exc:
                self.logger.error(
                    f"Attempt {attempt} exception: {exc} | URL: {url}"
                )
                time.sleep(REQUEST_RETRY_SLEEP_SECONDS)

        self.logger.error(
            f"All retries failed | URL: {url}"
        )
        return None

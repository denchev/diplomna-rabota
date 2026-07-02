"""
Delay service for controlling request pacing.
"""

from __future__ import annotations

import random
import time

from config import (
    DEBUG_REQUEST_DELAY_MAX_SECONDS,
    DEBUG_REQUEST_DELAY_MIN_SECONDS,
    REQUEST_DELAY_MAX_SECONDS,
    REQUEST_DELAY_MIN_SECONDS,
)


def apply_delay(debug: bool = False) -> None:
    """
    Apply a randomized delay between requests.

    Args:
        debug: If True, use shorter debug delay range.
    """

    if debug:
        delay = random.uniform(
            DEBUG_REQUEST_DELAY_MIN_SECONDS,
            DEBUG_REQUEST_DELAY_MAX_SECONDS,
        )
    else:
        delay = random.uniform(
            REQUEST_DELAY_MIN_SECONDS,
            REQUEST_DELAY_MAX_SECONDS,
        )

    time.sleep(delay)

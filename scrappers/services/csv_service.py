"""
CSV service for writing scraped records.

Responsible for:
- creating per-run output files
- writing headers
- appending records
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Optional, Type

from config import OUTPUT_DIR, OUTPUT_FILE_EXTENSION, OUTPUT_FILE_TEMPLATE
from models.comment_record import CommentRecord, OUTPUT_FIELD_NAMES


def ensure_output_directory_exists() -> None:
    """
    Ensure that the output directory exists.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_output_file_path(source_name: str, session_timestamp: str) -> Path:
    """
    Build output file path for a source and session.

    Args:
        source_name: Normalized source name (e.g. dnes_bg).
        session_timestamp: Session timestamp.

    Returns:
        Path: Path to output file.
    """

    filename = OUTPUT_FILE_TEMPLATE.format(
        source_name=source_name,
        session_timestamp=session_timestamp,
        extension=OUTPUT_FILE_EXTENSION,
    )

    return OUTPUT_DIR / filename


class CsvWriter:
    """
    CSV writer for comment records.
    """

    def __init__(self, source_name: str, session_timestamp: str) -> None:
        """
        Initialize writer.

        Args:
            source_name: Source identifier.
            session_timestamp: Session timestamp.
        """

        ensure_output_directory_exists()

        self.source_name = source_name
        self.session_timestamp = session_timestamp
        self.file_path = build_output_file_path(
            source_name=source_name,
            session_timestamp=session_timestamp,
        )

        self._file = open(self.file_path, mode="w", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(
            self._file,
            fieldnames=OUTPUT_FIELD_NAMES,
        )

        self._writer.writeheader()

    def write_record(self, record: CommentRecord) -> None:
        """
        Write a single record.

        Args:
            record: CommentRecord instance.
        """

        record.validate()

        row = record.to_output_dict()
        self._writer.writerow(row)

    def write_many(self, records: Iterable[CommentRecord]) -> None:
        """
        Write multiple records.

        Args:
            records: Iterable of CommentRecord.
        """

        for record in records:
            self.write_record(record)

    def close(self) -> None:
        """
        Close file handle.
        """

        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "CsvWriter":
        """
        Enter the context manager.

        Returns:
            CsvWriter: Self.
        """

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Exit the context manager and close the file.

        Args:
            exc_type: Exception type, if any.
            exc_val: Exception value, if any.
            exc_tb: Exception traceback, if any.
        """

        self.close()

# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""Watch / scheduling mode: run scrape jobs on a recurring interval."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from web_scraper.config import parse_interval

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def watch(
    job: Callable[[], list[dict[str, Any]]],
    interval: str,
    *,
    notify_changes: bool = False,
    on_new_records: Callable[[list[dict[str, Any]]], None] | None = None,
) -> None:
    """Run *job* repeatedly on the given *interval*, indefinitely.

    Parameters
    ----------
    job:
        A zero-argument callable that returns a list of scraped records.
    interval:
        Human-readable interval string (``"1h"``, ``"30m"``, ``"60s"``).
    notify_changes:
        When ``True``, compare results between runs and report new/removed records
        via *on_new_records* or the default logger.
    on_new_records:
        Optional callback invoked with the list of new records when
        *notify_changes* is ``True`` and new records are found.
    """
    delay = parse_interval(interval)
    logger.info("Watch mode started. Interval: %s (%.0fs)", interval, delay)

    previous: list[dict[str, Any]] | None = None

    while True:
        try:
            records = job()
            logger.info("Fetched %d records.", len(records))

            if notify_changes and previous is not None:
                new_records = _diff_records(previous, records)
                if new_records:
                    msg = f"⚡ {len(new_records)} new record(s) detected."
                    logger.info(msg)
                    if on_new_records:
                        on_new_records(new_records)
                    else:
                        for rec in new_records:
                            logger.info("  NEW: %s", rec)

            previous = records
        except KeyboardInterrupt:
            logger.info("Watch mode stopped by user.")
            break
        except Exception as exc:
            logger.error("Error during scrape job: %s", exc)

        logger.info("Next run in %.0f seconds …", delay)
        try:
            time.sleep(delay)
        except KeyboardInterrupt:
            logger.info("Watch mode stopped by user.")
            break


def _diff_records(
    old: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return records in *new* that are not in *old* (based on full dict equality)."""
    old_set = {_hashable(r) for r in old}
    return [r for r in new if _hashable(r) not in old_set]


def _hashable(record: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(sorted(record.items()))

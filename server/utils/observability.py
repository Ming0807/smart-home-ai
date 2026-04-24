from __future__ import annotations

import logging
from time import perf_counter
from typing import Iterator

from server.config import Settings


def configure_logging(settings: Settings) -> None:
    level = logging.DEBUG if settings.debug_logs else logging.INFO
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    root_logger.setLevel(level)


def should_log_timings(settings: Settings) -> bool:
    return settings.debug_logs or settings.demo_mode


def log_timing(
    logger: logging.Logger,
    settings: Settings,
    operation: str,
    duration_ms: float,
    **fields: object,
) -> None:
    if not should_log_timings(settings):
        return

    field_text = " ".join(
        f"{key}={value}"
        for key, value in fields.items()
        if value is not None
    )
    suffix = f" {field_text}" if field_text else ""
    logger.info("%s latency_ms=%.1f%s", operation, duration_ms, suffix)


class Timer:
    def __init__(self) -> None:
        self._started_at = perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (perf_counter() - self._started_at) * 1000


def start_timer() -> Timer:
    return Timer()

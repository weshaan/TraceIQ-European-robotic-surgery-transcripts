"""Pipeline step timing logs (terminal / Streamlit server process)."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

LOGGER_NAME = "hasamex.pipeline"


def setup_pipeline_logging() -> None:
    root = logging.getLogger(LOGGER_NAME)
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.propagate = False


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


@contextmanager
def log_step(step: str, *, detail: str | None = None) -> Iterator[None]:
    label = f"{step} ({detail})" if detail else step
    log = get_logger()
    log.info("START %s", label)
    t0 = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed = time.perf_counter() - t0
        log.exception("FAIL %s after %.2fs", label, elapsed)
        raise
    else:
        elapsed = time.perf_counter() - t0
        log.info("DONE %s in %.2fs", label, elapsed)

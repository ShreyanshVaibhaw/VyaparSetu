"""Rich logging utilities with file output and operation timing helpers."""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Generator, TypeVar

from rich.logging import RichHandler


LOG_FILE = Path(__file__).resolve().parents[2] / "outputs" / "logs" / "vyaparsetu.log"
AUDIT_LOG_FILE = Path(
    os.getenv(
        "VYAPARSETU_AUDIT_LOG",
        str(Path(__file__).resolve().parents[2] / "outputs" / "logs" / "audit.log"),
    )
)
F = TypeVar("F", bound=Callable[..., Any])


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for rich console + persistent file logs."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    rich_handler = RichHandler(show_time=True, show_path=False, markup=False, rich_tracebacks=True)
    rich_handler.setLevel(logging.INFO)
    rich_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))

    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)
    return logger


def get_audit_logger() -> logging.Logger:
    """Return dedicated audit logger that writes JSON lines to audit log."""
    logger = logging.getLogger("vyaparsetu.audit")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)
    return logger


def audit_event(event: str, status: str = "ok", **fields: Any) -> None:
    """Append structured audit event as JSON.

    Fields are normalized to JSON-safe values.
    """
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "status": status,
    }
    for key, value in fields.items():
        payload[key] = _json_safe(value)
    get_audit_logger().info(json.dumps(payload, ensure_ascii=False))


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return str(value)


@contextmanager
def log_timing(logger: logging.Logger, operation: str) -> Generator[None, None, None]:
    """Context manager that logs elapsed time for an operation."""
    start = time.perf_counter()
    logger.info("Starting: %s", operation)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("Completed: %s in %.3fs", operation, elapsed)


def timed(logger: logging.Logger, operation_name: str | None = None) -> Callable[[F], F]:
    """Decorator to log execution time for a function."""

    def decorator(func: F) -> F:
        op_name = operation_name or func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with log_timing(logger, op_name):
                return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator

"""Security logging regression tests."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import src.common.logger as app_logger


def _test_audit_file() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "outputs" / "logs" / "audit_test.log"


def _reset_audit_logger() -> None:
    logger = logging.getLogger("vyaparsetu.audit")
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def test_audit_event_writes_json_line() -> None:
    audit_path = _test_audit_file()
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.unlink(missing_ok=True)
        app_logger.AUDIT_LOG_FILE = audit_path
        _reset_audit_logger()
        app_logger.audit_event("unit_test_event", status="success", user="demo", count=1)

        assert app_logger.AUDIT_LOG_FILE.exists()
        line = app_logger.AUDIT_LOG_FILE.read_text(encoding="utf-8").strip().splitlines()[-1]
        payload = json.loads(line)
        assert payload["event"] == "unit_test_event"
        assert payload["status"] == "success"
        assert payload["user"] == "demo"
        assert payload["count"] == 1
        assert "ts" in payload
    finally:
        _reset_audit_logger()
        audit_path.unlink(missing_ok=True)

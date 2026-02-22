"""Submission pack regression tests."""

from __future__ import annotations

from pathlib import Path

from src.common.submission_pack import generate_submission_pack


def test_generate_submission_pack_outputs_bundle() -> None:
    result = generate_submission_pack()
    assert result["status"] == "ok"

    zip_path = Path(result["zip_path"])
    assert zip_path.exists()
    assert zip_path.stat().st_size > 0

    score = result.get("score", {})
    assert "overall_score" in score
    assert "readiness_band" in score

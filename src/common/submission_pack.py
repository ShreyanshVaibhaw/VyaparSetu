"""Submission readiness pack builder for competition/demo handoff."""

from __future__ import annotations

import json
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import OLLAMA_MODEL, PROJECT_NAME, PROJECT_SANSKRIT, TAGLINE, TEAM_WOMEN_TARGET
from src.common.logger import audit_event


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _output_dir() -> Path:
    return _project_root() / "outputs" / "submission"


def _model_evaluation_path() -> Path:
    return _project_root() / "outputs" / "model_evaluation_report.json"


def _safe_import_reference_validation() -> dict[str, bool]:
    try:
        from scripts.validate_reference_data import validate

        return validate()
    except Exception:
        return {
            "ondc_categories_present": False,
            "hsn_mapping_present": False,
            "hsn_has_required_fields": False,
            "nic_divisions_present": False,
            "nic_details_present": False,
            "snp_profiles_present": False,
            "snp_has_realistic_fields": False,
            "geo_data_with_latlon": False,
        }


def _safe_import_demo_summary() -> dict[str, Any]:
    try:
        from scripts.demo_flow import run_demo

        payload = run_demo(demo_mode=True, verbose=False)
        if isinstance(payload, dict):
            return payload
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "error", "error": "Unknown demo failure"}


def _security_snapshot() -> dict[str, Any]:
    import os

    has_admin_hash = bool(os.getenv("VYAPARSETU_ADMIN_PASSWORD_HASH", "").strip())
    has_plain_password = bool(os.getenv("VYAPARSETU_ADMIN_PASSWORD", "").strip())
    lockout_seconds = os.getenv("VYAPARSETU_ADMIN_LOCKOUT_SECONDS", "300")
    max_attempts = os.getenv("VYAPARSETU_ADMIN_MAX_FAILED_ATTEMPTS", "5")
    cooldown_seconds = os.getenv("VYAPARSETU_ACTION_COOLDOWN_SECONDS", "1.5")
    return {
        "admin_hash_configured": has_admin_hash,
        "admin_plain_password_present": has_plain_password,
        "admin_lockout_seconds": lockout_seconds,
        "admin_max_failed_attempts": max_attempts,
        "action_cooldown_seconds": cooldown_seconds,
        "audit_log_path": os.getenv("VYAPARSETU_AUDIT_LOG", "outputs/logs/audit.log"),
    }


def _runtime_snapshot() -> dict[str, Any]:
    return {
        "project_name": PROJECT_NAME,
        "project_sanskrit": PROJECT_SANSKRIT,
        "tagline": TAGLINE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "llm_model": OLLAMA_MODEL,
        "team_women_target": TEAM_WOMEN_TARGET,
    }


def _load_model_evaluation() -> dict[str, Any] | None:
    path = _model_evaluation_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


def _score_readiness(
    reference_checks: dict[str, bool],
    demo_summary: dict[str, Any],
    security: dict[str, Any],
    model_evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ref_score = int(round(100 * (sum(1 for ok in reference_checks.values() if ok) / max(len(reference_checks), 1))))
    demo_ok = str(demo_summary.get("status", "")).lower() == "ok"
    demo_score = 100 if demo_ok else 20
    security_score = 100 if bool(security.get("admin_hash_configured")) else 70

    weighted = int(round(ref_score * 0.45 + demo_score * 0.35 + security_score * 0.20))
    bonus_points = 0
    if model_evaluation:
        product = model_evaluation.get("product_classifier", {})
        try:
            product_accuracy = float(product.get("accuracy", 0.0))
        except (TypeError, ValueError):
            product_accuracy = 0.0
        if product_accuracy >= 0.70:
            bonus_points = 5

    weighted = min(100, weighted + bonus_points)
    if weighted >= 90:
        band = "Submission-Ready"
    elif weighted >= 75:
        band = "Strong-Prototype"
    else:
        band = "Needs-Polish"

    return {
        "reference_data_score": ref_score,
        "demo_score": demo_score,
        "security_score": security_score,
        "model_evaluation_bonus": bonus_points,
        "overall_score": weighted,
        "readiness_band": band,
    }


def _build_markdown(
    runtime: dict[str, Any],
    checks: dict[str, bool],
    demo: dict[str, Any],
    security: dict[str, Any],
    score: dict[str, Any],
    model_evaluation: dict[str, Any] | None = None,
) -> str:
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    check_lines = "\n".join(
        f"- {'PASS' if ok else 'FAIL'}: `{name}`" for name, ok in checks.items()
    )
    scene4 = demo.get("scene_4", {}) if isinstance(demo, dict) else {}
    women_pct = scene4.get("women_percentage", "N/A")
    total_mses = scene4.get("total_mses", "N/A")
    total_products = scene4.get("total_products", "N/A")

    model_perf_section = "## Model Performance\nRun `scripts/evaluate_models.py` to generate model metrics\n"
    if model_evaluation:
        product = model_evaluation.get("product_classifier", {})
        business = model_evaluation.get("business_classifier", {})
        snp = model_evaluation.get("snp_scorer", {})
        product_acc_pct = _to_float(product.get("accuracy", 0.0)) * 100.0
        model_perf_section = (
            "## Model Performance\n"
            f"- Product Classifier Accuracy: {product_acc_pct:.2f}%\n"
            f"- Product Classifier Macro-F1: {_to_float(product.get('macro_f1', 0.0)):.4f}\n"
            f"- Product Classifier Weighted-F1: {_to_float(product.get('weighted_f1', 0.0)):.4f}\n"
            f"- Business Classifier Accuracy: {_to_float(business.get('accuracy', 0.0)) * 100.0:.2f}%\n"
            f"- SNP Matcher Top-3 Accuracy: {_to_float(snp.get('top3_accuracy', 0.0)) * 100.0:.2f}%\n"
            f"- SNP Matcher MRR: {_to_float(snp.get('mrr', 0.0)):.4f}\n"
        )

    return (
        f"# {runtime['project_name']} Competition Submission Pack\n\n"
        f"Generated: `{runtime['generated_at_utc']}`\n\n"
        "## Readiness Score\n"
        f"- Overall: **{score['overall_score']}/100** (`{score['readiness_band']}`)\n"
        f"- Reference Data: `{score['reference_data_score']}`\n"
        f"- Demo Reliability: `{score['demo_score']}`\n"
        f"- Security Posture: `{score['security_score']}`\n\n"
        f"{model_perf_section}\n"
        "## Core Evidence\n"
        f"- LLM Model: `{runtime['llm_model']}`\n"
        f"- Demo Status: `{demo.get('status', 'unknown')}`\n"
        f"- Synthetic Coverage: `{total_mses}` MSEs, `{total_products}` products\n"
        f"- Women Inclusion (demo): `{women_pct}%` (target `{runtime['team_women_target']*100:.0f}%`)\n\n"
        "## Reference Data Validation\n"
        f"{check_lines}\n\n"
        "## Security Snapshot\n"
        f"- Admin hash configured: `{security.get('admin_hash_configured')}`\n"
        f"- Admin lockout (seconds): `{security.get('admin_lockout_seconds')}`\n"
        f"- Max failed attempts: `{security.get('admin_max_failed_attempts')}`\n"
        f"- UI action cooldown (seconds): `{security.get('action_cooldown_seconds')}`\n"
        f"- Audit log path: `{security.get('audit_log_path')}`\n"
    )


def generate_submission_pack() -> dict[str, Any]:
    """Generate a zipped evidence pack for competition submission."""
    out_dir = _output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    runtime = _runtime_snapshot()
    reference_checks = _safe_import_reference_validation()
    demo_summary = _safe_import_demo_summary()
    security = _security_snapshot()
    model_evaluation = _load_model_evaluation()
    score = _score_readiness(reference_checks, demo_summary, security, model_evaluation)

    report_md = _build_markdown(runtime, reference_checks, demo_summary, security, score, model_evaluation)

    overview_path = out_dir / "submission_overview.md"
    runtime_path = out_dir / "runtime_snapshot.json"
    checks_path = out_dir / "reference_validation.json"
    demo_path = out_dir / "demo_summary.json"
    security_path = out_dir / "security_snapshot.json"
    score_path = out_dir / "readiness_score.json"
    model_eval_path = _model_evaluation_path()
    zip_path = out_dir / "vyaparsetu_submission_pack.zip"

    overview_path.write_text(report_md, encoding="utf-8")
    runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False), encoding="utf-8")
    checks_path.write_text(json.dumps(reference_checks, indent=2, ensure_ascii=False), encoding="utf-8")
    demo_path.write_text(json.dumps(demo_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    security_path.write_text(json.dumps(security, indent=2, ensure_ascii=False), encoding="utf-8")
    score_path.write_text(json.dumps(score, indent=2, ensure_ascii=False), encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle_items = [overview_path, runtime_path, checks_path, demo_path, security_path, score_path]
        if model_eval_path.exists():
            bundle_items.append(model_eval_path)
        for item in bundle_items:
            bundle.write(item, arcname=item.name)

    audit_event(
        "submission_pack_generate",
        status="success",
        overall_score=score.get("overall_score"),
        readiness_band=score.get("readiness_band"),
        output_zip=str(zip_path),
    )

    return {
        "status": "ok",
        "output_dir": str(out_dir),
        "zip_path": str(zip_path),
        "files": [
            str(overview_path),
            str(runtime_path),
            str(checks_path),
            str(demo_path),
            str(security_path),
            str(score_path),
        ] + ([str(model_eval_path)] if model_eval_path.exists() else []),
        "score": score,
    }

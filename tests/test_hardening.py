"""Hardening regression tests for config/runtime resilience."""

from __future__ import annotations

import importlib
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.common.models import MSEProfile
from src.udyambodh.business_classifier import BusinessClassifier
from src.udyambodh.gst_validator import GSTValidator
from src.vastrasuchi.product_classifier import ProductClassifier
from src.vriddhidisha.catalog_performance import CatalogPerformance
from src.vriddhidisha.funnel_analytics import FunnelAnalytics
from src.vriddhidisha.women_mse_tracker import WomenMSETracker


class _FakeLLM:
    def generate_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        return {}


def _sample_profile() -> MSEProfile:
    return MSEProfile(
        udyam_number="UDYAM-RJ-01-0012345",
        enterprise_name="Sample Enterprise",
        owner_name="Owner",
        owner_gender="Male",
        enterprise_type="Micro",
        major_activity="Manufacturing",
        nic_2digit="10",
        nic_5digit="10795",
        nic_description="Manufacture of papads and similar foods",
        state="Rajasthan",
        district="Jaipur",
        pincode="302001",
        address="Jaipur",
        mobile=None,
        email=None,
        date_of_incorporation=None,
        date_of_udyam=None,
        investment_plant=5.0,
        turnover=20.0,
        gstin=None,
        pan=None,
        social_category=None,
        is_women_owned=False,
        language_preference="hi",
        products_services=["Papad"],
    )


@pytest.fixture
def config_module():
    import config

    importlib.reload(config)
    yield config
    importlib.reload(config)


def test_config_reads_env_overrides(monkeypatch: pytest.MonkeyPatch, config_module: Any) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "ollama")
    monkeypatch.setenv("OLLAMA_PORT", "12345")
    monkeypatch.setenv("TEAM_WOMEN_TARGET", "0.55")

    cfg = importlib.reload(config_module)
    assert cfg.OLLAMA_HOST == "ollama"
    assert cfg.OLLAMA_PORT == 12345
    assert cfg.TEAM_WOMEN_TARGET == 0.55


def test_config_invalid_numeric_env_falls_back(monkeypatch: pytest.MonkeyPatch, config_module: Any) -> None:
    monkeypatch.setenv("OLLAMA_PORT", "not-a-number")
    cfg = importlib.reload(config_module)
    assert cfg.OLLAMA_PORT == 11434


def _workspace_temp_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    return Path(tempfile.mkdtemp(prefix="hardening_", dir=str(root)))


def test_business_classifier_missing_files_is_safe() -> None:
    tmp_path = _workspace_temp_dir()
    try:
        classifier = BusinessClassifier(
            llm_client=_FakeLLM(),
            nic_to_ondc_path=str(tmp_path / "missing_nic_to_ondc.json"),
            categories_path=str(tmp_path / "missing_categories.json"),
        )
        result = classifier.classify_hybrid(_sample_profile())
        assert result["primary_l1"] in {"General", "Food & Beverage"}
        assert "confidence" in result
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_product_classifier_missing_files_is_safe() -> None:
    tmp_path = _workspace_temp_dir()
    try:
        classifier = ProductClassifier(
            categories_path=str(tmp_path / "missing_categories.json"),
            hsn_mapping_path=str(tmp_path / "missing_hsn_mapping.json"),
            llm_client=_FakeLLM(),
        )
        result = classifier.classify(product_description="", business_nic="10")
        assert {"l1", "l2", "l3", "confidence"} <= result.keys()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_gst_validator_non_string_is_invalid() -> None:
    result = GSTValidator().validate_gstin(None)
    assert result["valid"] is False
    assert result["state_name"] == ""


def test_analytics_missing_data_files_do_not_crash() -> None:
    tmp_path = _workspace_temp_dir()
    try:
        missing_csv = str(tmp_path / "missing.csv")

        funnel = FunnelAnalytics(missing_csv)
        women = WomenMSETracker(missing_csv)
        catalog = CatalogPerformance()

        summary = funnel.get_funnel_summary()
        assert summary["counts"]["registered"] == 0
        assert women.get_women_percentage() == 0.0

        trend = funnel.get_monthly_trend("registered")
        assert trend is not None

        cat_fig = catalog.get_category_distribution(missing_csv)
        price_fig = catalog.get_pricing_analysis(missing_csv)
        assert cat_fig is not None
        assert price_fig is not None
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

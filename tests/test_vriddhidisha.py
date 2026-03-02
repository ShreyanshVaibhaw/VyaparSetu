"""Prompt 6 tests for VriddhiDisha analytics module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from src.common.models import ONDCCatalogItem
from src.vriddhidisha.catalog_performance import CatalogPerformance
from src.vriddhidisha.dashboard_data import DashboardDataPrep, build_dashboard_payload
from src.vriddhidisha.funnel_analytics import FunnelAnalytics
from src.vriddhidisha.geo_analytics import GeoAnalytics
from src.vriddhidisha.women_mse_tracker import WomenMSETracker, women_mse_progress


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def synthetic_paths() -> dict[str, Path]:
    """Ensure Prompt 6 synthetic data exists at expected scale."""
    base = _root() / "data" / "synthetic"
    paths = {
        "mse": base / "mse_profiles.csv",
        "products": base / "products.csv",
        "funnel": base / "onboarding_funnel.csv",
        "assignments": base / "snp_assignments.csv",
    }

    needs_generation = not all(path.exists() for path in paths.values())
    if not needs_generation:
        try:
            needs_generation = (
                len(pd.read_csv(paths["mse"])) < 5000
                or len(pd.read_csv(paths["products"])) < 2000
                or len(pd.read_csv(paths["funnel"])) < 60
            )
        except Exception:
            needs_generation = True

    if needs_generation:
        subprocess.run([sys.executable, str(_root() / "scripts" / "generate_synthetic_data.py")], check=True)

    return paths


def _sample_catalog_item() -> ONDCCatalogItem:
    return ONDCCatalogItem(
        item_id="ITEM-TEST-1",
        mse_udyam="UDYAM-RJ-01-1234567",
        product_name_en="Homemade Mango Pickle (500g)",
        product_name_regional="घर का बना आम का अचार (500 ग्राम)",
        short_description="Traditional mango pickle made in small batches.",
        long_description="This handmade mango pickle is prepared using regional spices and cold-pressed oil for authentic taste and long shelf life.",
        category_l1="Food & Beverage",
        category_l2="Packaged Foods",
        category_l3="Pickles & Chutneys",
        hsn_code="2001",
        price_mrp=220.0,
        price_selling=199.0,
        quantity_unit="gram",
        quantity_value=500.0,
        images=["https://example.com/pickle.jpg"],
        attributes={"ingredients": "mango, spices, oil", "spice_level": "medium", "shelf_life": "6 months"},
        tags={"handmade": "yes"},
        origin_country="India",
        returnable=False,
        cancellable=True,
        available_on_cod=True,
        time_to_ship="P2D",
        generated_by_ai=True,
        reviewed_by_mse=True,
        created_at=datetime.now(timezone.utc),
    )


def test_prompt6_synthetic_data_generation(synthetic_paths: dict[str, Path]) -> None:
    """Synthetic datasets should be generated with expected base volumes."""
    mse_rows = len(pd.read_csv(synthetic_paths["mse"]))
    product_rows = len(pd.read_csv(synthetic_paths["products"]))
    funnel_rows = len(pd.read_csv(synthetic_paths["funnel"]))
    assignment_rows = len(pd.read_csv(synthetic_paths["assignments"]))

    assert mse_rows == 5000
    assert product_rows == 2000
    assert funnel_rows == 216
    assert assignment_rows > 0


def test_funnel_analytics_outputs_are_sensible(synthetic_paths: dict[str, Path]) -> None:
    """Funnel analytics should return valid metrics and non-empty figures."""
    analytics = FunnelAnalytics(str(synthetic_paths["funnel"]))

    summary = analytics.get_funnel_summary()
    counts = summary["counts"]
    rates = summary["conversion_rates"]

    assert counts["registered"] > 0
    assert counts["first_order"] > 0
    assert counts["registered"] >= counts["catalog_created"] >= counts["snp_matched"] >= counts["live"] >= counts["first_order"]
    assert all(0 <= float(v) <= 1 for v in rates.values())

    funnel_chart = analytics.get_funnel_chart()
    assert len(funnel_chart.data) == 1
    assert funnel_chart.data[0].type == "funnel"

    trend = analytics.get_monthly_trend("registered")
    assert len(trend.data) == 1
    assert len(trend.data[0].x) >= 6

    bottleneck = analytics.get_bottleneck_analysis()
    assert {"worst_conversion_stage", "rate", "suggested_action"} <= bottleneck.keys()
    assert 0 <= float(bottleneck["rate"]) <= 1


def test_geo_analytics_produces_non_empty_maps_and_charts(synthetic_paths: dict[str, Path]) -> None:
    """Geo analytics outputs should be non-empty and usable for dashboard rendering."""
    geo = GeoAnalytics(
        mse_data_path=str(synthetic_paths["mse"]),
        state_districts_path=str(_root() / "data" / "mse_data" / "state_districts.json"),
    )

    state_map = geo.get_state_heatmap()
    district_map = geo.get_district_bubble_map("Rajasthan")
    assert len(state_map._children) > 1
    assert len(district_map._children) > 1

    tier_fig = geo.get_tier_distribution()
    comparison_fig = geo.get_state_comparison()
    assert len(tier_fig.data) >= 1
    assert len(comparison_fig.data) >= 1


def test_women_tracker_outputs_metrics_visuals_and_recommendations(synthetic_paths: dict[str, Path]) -> None:
    """Women MSE tracker should surface share, funnel gap, visuals, and recommendations."""
    tracker = WomenMSETracker(str(synthetic_paths["mse"]))

    pct_all = tracker.get_women_percentage()
    pct_rj = tracker.get_women_percentage("Rajasthan")
    assert 0 <= pct_all <= 1
    assert 0 <= pct_rj <= 1

    women_funnel = tracker.get_women_funnel()
    assert {"women_counts", "other_counts", "women_conversion", "other_conversion", "conversion_gap"} <= women_funnel.keys()
    assert women_funnel["women_counts"]["registered"] > 0

    gauge = tracker.get_women_target_gauge()
    by_category = tracker.get_women_by_category()
    recommendations = tracker.get_recommendations()
    assert len(gauge.data) == 1
    assert len(by_category.data) >= 1
    assert len(recommendations) >= 1


def test_catalog_performance_outputs_distribution_pricing_and_quality(synthetic_paths: dict[str, Path]) -> None:
    """Catalog analytics should provide treemap, pricing boxplot, and a scored quality report."""
    performance = CatalogPerformance()

    treemap = performance.get_category_distribution(str(synthetic_paths["products"]))
    pricing = performance.get_pricing_analysis(str(synthetic_paths["products"]))
    quality = performance.get_catalog_quality_score([_sample_catalog_item()])

    assert len(treemap.data) >= 1
    assert len(pricing.data) >= 1
    assert 0 <= float(quality["score"]) <= 100
    assert {"score", "issues", "suggestions"} <= quality.keys()


def test_dashboard_data_prep_returns_overview_and_admin_payload(synthetic_paths: dict[str, Path]) -> None:
    """DashboardDataPrep should aggregate all module outputs for admin consumption."""
    funnel = FunnelAnalytics(str(synthetic_paths["funnel"]))
    geo = GeoAnalytics(
        mse_data_path=str(synthetic_paths["mse"]),
        state_districts_path=str(_root() / "data" / "mse_data" / "state_districts.json"),
    )
    women = WomenMSETracker(str(synthetic_paths["mse"]))
    catalog = CatalogPerformance()
    prep = DashboardDataPrep(funnel=funnel, geo=geo, women=women, catalog=catalog)

    overview = prep.get_overview_metrics()
    assert {
        "total_registered",
        "total_live",
        "women_percentage",
        "top_category",
        "best_state",
        "worst_bottleneck",
    } <= overview.keys()
    assert overview["total_registered"] > 0
    assert overview["total_live"] > 0
    assert 0 <= float(overview["women_percentage"]) <= 100

    report = prep.get_admin_report_data()
    assert {"overview", "funnel", "geography", "women_mse", "catalog"} <= report.keys()
    assert report["catalog"]["category_distribution"] is not None
    assert report["catalog"]["pricing_analysis"] is not None
    assert len(report["funnel"]["chart"].data) >= 1
    assert len(report["geography"]["tier_distribution"].data) >= 1


def test_backward_compatibility_helpers() -> None:
    """Legacy helper utilities should remain callable."""
    women_result = women_mse_progress([])
    payload = build_dashboard_payload({"a": 1}, {"b": 2}, {"c": 3})

    assert set(women_result.keys()) == {"ratio", "target", "met"}
    assert payload == {"funnel": {"a": 1}, "geo": {"b": 2}, "catalog": {"c": 3}}

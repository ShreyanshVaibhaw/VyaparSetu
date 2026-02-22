"""Dashboard-level data preparation for VriddhiDisha."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class DashboardDataPrep:
    """Compose analytics outputs into dashboard/admin-ready payloads."""

    def __init__(self, funnel: Any, geo: Any, women: Any, catalog: Any) -> None:
        self.funnel = funnel
        self.geo = geo
        self.women = women
        self.catalog = catalog

    def get_overview_metrics(self) -> dict[str, Any]:
        """Return top-line metrics used in dashboard header cards."""
        funnel_summary = self.funnel.get_funnel_summary()
        counts = funnel_summary.get("counts", {})

        women_percentage = round(float(self.women.get_women_percentage()) * 100, 2)
        top_category = self._top_category()
        best_state = self._best_state()
        bottleneck = self.funnel.get_bottleneck_analysis().get("worst_conversion_stage", "N/A")

        return {
            "total_registered": int(counts.get("registered", 0)),
            "total_live": int(counts.get("live", 0)),
            "women_percentage": women_percentage,
            "top_category": top_category,
            "best_state": best_state,
            "worst_bottleneck": bottleneck,
        }

    def get_admin_report_data(self) -> dict[str, Any]:
        """Return a complete payload consumed by admin dashboards/PDF reports."""
        products_path = self._products_path()
        has_products = products_path is not None

        category_distribution = self.catalog.get_category_distribution(str(products_path)) if has_products else None
        pricing_analysis = self.catalog.get_pricing_analysis(str(products_path)) if has_products else None

        return {
            "overview": self.get_overview_metrics(),
            "funnel": {
                "summary": self.funnel.get_funnel_summary(),
                "chart": self.funnel.get_funnel_chart(),
                "monthly_trends": {stage: self.funnel.get_monthly_trend(stage) for stage in self.funnel.STAGES},
                "bottleneck": self.funnel.get_bottleneck_analysis(),
            },
            "geography": {
                "state_heatmap": self.geo.get_state_heatmap(),
                "district_bubble_map": self.geo.get_district_bubble_map(),
                "tier_distribution": self.geo.get_tier_distribution(),
                "state_comparison": self.geo.get_state_comparison(),
            },
            "women_mse": {
                "percentage": self.women.get_women_percentage(),
                "funnel": self.women.get_women_funnel(),
                "target_gauge": self.women.get_women_target_gauge(),
                "by_category": self.women.get_women_by_category(),
                "recommendations": self.women.get_recommendations(),
            },
            "catalog": {
                "category_distribution": category_distribution,
                "pricing_analysis": pricing_analysis,
                "quality_score": None,
            },
        }

    def _top_category(self) -> str:
        data = getattr(self.women, "data", None)
        if data is None or data.empty or "category_l1" not in data.columns:
            return "N/A"
        top = data["category_l1"].value_counts()
        if top.empty:
            return "N/A"
        return str(top.index[0])

    def _best_state(self) -> str:
        data = getattr(self.funnel, "data", None)
        if data is None or data.empty or "state" not in data.columns:
            return "N/A"
        grouped = (
            data.groupby("state", as_index=False)
            .agg(registered=("registered", "sum"), live=("live", "sum"))
            .assign(live_rate=lambda x: x["live"] / x["registered"].clip(lower=1))
            .sort_values("live_rate", ascending=False)
        )
        if grouped.empty:
            return "N/A"
        return str(grouped.iloc[0]["state"])

    def _products_path(self) -> Path | None:
        candidate = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "products.csv"
        if candidate.exists():
            return candidate

        data = getattr(self.geo, "mse_data", None)
        if isinstance(data, pd.DataFrame) and "products_path" in data.attrs:
            attr_path = Path(str(data.attrs["products_path"]))
            if attr_path.exists():
                return attr_path
        return None


def build_dashboard_payload(funnel: dict[str, Any], geo: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible helper for legacy callers."""
    return {"funnel": funnel, "geo": geo, "catalog": catalog}

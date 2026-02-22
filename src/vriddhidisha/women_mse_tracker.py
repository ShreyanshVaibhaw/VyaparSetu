"""Women-owned MSE onboarding analytics."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class WomenMSETracker:
    """Track women-owned MSE participation and conversion metrics."""

    def __init__(self, mse_data_path: str) -> None:
        try:
            self.data = pd.read_csv(mse_data_path)
        except Exception:
            self.data = pd.DataFrame(columns=["state", "is_women_owned", "registered", "catalog_created", "snp_matched", "live", "first_order", "category_l1"])
        if "is_women_owned" in self.data.columns:
            self.data["is_women_owned"] = self.data["is_women_owned"].astype(int)

    def get_women_percentage(self, state: str | None = None) -> float:
        """Return women-owned MSE share, optionally state-filtered."""
        df = self._filtered(state)
        if df.empty:
            return 0.0
        return round(float(df["is_women_owned"].mean()), 4)

    def get_women_funnel(self) -> dict[str, Any]:
        """Compare funnel drop-offs between women-owned and other MSEs."""
        women = self.data[self.data["is_women_owned"] == 1]
        others = self.data[self.data["is_women_owned"] == 0]

        def _summary(df: pd.DataFrame) -> dict[str, int]:
            return {
                "registered": int(df["registered"].sum()),
                "catalog_created": int(df["catalog_created"].sum()),
                "snp_matched": int(df["snp_matched"].sum()),
                "live": int(df["live"].sum()),
                "first_order": int(df["first_order"].sum()),
            }

        women_counts = _summary(women)
        other_counts = _summary(others)
        women_conv = self._conversion_rates(women_counts)
        other_conv = self._conversion_rates(other_counts)

        stage_gap = {
            key: round(other_conv.get(key, 0.0) - women_conv.get(key, 0.0), 4)
            for key in women_conv.keys()
        }
        return {
            "women_counts": women_counts,
            "other_counts": other_counts,
            "women_conversion": women_conv,
            "other_conversion": other_conv,
            "conversion_gap": stage_gap,
        }

    def get_women_target_gauge(self) -> go.Figure:
        """Gauge chart for women-owned percentage vs 50% target."""
        pct = self.get_women_percentage() * 100
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=pct,
                number={"suffix": "%"},
                delta={"reference": 50},
                title={"text": "Women-owned MSE Share (Target: 50%)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "steps": [
                        {"range": [0, 35], "color": "#f4a261"},
                        {"range": [35, 50], "color": "#e9c46a"},
                        {"range": [50, 100], "color": "#2a9d8f"},
                    ],
                    "threshold": {"line": {"color": "#e63946", "width": 4}, "value": 50},
                },
            )
        )
        return fig

    def get_women_by_category(self) -> go.Figure:
        """Category distribution among women-owned MSEs."""
        women = self.data[self.data["is_women_owned"] == 1]
        grouped = women.groupby("category_l1", as_index=False).size().sort_values("size", ascending=False)
        fig = px.bar(grouped, x="category_l1", y="size", title="Women-owned MSEs by Category")
        return fig

    def get_recommendations(self) -> list[str]:
        """Generate data-driven interventions for women onboarding performance."""
        funnel = self.get_women_funnel()
        gap = funnel["conversion_gap"]
        recommendations: list[str] = []

        if gap["reg_to_catalog"] > 0.05:
            recommendations.append(
                "Women-owned MSEs show lower catalog completion; add WhatsApp-assisted listing support and local language voice guidance."
            )
        if gap["catalog_to_snp"] > 0.05:
            recommendations.append(
                "Improve SNP handholding for women-owned businesses with guided SNP comparison and partner-led onboarding camps."
            )
        if gap["snp_to_live"] > 0.05:
            recommendations.append(
                "Women-owned MSEs drop between SNP match and go-live; prioritize logistics enablement and onboarding concierge support."
            )

        women = self.data[self.data["is_women_owned"] == 1]
        if not women.empty:
            by_category = (
                women.groupby(["category_l1"], as_index=False)
                .agg(registered=("registered", "sum"), catalog_created=("catalog_created", "sum"))
            )
            by_category["catalog_rate"] = by_category["catalog_created"] / by_category["registered"].clip(lower=1)
            weakest = by_category.sort_values("catalog_rate").iloc[0]
            recommendations.append(
                f"Women MSEs in {weakest['category_l1']} have weaker catalog completion; deploy category-specific templates and assisted onboarding sessions."
            )

        if not recommendations:
            recommendations.append("Women MSE onboarding is on track; continue targeted language-first support.")
        return recommendations

    def _filtered(self, state: str | None) -> pd.DataFrame:
        if not state:
            return self.data
        return self.data[self.data["state"].astype(str).str.lower() == state.lower()]

    def _conversion_rates(self, counts: dict[str, int]) -> dict[str, float]:
        def safe(a: int, b: int) -> float:
            return round(a / b, 4) if b else 0.0

        return {
            "reg_to_catalog": safe(counts["catalog_created"], counts["registered"]),
            "catalog_to_snp": safe(counts["snp_matched"], counts["catalog_created"]),
            "snp_to_live": safe(counts["live"], counts["snp_matched"]),
            "live_to_first_order": safe(counts["first_order"], counts["live"]),
        }


def women_mse_progress(rows: list[dict[str, Any]], target: float = 0.50) -> dict[str, float | bool]:
    """Backward-compatible in-memory women progress calculator."""
    total = len(rows)
    women = sum(1 for r in rows if str(r.get("owner_gender", "")).upper().startswith("F"))
    ratio = (women / total) if total else 0.0
    return {"ratio": round(ratio, 4), "target": target, "met": ratio >= target}

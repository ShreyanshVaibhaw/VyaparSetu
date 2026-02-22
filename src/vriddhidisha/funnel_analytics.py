"""Funnel analytics for onboarding conversion tracking."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


class FunnelAnalytics:
    """Analyze and visualize onboarding funnel performance."""

    STAGES = ["registered", "catalog_created", "snp_matched", "live", "first_order"]

    def __init__(self, onboarding_data_path: str) -> None:
        try:
            self.data = pd.read_csv(onboarding_data_path)
        except Exception:
            self.data = pd.DataFrame(columns=["month", "state", *self.STAGES])
        if "month" in self.data.columns:
            self.data["month"] = self.data["month"].astype(str)

    def get_funnel_summary(self, state: str | None = None, month: str | None = None) -> dict[str, Any]:
        """Return funnel counts and conversion rates with optional filters."""
        df = self._filtered(state=state, month=month)
        totals = {stage: int(df[stage].sum()) if stage in df.columns else 0 for stage in self.STAGES}
        conversions = {
            "reg_to_catalog": self._safe_rate(totals["catalog_created"], totals["registered"]),
            "catalog_to_snp": self._safe_rate(totals["snp_matched"], totals["catalog_created"]),
            "snp_to_live": self._safe_rate(totals["live"], totals["snp_matched"]),
            "live_to_first_order": self._safe_rate(totals["first_order"], totals["live"]),
        }
        return {"counts": totals, "conversion_rates": conversions}

    def get_funnel_chart(self, state: str | None = None) -> go.Figure:
        """Create Plotly funnel chart with absolute counts."""
        summary = self.get_funnel_summary(state=state)
        counts = summary["counts"]
        fig = go.Figure(
            go.Funnel(
                y=["Registered", "Catalog Created", "SNP Matched", "Live", "First Order"],
                x=[
                    counts["registered"],
                    counts["catalog_created"],
                    counts["snp_matched"],
                    counts["live"],
                    counts["first_order"],
                ],
                textinfo="value+percent previous",
            )
        )
        fig.update_layout(title=f"Onboarding Funnel{' - ' + state if state else ''}")
        return fig

    def get_monthly_trend(self, stage: str) -> go.Figure:
        """Create line chart for monthly trend of one funnel stage."""
        if stage not in self.STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        if "month" not in self.data.columns:
            fig = go.Figure()
            fig.update_layout(title=f"Monthly Trend - {stage} (no data)", xaxis_title="Month", yaxis_title="Count")
            return fig

        trend = self.data.groupby("month", as_index=False)[stage].sum().sort_values("month")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend["month"], y=trend[stage], mode="lines+markers", name=stage))
        fig.update_layout(title=f"Monthly Trend - {stage}", xaxis_title="Month", yaxis_title="Count")
        return fig

    def get_bottleneck_analysis(self) -> dict[str, Any]:
        """Identify stage with highest drop-off and suggest remediation."""
        summary = self.get_funnel_summary()
        conv = summary["conversion_rates"]
        stage_map = {
            "reg_to_catalog": "Registration -> Catalog",
            "catalog_to_snp": "Catalog -> SNP Match",
            "snp_to_live": "SNP Match -> Live",
            "live_to_first_order": "Live -> First Order",
        }
        worst_key = min(conv, key=conv.get)
        suggestions = {
            "reg_to_catalog": "Increase guided catalog assistance via voice and WhatsApp onboarding.",
            "catalog_to_snp": "Improve SNP recommendation explainability and simplify selection UX.",
            "snp_to_live": "Strengthen logistics readiness and faster SNP activation hand-holding.",
            "live_to_first_order": "Launch first-order incentives and onboarding campaigns.",
        }
        return {
            "worst_conversion_stage": stage_map[worst_key],
            "rate": round(conv[worst_key], 4),
            "suggested_action": suggestions[worst_key],
        }

    def _filtered(self, state: str | None = None, month: str | None = None) -> pd.DataFrame:
        df = self.data.copy()
        if state is not None and "state" in df.columns:
            df = df[df["state"].astype(str).str.lower() == state.lower()]
        if month is not None and "month" in df.columns:
            df = df[df["month"].astype(str) == str(month)]
        return df

    def _safe_rate(self, num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round(num / den, 4)


def compute_funnel_metrics(records: list[dict[str, Any]]) -> dict[str, int]:
    """Backward-compatible record-based metric calculator."""
    return {
        "registered": len(records),
        "catalog_created": sum(1 for r in records if r.get("catalog_created")),
        "snp_matched": sum(1 for r in records if r.get("snp_matched")),
        "live": sum(1 for r in records if r.get("live")),
        "first_order": sum(1 for r in records if r.get("first_order")),
    }

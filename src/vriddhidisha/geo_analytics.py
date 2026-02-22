"""Geographic analytics and map visualizations."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class GeoAnalytics:
    """Analyze state/district-level onboarding distribution."""

    def __init__(self, mse_data_path: str, state_districts_path: str) -> None:
        try:
            self.mse_data = pd.read_csv(mse_data_path)
        except Exception:
            self.mse_data = pd.DataFrame()
        self.districts = self._load_districts(state_districts_path)

    def _load_districts(self, state_districts_path: str) -> pd.DataFrame:
        path = Path(state_districts_path)
        if not path.exists():
            return pd.DataFrame(columns=["state", "district", "lat", "lon", "tier"])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return pd.DataFrame(columns=["state", "district", "lat", "lon", "tier"])
        rows: list[dict[str, Any]] = []
        for state_row in payload.get("states", []):
            state = state_row.get("state")
            for district in state_row.get("districts", []):
                rows.append(
                    {
                        "state": state,
                        "district": district.get("district") or district.get("name"),
                        "lat": district.get("lat"),
                        "lon": district.get("lon"),
                        "tier": district.get("tier", 3),
                    }
                )
        return pd.DataFrame(rows)

    def get_state_heatmap(self) -> folium.Map:
        """State-level marker map with onboarding and conversion info."""
        m = folium.Map(location=[22.0, 79.0], zoom_start=5, tiles="cartodbpositron")
        if self.mse_data.empty:
            return m

        summary = (
            self.mse_data.groupby("state", as_index=False)
            .agg(
                total_registered=("registered", "sum"),
                total_live=("live", "sum"),
                women_pct=("is_women_owned", "mean"),
            )
            .sort_values("total_registered", ascending=False)
        )

        top_cat = (
            self.mse_data.groupby(["state", "category_l1"])
            .size()
            .reset_index(name="count")
            .sort_values(["state", "count"], ascending=[True, False])
            .drop_duplicates("state")
            .set_index("state")["category_l1"]
            .to_dict()
        )

        coords = self.districts.groupby("state", as_index=False)[["lat", "lon"]].mean()
        merged = summary.merge(coords, on="state", how="left")
        merged["lat"] = merged["lat"].fillna(22.0)
        merged["lon"] = merged["lon"].fillna(79.0)

        max_reg = max(float(merged["total_registered"].max()), 1.0)
        for _, row in merged.iterrows():
            popup = (
                f"<b>{row['state']}</b><br>"
                f"Total Registered: {int(row['total_registered'])}<br>"
                f"Total Live: {int(row['total_live'])}<br>"
                f"Women %: {row['women_pct'] * 100:.1f}%<br>"
                f"Top Category: {top_cat.get(row['state'], 'N/A')}"
            )
            radius = 6 + (row["total_registered"] / max_reg) * 16
            color = "#2a9d8f" if row["women_pct"] >= 0.5 else "#e76f51"
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=radius,
                color=color,
                fill=True,
                fill_opacity=0.65,
                popup=folium.Popup(popup, max_width=280),
            ).add_to(m)
        return m

    def get_district_bubble_map(self, state: str | None = None) -> folium.Map:
        """District-level bubble map. Bubble size reflects MSE count; color indicates stage completion."""
        m = folium.Map(location=[22.0, 79.0], zoom_start=5, tiles="cartodbpositron")
        df = self.mse_data.copy()
        if state:
            df = df[df["state"].astype(str).str.lower() == state.lower()]
            center = self.districts[self.districts["state"].astype(str).str.lower() == state.lower()]
            if not center.empty:
                m = folium.Map(location=[center["lat"].mean(), center["lon"].mean()], zoom_start=6, tiles="cartodbpositron")
        if df.empty:
            return m

        dist = (
            df.groupby(["state", "district"], as_index=False)
            .agg(mse_count=("mse_id", "count"), live_rate=("live", "mean"))
        )
        merged = dist.merge(self.districts, on=["state", "district"], how="left")
        merged["lat"] = merged["lat"].fillna(22.0)
        merged["lon"] = merged["lon"].fillna(79.0)

        max_count = max(float(merged["mse_count"].max()), 1.0)
        for _, row in merged.iterrows():
            color = "#2a9d8f" if row["live_rate"] >= 0.55 else "#f4a261" if row["live_rate"] >= 0.35 else "#e63946"
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=4 + (row["mse_count"] / max_count) * 10,
                color=color,
                fill=True,
                fill_opacity=0.6,
                popup=f"{row['district']} ({row['state']})<br>MSEs: {int(row['mse_count'])}<br>Live rate: {row['live_rate']*100:.1f}%",
            ).add_to(m)
        return m

    def get_tier_distribution(self) -> go.Figure:
        """Pie chart of Tier 1 / Tier 2 / Tier 3 onboarding distribution."""
        if "tier" not in self.mse_data.columns:
            if not self.districts.empty:
                merged = self.mse_data.merge(
                    self.districts[["state", "district", "tier"]],
                    on=["state", "district"],
                    how="left",
                )
                merged["tier"] = merged["tier"].fillna(3)
                data = merged
            else:
                data = self.mse_data.assign(tier=3)
        else:
            data = self.mse_data

        counts = data.groupby("tier", as_index=False).size()
        counts["tier_label"] = counts["tier"].astype(int).map({1: "Tier 1", 2: "Tier 2", 3: "Tier 3"}).fillna("Tier 3")
        fig = px.pie(counts, names="tier_label", values="size", title="MSE Distribution by City Tier")
        return fig

    def get_state_comparison(self) -> go.Figure:
        """Grouped bar chart comparing funnel stages by state."""
        grouped = (
            self.mse_data.groupby("state", as_index=False)
            .agg(
                registered=("registered", "sum"),
                catalog_created=("catalog_created", "sum"),
                snp_matched=("snp_matched", "sum"),
                live=("live", "sum"),
                first_order=("first_order", "sum"),
            )
            .sort_values("registered", ascending=False)
        )

        fig = go.Figure()
        for stage, color in [
            ("registered", "#264653"),
            ("catalog_created", "#2a9d8f"),
            ("snp_matched", "#e9c46a"),
            ("live", "#f4a261"),
            ("first_order", "#e76f51"),
        ]:
            fig.add_trace(go.Bar(name=stage, x=grouped["state"], y=grouped[stage], marker_color=color))
        fig.update_layout(
            barmode="group",
            title="State-wise Funnel Stage Comparison",
            xaxis_title="State",
            yaxis_title="Count",
        )
        return fig


def summarize_geo_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Backward-compatible helper: count rows by state."""
    counter = Counter(str(r.get("state", "Unknown")) for r in rows)
    return dict(counter)

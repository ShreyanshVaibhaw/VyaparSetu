"""Catalog performance analytics."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.common.models import ONDCCatalogItem


class CatalogPerformance:
    """Catalog-level quality and pricing analytics."""

    def __init__(self) -> None:
        pass

    def get_category_distribution(self, products_path: str) -> go.Figure:
        """Treemap showing product counts by ONDC categories."""
        try:
            df = pd.read_csv(products_path)
        except Exception:
            df = pd.DataFrame(columns=["category_l1", "category_l2"])
        if "category_l1" not in df.columns:
            df["category_l1"] = "General"
        if "category_l2" not in df.columns:
            df["category_l2"] = "General"
        grouped = df.groupby(["category_l1", "category_l2"], as_index=False).size()
        fig = px.treemap(
            grouped,
            path=["category_l1", "category_l2"],
            values="size",
            title="Catalog Category Distribution",
        )
        return fig

    def get_catalog_quality_score(self, catalog_items: list[ONDCCatalogItem]) -> dict[str, Any]:
        """Score catalog quality based on content completeness and richness."""
        if not catalog_items:
            return {"score": 0, "issues": ["No catalog items provided."], "suggestions": ["Generate at least one catalog item."]}

        total = len(catalog_items)
        long_desc_ok = sum(1 for i in catalog_items if 120 <= len(i.long_description) <= 2000)
        short_desc_ok = sum(1 for i in catalog_items if 40 <= len(i.short_description) <= 200)
        image_ok = sum(1 for i in catalog_items if len(i.images) >= 1)
        attr_ok = sum(1 for i in catalog_items if len(i.attributes) >= 3)
        hsn_ok = sum(1 for i in catalog_items if i.hsn_code and i.hsn_code != "0000")

        score = (
            (long_desc_ok / total) * 30
            + (short_desc_ok / total) * 20
            + (image_ok / total) * 20
            + (attr_ok / total) * 20
            + (hsn_ok / total) * 10
        )
        score = round(score, 2)

        issues: list[str] = []
        suggestions: list[str] = []
        if long_desc_ok / total < 0.7:
            issues.append("Long descriptions are too short or missing for many items.")
            suggestions.append("Regenerate long descriptions to 150-200 words with key product details.")
        if image_ok / total < 0.9:
            issues.append("Some catalog items have no product images.")
            suggestions.append("Upload at least one clear product image per item.")
        if attr_ok / total < 0.75:
            issues.append("Attribute completeness is low.")
            suggestions.append("Add category-specific required attributes before publishing.")
        if hsn_ok / total < 0.9:
            issues.append("HSN mapping missing or uncertain for some products.")
            suggestions.append("Review HSN codes to avoid GST compliance issues.")

        if not issues:
            suggestions.append("Catalog quality looks strong; continue periodic listing audits.")

        return {"score": score, "issues": issues, "suggestions": suggestions}

    def get_pricing_analysis(self, products_path: str) -> go.Figure:
        """Box plot of price distributions by category with outlier visibility."""
        try:
            df = pd.read_csv(products_path)
        except Exception:
            df = pd.DataFrame(columns=["category_l1", "category_l2", "price"])
        if "price" not in df.columns:
            df["price"] = 0.0
        if "category_l2" not in df.columns:
            df["category_l2"] = df.get("category_l1", "General")
        fig = px.box(
            df,
            x="category_l2",
            y="price",
            points="outliers",
            title="Pricing Distribution by Category",
        )
        fig.update_layout(xaxis_title="Category", yaxis_title="Price (INR)")
        return fig


def summarize_catalog_performance(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Backward-compatible basic performance summary helper."""
    if not rows:
        return {"views": 0.0, "clicks": 0.0, "conversion_rate": 0.0}
    views = float(sum(r.get("views", 0) for r in rows))
    clicks = float(sum(r.get("clicks", 0) for r in rows))
    conversion = (clicks / views) if views else 0.0
    return {"views": views, "clicks": clicks, "conversion_rate": round(conversion, 4)}

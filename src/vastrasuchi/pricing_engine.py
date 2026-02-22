"""Pricing engine for ONDC product recommendations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class PricingEngine:
    """Suggest and validate pricing ranges using category priors."""

    DEFAULT_CATEGORY_PRICES = {
        "Packaged Foods": {"base_mrp": 180, "min": 60, "max": 550},
        "Fresh Foods": {"base_mrp": 120, "min": 25, "max": 400},
        "Beverages": {"base_mrp": 95, "min": 25, "max": 350},
        "Women's Apparel": {"base_mrp": 1499, "min": 399, "max": 12000},
        "Accessories": {"base_mrp": 899, "min": 199, "max": 7000},
        "Home Decor": {"base_mrp": 999, "min": 199, "max": 15000},
        "Kitchen": {"base_mrp": 699, "min": 149, "max": 8500},
        "Electronics": {"base_mrp": 2499, "min": 399, "max": 55000},
        "Ayurveda & Herbal": {"base_mrp": 399, "min": 90, "max": 3500},
        "Seeds": {"base_mrp": 220, "min": 40, "max": 2200},
        "Crafts": {"base_mrp": 850, "min": 200, "max": 14000},
    }

    def __init__(self, category_pricing_path: str | None = None) -> None:
        self.category_prices = self._load_prices(category_pricing_path)

    def suggest_price(
        self,
        category_l2: str,
        product_description: str,
        quantity: str,
        is_handmade: bool = False,
    ) -> dict[str, Any]:
        """Suggest realistic price bands for a product."""
        base_info = self.category_prices.get(category_l2, {"base_mrp": 499, "min": 99, "max": 9000})
        quantity_factor = self._quantity_factor(quantity)
        text_factor = self._text_premium_factor(product_description)
        handmade_factor = 1.15 if is_handmade else 1.0

        mrp = base_info["base_mrp"] * quantity_factor * text_factor * handmade_factor
        selling = mrp * 0.92

        min_viable = max(base_info["min"], selling * 0.68)
        max_reasonable = min(base_info["max"] * max(quantity_factor, 1.0) * 1.35, selling * 1.45)

        confidence = 0.86 if category_l2 in self.category_prices else 0.62
        confidence = min(0.95, confidence + (0.05 if quantity_factor != 1.0 else 0.0))

        return {
            "suggested_mrp": round(mrp, 2),
            "suggested_selling": round(selling, 2),
            "min_viable": round(min_viable, 2),
            "max_reasonable": round(max_reasonable, 2),
            "confidence": round(confidence, 2),
        }

    def validate_price(self, price: float, category_l2: str) -> dict[str, Any]:
        """Validate whether price is competitive for category."""
        base_info = self.category_prices.get(category_l2, {"base_mrp": 499, "min": 99, "max": 9000})
        if price < base_info["min"]:
            return {
                "valid": False,
                "warning": "Price appears too low for sustainability; verify cost coverage.",
            }
        if price > base_info["max"] * 1.5:
            return {
                "valid": False,
                "warning": "Price appears significantly above market range; competitiveness may be affected.",
            }
        return {"valid": True, "warning": ""}

    def _load_prices(self, category_pricing_path: str | None) -> dict[str, dict[str, float]]:
        if not category_pricing_path:
            return self.DEFAULT_CATEGORY_PRICES
        path = Path(category_pricing_path)
        if not path.exists():
            return self.DEFAULT_CATEGORY_PRICES
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except (OSError, json.JSONDecodeError):
            pass
        return self.DEFAULT_CATEGORY_PRICES

    def _quantity_factor(self, quantity: str) -> float:
        if not quantity:
            return 1.0
        text = quantity.lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|gram|grams|ml|l|litre|liter|meter|m|piece|pc)?", text)
        if not match:
            return 1.0
        value = float(match.group(1))
        unit = (match.group(2) or "").lower()

        if unit in {"kg"}:
            grams = value * 1000
        elif unit in {"g", "gram", "grams"}:
            grams = value
        elif unit in {"l", "litre", "liter"}:
            grams = value * 1000
        elif unit in {"ml"}:
            grams = value
        elif unit in {"piece", "pc"}:
            return max(0.7, min(1.8, value))
        else:
            return 1.0

        if grams <= 100:
            return 0.75
        if grams <= 250:
            return 0.9
        if grams <= 500:
            return 1.0
        if grams <= 1000:
            return 1.2
        return 1.5

    def _text_premium_factor(self, description: str) -> float:
        text = description.lower()
        premium_terms = ["organic", "handmade", "pure silk", "genuine leather", "zari", "engraved"]
        hits = sum(1 for term in premium_terms if term in text)
        return min(1.35, 1.0 + hits * 0.08)


def suggest_price(cost_price: float, category: str = "General") -> dict[str, float | str]:
    """Backward-compatible cost-plus suggestion helper."""
    base = max(cost_price, 0.0)
    suggested = round(base * 1.35, 2)
    return {
        "category": category,
        "suggested_price": suggested,
        "min_price": round(base * 1.20, 2),
        "max_price": round(base * 1.50, 2),
    }

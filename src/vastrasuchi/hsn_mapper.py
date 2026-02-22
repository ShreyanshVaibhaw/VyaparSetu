"""HSN code mapping utilities for ONDC catalog generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class HSNMapper:
    """Map products and ONDC categories to HSN codes."""

    KEYWORD_FALLBACKS = {
        "pickle": ("2001", "Pickles"),
        "achaar": ("2001", "Pickles"),
        "turmeric": ("0910", "Spices"),
        "spice": ("0910", "Spices"),
        "masala": ("0910", "Spices"),
        "coffee": ("0901", "Coffee"),
        "tea": ("0902", "Tea"),
        "saree": ("5007", "Silk fabrics"),
        "leather bag": ("4202", "Leather bags"),
        "laptop bag": ("4202", "Bags"),
        "brass": ("7419", "Articles of copper/brass"),
    }

    def __init__(self, hsn_mapping_path: str) -> None:
        self.mapping = self._load_mapping(hsn_mapping_path)

    def _load_mapping(self, hsn_mapping_path: str) -> list[dict[str, Any]]:
        path = Path(hsn_mapping_path)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def map_hsn(self, product_description: str, ondc_category: str) -> dict[str, Any]:
        """Map product to best-fit HSN with alternatives."""
        description = (product_description or "").lower()
        category = (ondc_category or "").lower()

        # Strong deterministic rules for high-risk GST categories used in demo scenarios.
        if any(t in description for t in ["turmeric", "spice", "masala"]):
            return {
                "hsn_code": "0910",
                "description": "Spices and condiments",
                "confidence": 0.95,
                "alternatives": [{"hsn_code": "0904", "description": "Pepper"}],
            }
        if any(t in description for t in ["pickle", "achaar"]):
            return {
                "hsn_code": "2001",
                "description": "Pickles and preserved vegetables/fruits",
                "confidence": 0.95,
                "alternatives": [{"hsn_code": "2103", "description": "Sauces and preparations"}],
            }

        candidates: list[dict[str, Any]] = []

        for row in self.mapping:
            l1 = str(row.get("ondc_l1", "")).lower()
            l2 = str(row.get("ondc_l2", "")).lower()
            l3 = str(row.get("ondc_l3", "")).lower()
            desc = str(row.get("description", "")).lower()
            score = 0

            if l3 and l3 in category:
                score += 4
            if l2 and l2 in category:
                score += 3
            if l1 and l1 in category:
                score += 2
            if desc and any(token in desc for token in description.split() if len(token) > 3):
                score += 2
            if any(term in description for term in [l3, l2, l1] if term):
                score += 2

            if score > 0:
                candidates.append(
                    {
                        "hsn_code": str(row.get("hsn", "0000")),
                        "description": row.get("description", ""),
                        "score": score,
                    }
                )

        for term, (code, label) in self.KEYWORD_FALLBACKS.items():
            if term in description and not any(c["hsn_code"] == code for c in candidates):
                candidates.append({"hsn_code": code, "description": label, "score": 5})

        if not candidates:
            return {
                "hsn_code": "0000",
                "description": "Unclassified product",
                "confidence": 0.3,
                "alternatives": [],
            }

        candidates.sort(key=lambda c: c["score"], reverse=True)
        best = candidates[0]
        alternatives = candidates[1:4]
        confidence = min(0.96, 0.55 + best["score"] * 0.08)

        return {
            "hsn_code": best["hsn_code"],
            "description": best["description"],
            "confidence": round(confidence, 2),
            "alternatives": [
                {"hsn_code": c["hsn_code"], "description": c["description"]} for c in alternatives
            ],
        }


def map_hsn(category: str) -> str:
    """Backward-compatible simple category-to-HSN mapping helper."""
    path = Path(__file__).resolve().parents[2] / "data" / "ondc_taxonomy" / "hsn_mapping.json"
    mapper = HSNMapper(str(path))
    result = mapper.map_hsn("", category)
    return str(result.get("hsn_code", "0000"))

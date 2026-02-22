"""Business classification engine for mapping MSEs to ONDC categories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.models import MSEProfile
from src.llm.prompt_templates import (
    BUSINESS_CLASSIFICATION_TEMPLATE,
    SYSTEM_PROMPT_VYAPARSETU,
)


class BusinessClassifier:
    """Hybrid classifier using NIC rules plus LLM refinement."""

    def __init__(self, llm_client: Any, nic_to_ondc_path: str, categories_path: str) -> None:
        self.llm = llm_client
        self.nic_mapping = self._load_mapping(nic_to_ondc_path)
        self.categories = self._load_categories(categories_path)

    def _load_mapping(self, path: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            return []
        return []

    def _load_categories(self, path: str) -> dict[str, Any]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            return {"categories": []}
        return {"categories": []}

    def classify_from_nic(self, nic_code: str) -> list[str]:
        """Rule-based: NIC 2-digit code -> ONDC L1 categories using mapping table."""
        nic_2digit = "".join(ch for ch in nic_code if ch.isdigit())[:2]
        if not nic_2digit:
            return []
        for row in self.nic_mapping:
            if row.get("nic_2digit") == nic_2digit:
                categories = row.get("ondc_l1", [])
                if isinstance(categories, list):
                    return categories
                if isinstance(categories, str):
                    return [categories]
                return []
        return []

    def classify_from_description(
        self,
        enterprise_name: str,
        nic_code: str,
        nic_desc: str,
        products_services: list[str],
        district: str,
        state: str,
        major_activity: str,
    ) -> dict[str, Any]:
        """LLM-based: full business context -> detailed ONDC classification."""
        categories_text = self._categories_text()
        prompt = BUSINESS_CLASSIFICATION_TEMPLATE.format(
            enterprise_name=enterprise_name,
            nic_code=nic_code,
            nic_description=nic_desc,
            products_services=", ".join(products_services) if products_services else "Not provided",
            district=district,
            state=state,
            major_activity=major_activity,
            ondc_categories=categories_text,
        )
        response = self.llm.generate_json(prompt=prompt, system=SYSTEM_PROMPT_VYAPARSETU)
        return self._normalize_llm_response(response)

    def classify_hybrid(self, mse_profile: MSEProfile) -> dict[str, Any]:
        """Hybrid: NIC mapping + LLM refinement + compatibility validation."""
        nic_categories = self.classify_from_nic(mse_profile.nic_2digit)
        llm_result = self.classify_from_description(
            enterprise_name=mse_profile.enterprise_name,
            nic_code=mse_profile.nic_2digit,
            nic_desc=mse_profile.nic_description,
            products_services=mse_profile.products_services,
            district=mse_profile.district,
            state=mse_profile.state,
            major_activity=mse_profile.major_activity,
        )

        primary_l1 = str(llm_result.get("primary_category_l1", "")).strip()
        primary_l2 = str(llm_result.get("primary_category_l2", "")).strip()
        secondary = list(llm_result.get("secondary_categories", []))
        confidence = self._safe_float(llm_result.get("confidence"), 0.5)
        reasoning = str(llm_result.get("reasoning", "Classification based on available details.")).strip()

        # Validation: if LLM category conflicts with NIC mapping, prefer mapped coarse category.
        if nic_categories:
            if not primary_l1 or primary_l1 not in nic_categories:
                original = primary_l1 or "unknown"
                primary_l1 = nic_categories[0]
                if original and original != "unknown" and original not in secondary:
                    secondary.append(original)
                confidence = min(confidence, 0.75)
                reasoning = (
                    f"{reasoning} L1 adjusted to NIC-compatible category ({primary_l1}) from {original}."
                )

        if not primary_l2:
            primary_l2 = self._first_l2_for_l1(primary_l1) or "General"

        return {
            "primary_l1": primary_l1 or "General",
            "primary_l2": primary_l2,
            "secondary": secondary,
            "confidence": max(0.0, min(confidence, 1.0)),
            "reasoning": reasoning,
        }

    def _categories_text(self) -> str:
        lines: list[str] = []
        for l1 in self.categories.get("categories", []):
            l1_name = l1.get("l1", "")
            lines.append(f"- {l1_name}")
            for l2 in l1.get("l2_categories", []):
                l2_name = l2.get("l2", "")
                l3_items = ", ".join(l2.get("l3_categories", []))
                lines.append(f"  - {l2_name}: {l3_items}")
        return "\n".join(lines)

    def _first_l2_for_l1(self, l1_name: str) -> str | None:
        for l1 in self.categories.get("categories", []):
            if l1.get("l1") == l1_name:
                l2_categories = l1.get("l2_categories", [])
                if l2_categories:
                    return str(l2_categories[0].get("l2", "General"))
        return None

    def _normalize_llm_response(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {
                "primary_category_l1": "General",
                "primary_category_l2": "General",
                "secondary_categories": [],
                "suggested_product_types": [],
                "confidence": 0.5,
                "reasoning": "Fallback classification due to invalid LLM response.",
            }
        secondary = data.get("secondary_categories", [])
        if not isinstance(secondary, list):
            secondary = []
        product_types = data.get("suggested_product_types", [])
        if not isinstance(product_types, list):
            product_types = []
        return {
            "primary_category_l1": str(data.get("primary_category_l1", "General")),
            "primary_category_l2": str(data.get("primary_category_l2", "General")),
            "secondary_categories": [str(x) for x in secondary],
            "suggested_product_types": [str(x) for x in product_types],
            "confidence": self._safe_float(data.get("confidence"), 0.5),
            "reasoning": str(data.get("reasoning", "Classification derived from available context.")),
        }

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


def classify_business(nic_code: str, business_description: str = "") -> dict[str, str | float]:
    """Backward-compatible helper for basic single-code classification."""
    mapping = {
        "10": "Food & Beverage",
        "13": "Fashion",
        "32": "Handicrafts & Handloom",
    }
    category = mapping.get("".join(ch for ch in nic_code if ch.isdigit())[:2], "General")
    return {"category": category, "confidence": 0.6, "description": business_description}

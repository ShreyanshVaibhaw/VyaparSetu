"""ONDC product taxonomy classification engine."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class ProductClassifier:
    """Classify product descriptions into ONDC taxonomy levels."""

    def __init__(self, categories_path: str, hsn_mapping_path: str, llm_client: Any) -> None:
        self.taxonomy = self._load_taxonomy(categories_path)
        self.hsn_map = self._load_hsn(hsn_mapping_path)
        self.llm = llm_client
        self.nic_mapping = self._load_nic_mapping(categories_path)

    def classify(
        self,
        product_description: str,
        business_nic: str | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        """Classify a single product to ONDC L1/L2/L3 with confidence."""
        safe_description = str(product_description or "")
        narrowed_l1 = self._narrow_l1_from_nic(business_nic)
        keyword_hits = self._keyword_rank(safe_description, narrowed_l1)
        best_keyword = keyword_hits[0] if keyword_hits else None

        llm_guess = self._llm_classify(safe_description, language, narrowed_l1)
        llm_valid = self._is_valid_path(llm_guess.get("l1"), llm_guess.get("l2"), llm_guess.get("l3"))

        if best_keyword and llm_valid:
            agree = (
                best_keyword["l1"] == llm_guess.get("l1")
                and best_keyword["l2"] == llm_guess.get("l2")
            )
            selected = {
                "l1": llm_guess.get("l1"),
                "l2": llm_guess.get("l2"),
                "l3": llm_guess.get("l3"),
            }
            confidence = 0.9 if agree else 0.72
        elif llm_valid:
            selected = {
                "l1": llm_guess.get("l1"),
                "l2": llm_guess.get("l2"),
                "l3": llm_guess.get("l3"),
            }
            confidence = 0.68
        elif best_keyword:
            selected = {"l1": best_keyword["l1"], "l2": best_keyword["l2"], "l3": best_keyword["l3"]}
            confidence = 0.75 if best_keyword["score"] >= 2 else 0.6
        else:
            selected = {"l1": "Grocery", "l2": "Basics", "l3": "General"}
            confidence = 0.4

        alternatives = [
            {"l1": h["l1"], "l2": h["l2"], "l3": h["l3"], "score": h["score"]}
            for h in keyword_hits[1:4]
        ]

        return {
            "l1": selected["l1"],
            "l2": selected["l2"],
            "l3": selected["l3"],
            "confidence": round(confidence, 3),
            "alternatives": alternatives,
        }

    def classify_batch(self, products: list[str], business_nic: str | None = None) -> list[dict[str, Any]]:
        """Classify multiple products, attempting one LLM call for efficiency."""
        if not products:
            return []

        narrowed = self._narrow_l1_from_nic(business_nic)
        prompt = (
            "Classify each product into ONDC taxonomy and return JSON with key 'items' containing "
            "objects {index,l1,l2,l3}. Products:\n"
            + "\n".join(f"{i}: {p}" for i, p in enumerate(products))
            + f"\nAllowed L1 categories: {', '.join(narrowed) if narrowed else 'All'}"
        )
        try:
            data = self.llm.generate_json(prompt=prompt, system=None)
            items = data.get("items", []) if isinstance(data, dict) else []
            if isinstance(items, list) and len(items) == len(products):
                results = []
                for idx, product in enumerate(products):
                    item = items[idx] if idx < len(items) and isinstance(items[idx], dict) else {}
                    path = {
                        "l1": item.get("l1"),
                        "l2": item.get("l2"),
                        "l3": item.get("l3"),
                    }
                    if not self._is_valid_path(path["l1"], path["l2"], path["l3"]):
                        path = self.classify(product, business_nic=business_nic)
                    else:
                        path["confidence"] = 0.7
                        path["alternatives"] = []
                    results.append(path)
                return results
        except Exception:
            pass

        return [self.classify(product, business_nic=business_nic) for product in products]

    def get_category_path(self, l1: str, l2: str, l3: str | None = None) -> str:
        """Format category path string."""
        if l3:
            return f"{l1} > {l2} > {l3}"
        return f"{l1} > {l2}"

    def _load_taxonomy(self, path: str) -> dict[str, Any]:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {"categories": []}
        except (OSError, json.JSONDecodeError):
            return {"categories": []}

    def _load_hsn(self, path: str) -> list[dict[str, Any]]:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _load_nic_mapping(self, categories_path: str) -> list[dict[str, Any]]:
        nic_path = Path(categories_path).with_name("nic_to_ondc.json")
        if not nic_path.exists():
            return []
        try:
            payload = json.loads(nic_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _narrow_l1_from_nic(self, business_nic: str | None) -> list[str]:
        if not business_nic:
            return []
        nic_2 = "".join(ch for ch in business_nic if ch.isdigit())[:2]
        for row in self.nic_mapping:
            if row.get("nic_2digit") == nic_2:
                categories = row.get("ondc_l1", [])
                if isinstance(categories, list):
                    return [str(c) for c in categories]
                if isinstance(categories, str):
                    return [categories]
        return []

    def _keyword_rank(self, description: str, narrowed_l1: list[str]) -> list[dict[str, Any]]:
        text = description.lower()
        hits: list[dict[str, Any]] = []
        for l1_row in self.taxonomy.get("categories", []):
            l1 = str(l1_row.get("l1", ""))
            if narrowed_l1 and l1 not in narrowed_l1:
                continue
            for l2_row in l1_row.get("l2_categories", []):
                l2 = str(l2_row.get("l2", ""))
                l2_terms = self._terms(l2)
                for l3 in l2_row.get("l3_categories", []):
                    l3_name = str(l3)
                    terms = self._terms(l1) + l2_terms + self._terms(l3_name)
                    score = sum(1 for t in terms if t and t in text)
                    score += self._scenario_boost(text, l1, l2, l3_name)
                    if score > 0:
                        hits.append({"l1": l1, "l2": l2, "l3": l3_name, "score": score})

        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits

    def _llm_classify(self, description: str, language: str, narrowed_l1: list[str]) -> dict[str, Any]:
        prompt = (
            "Classify this product into ONDC categories. Return JSON with keys l1,l2,l3.\n"
            f"Product description: {description}\n"
            f"Language: {language}\n"
            f"Allowed L1 categories: {', '.join(narrowed_l1) if narrowed_l1 else 'All'}"
        )
        try:
            data = self.llm.generate_json(prompt=prompt, system=None)
            if isinstance(data, dict):
                return {
                    "l1": data.get("l1") or data.get("category_l1") or data.get("primary_category_l1"),
                    "l2": data.get("l2") or data.get("category_l2") or data.get("primary_category_l2"),
                    "l3": data.get("l3") or data.get("category_l3"),
                }
        except Exception:
            pass
        return {"l1": None, "l2": None, "l3": None}

    def _is_valid_path(self, l1: Any, l2: Any, l3: Any) -> bool:
        if not l1 or not l2:
            return False
        for l1_row in self.taxonomy.get("categories", []):
            if l1_row.get("l1") != l1:
                continue
            for l2_row in l1_row.get("l2_categories", []):
                if l2_row.get("l2") != l2:
                    continue
                l3_list = l2_row.get("l3_categories", [])
                if not l3:
                    return True
                return l3 in l3_list
        return False

    def _scenario_boost(self, text: str, l1: str, l2: str, l3: str) -> int:
        boosts = [
            (["achaar", "pickle"], ("Food & Beverage", "Packaged Foods", "Pickles & Chutneys")),
            (["turmeric", "masala", "spice"], ("Food & Beverage", "Packaged Foods", "Spices & Masala")),
            (["kanchipuram", "saree", "silk"], ("Fashion", "Women's Apparel", "Saree")),
            (["brass", "vase", "engraved"], ("Home & Kitchen", "Home Decor", "Metal Crafts")),
            (["laptop bag", "leather"], ("Fashion", "Accessories", "Bags & Wallets")),
        ]
        for tokens, target in boosts:
            if all(t in text for t in tokens if " " not in t) or any(t in text for t in tokens):
                if (l1, l2, l3) == target:
                    return 3
        return 0

    def _terms(self, value: str) -> list[str]:
        cleaned = re.sub(r"[^a-z0-9& ]+", " ", value.lower())
        parts = [p for p in cleaned.replace("&", " ").split() if len(p) > 2]
        return [cleaned.strip()] + parts


def classify_product(product_text: str, nic_hint: str = "") -> dict[str, Any]:
    """Backward-compatible classifier wrapper."""
    root = Path(__file__).resolve().parents[2] / "data" / "ondc_taxonomy"
    from src.llm.ollama_client import LLMClient

    classifier = ProductClassifier(
        categories_path=str(root / "categories.json"),
        hsn_mapping_path=str(root / "hsn_mapping.json"),
        llm_client=LLMClient(),
    )
    result = classifier.classify(product_text, business_nic=nic_hint or None, language="en")
    return {
        "level_1": result["l1"],
        "level_2": result["l2"],
        "level_3": result["l3"],
        "confidence": result["confidence"],
    }

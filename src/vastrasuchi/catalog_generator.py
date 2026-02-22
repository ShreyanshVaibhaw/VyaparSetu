"""Core VastraSuchi catalog generation engine."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.common.models import MSEProfile, ONDCCatalogItem, ProductGenerationRequest
from src.llm.prompt_templates import PRODUCT_CATALOG_TEMPLATE, SYSTEM_PROMPT_VYAPARSETU


class CatalogGenerator:
    """Convert raw MSE product input into ONDCCatalogItem records."""

    def __init__(self, llm_client: Any, product_classifier: Any, hsn_mapper: Any, pricing_engine: Any) -> None:
        self.llm = llm_client
        self.classifier = product_classifier
        self.hsn = hsn_mapper
        self.pricing = pricing_engine
        self.attribute_schemas = self._load_attribute_schemas()

    def generate_catalog_item(
        self,
        request: ProductGenerationRequest,
        mse_profile: MSEProfile,
    ) -> ONDCCatalogItem:
        """Pipeline: raw product request -> validated ONDC catalog item."""
        normalized_desc = self._translate_to_english(request.product_description_raw, request.language)

        classification = self.classifier.classify(
            product_description=normalized_desc,
            business_nic=mse_profile.nic_2digit,
            language=request.language,
        )

        category_path = self.classifier.get_category_path(
            classification["l1"], classification["l2"], classification.get("l3")
        )
        hsn_info = self.hsn.map_hsn(normalized_desc, category_path)
        quantity_value, quantity_unit = self._extract_quantity(normalized_desc)

        pricing = self.pricing.suggest_price(
            category_l2=classification["l2"],
            product_description=normalized_desc,
            quantity=f"{quantity_value} {quantity_unit}",
            is_handmade=("handmade" in normalized_desc.lower() or "ghar ka" in request.product_description_raw.lower()),
        )

        llm_data = self._generate_catalog_content(
            request=request,
            mse_profile=mse_profile,
            classification=classification,
            normalized_desc=normalized_desc,
        )

        product_name_en = llm_data.get("product_name_en") or self._default_name(normalized_desc)
        short_desc = llm_data.get("short_description") or self._default_short_desc(normalized_desc)
        long_desc = llm_data.get("long_description") or self._default_long_desc(normalized_desc, mse_profile)

        attributes = self._merge_attributes(
            category_l1=classification["l1"],
            llm_attributes=llm_data.get("attributes", {}),
            quantity_value=quantity_value,
            quantity_unit=quantity_unit,
        )
        tags = self._default_tags(normalized_desc, llm_data.get("tags", {}))

        item = ONDCCatalogItem(
            item_id=f"ITEM-{uuid4().hex[:12].upper()}",
            mse_udyam=mse_profile.udyam_number,
            product_name_en=product_name_en[:80],
            product_name_regional=llm_data.get("product_name_regional"),
            short_description=short_desc[:200],
            long_description=long_desc[:2000],
            category_l1=classification["l1"],
            category_l2=classification["l2"],
            category_l3=classification.get("l3"),
            hsn_code=str(hsn_info.get("hsn_code", "0000")),
            price_mrp=float(pricing["suggested_mrp"]),
            price_selling=float(pricing["suggested_selling"]),
            quantity_unit=quantity_unit,
            quantity_value=float(quantity_value),
            images=request.product_images or [],
            attributes={str(k): str(v) for k, v in attributes.items()},
            tags={str(k): str(v) for k, v in tags.items()},
            origin_country="IND",
            returnable=True,
            cancellable=True,
            available_on_cod=True,
            time_to_ship="P2D",
            generated_by_ai=True,
            reviewed_by_mse=False,
            created_at=datetime.now(timezone.utc),
        )

        self._validate_item(item)
        return item

    def generate_from_voice(
        self,
        audio_description: str,
        images: list[str],
        mse_profile: MSEProfile,
        language: str,
    ) -> ONDCCatalogItem:
        """Generate item from voice transcript and image list."""
        request = ProductGenerationRequest(
            mse_udyam=mse_profile.udyam_number,
            product_description_raw=audio_description,
            product_images=images,
            language=language,
            category_hint=None,
        )
        return self.generate_catalog_item(request, mse_profile)

    def generate_bulk(self, products: list[dict[str, Any]], mse_profile: MSEProfile) -> list[ONDCCatalogItem]:
        """Generate multiple catalog items in batch mode."""
        items: list[ONDCCatalogItem] = []
        for product in products:
            request = ProductGenerationRequest(
                mse_udyam=mse_profile.udyam_number,
                product_description_raw=str(product.get("description", "")),
                product_images=product.get("images", []) or [],
                language=str(product.get("language", mse_profile.language_preference or "en")),
                category_hint=product.get("category_hint"),
            )
            items.append(self.generate_catalog_item(request, mse_profile))
        return items

    def regenerate_description(self, item: ONDCCatalogItem, feedback: str) -> ONDCCatalogItem:
        """Regenerate product description using MSE feedback."""
        prompt = (
            "Rewrite ONDC product descriptions based on feedback.\n"
            f"Current short description: {item.short_description}\n"
            f"Current long description: {item.long_description}\n"
            f"Feedback: {feedback}\n"
            'Return JSON with keys "short_description" and "long_description".'
        )
        try:
            data = self.llm.generate_json(prompt=prompt, system=SYSTEM_PROMPT_VYAPARSETU)
            short_desc = str(data.get("short_description", item.short_description))[:200]
            long_desc = str(data.get("long_description", item.long_description))[:2000]
        except Exception:
            short_desc = item.short_description
            long_desc = item.long_description
        return item.model_copy(update={"short_description": short_desc, "long_description": long_desc})

    def _load_attribute_schemas(self) -> dict[str, Any]:
        path = Path(__file__).resolve().parents[2] / "data" / "catalog_templates" / "attribute_schemas.json"
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _translate_to_english(self, text: str, language: str) -> str:
        if language == "en":
            return text
        replaced = text.lower()
        translation_hints = {
            "aam ka achaar": "mango pickle",
            "achaar": "pickle",
            "ghar ka bana hua": "homemade",
            "desi ghee": "desi ghee",
            "saree": "saree",
            "zari": "zari",
            "haldi": "turmeric",
            "masala": "spices",
        }
        for src, dst in translation_hints.items():
            replaced = replaced.replace(src, dst)
        return replaced

    def _generate_catalog_content(
        self,
        request: ProductGenerationRequest,
        mse_profile: MSEProfile,
        classification: dict[str, Any],
        normalized_desc: str,
    ) -> dict[str, Any]:
        categories_subset = self.classifier.get_category_path(
            classification["l1"], classification["l2"], classification.get("l3")
        )
        prompt = PRODUCT_CATALOG_TEMPLATE.format(
            business_name=mse_profile.enterprise_name,
            nic_description=mse_profile.nic_description,
            district=mse_profile.district,
            state=mse_profile.state,
            raw_description=normalized_desc,
            language=request.language,
            category_hint=request.category_hint or "",
            categories_subset=categories_subset,
        )
        try:
            data = self.llm.generate_json(prompt=prompt, system=SYSTEM_PROMPT_VYAPARSETU)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _extract_quantity(self, text: str) -> tuple[float, str]:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|gram|grams|ml|l|litre|liter|meter|m|piece|pc)", text.lower())
        if not match:
            return 1.0, "piece"
        value = float(match.group(1))
        unit = match.group(2)
        if unit in {"gram", "grams"}:
            unit = "gram"
        elif unit in {"kg"}:
            unit = "kg"
        elif unit in {"ml"}:
            unit = "ml"
        elif unit in {"l", "litre", "liter"}:
            unit = "litre"
        elif unit in {"piece", "pc"}:
            unit = "piece"
        elif unit in {"m"}:
            unit = "meter"
        return value, unit

    def _merge_attributes(
        self,
        category_l1: str,
        llm_attributes: Any,
        quantity_value: float,
        quantity_unit: str,
    ) -> dict[str, str]:
        attributes: dict[str, str] = {}
        if isinstance(llm_attributes, dict):
            attributes.update({str(k): str(v) for k, v in llm_attributes.items()})

        schema = self.attribute_schemas.get(category_l1, {})
        required = schema.get("required", []) if isinstance(schema, dict) else []
        for key in required:
            attributes.setdefault(str(key), "not_specified")

        attributes.setdefault("net_quantity", f"{quantity_value} {quantity_unit}")
        return attributes

    def _default_tags(self, normalized_desc: str, llm_tags: Any) -> dict[str, str]:
        tags = {}
        if isinstance(llm_tags, dict):
            tags.update({str(k): str(v) for k, v in llm_tags.items()})
        desc = normalized_desc.lower()
        tags.setdefault("handmade", "yes" if "handmade" in desc or "ghar ka" in desc else "no")
        tags.setdefault("organic", "yes" if "organic" in desc else "no")
        tags.setdefault("veg_nonveg", "veg")
        return tags

    def _default_name(self, normalized_desc: str) -> str:
        base = normalized_desc.strip()
        if not base:
            return "MSE Product"
        return base[:1].upper() + base[1:80]

    def _default_short_desc(self, normalized_desc: str) -> str:
        return f"{self._default_name(normalized_desc)} suitable for ONDC catalog listing."

    def _default_long_desc(self, normalized_desc: str, mse_profile: MSEProfile) -> str:
        return (
            f"{self._default_name(normalized_desc)} offered by {mse_profile.enterprise_name} in "
            f"{mse_profile.district}, {mse_profile.state}. Generated for ONDC-ready listing with "
            "structured product details and compliance tags."
        )

    def _validate_item(self, item: ONDCCatalogItem) -> None:
        if not item.product_name_en:
            raise ValueError("Catalog item missing product_name_en")
        if item.price_selling <= 0:
            raise ValueError("Catalog item requires positive selling price")
        if not item.category_l1 or not item.category_l2:
            raise ValueError("Catalog item category hierarchy is incomplete")


def generate_catalog_entry(product_name: str, description: str, language: str = "en") -> dict[str, Any]:
    """Backward-compatible lightweight catalog entry helper."""
    return {
        "name": product_name,
        "description": description,
        "language": language,
        "status": "draft",
    }

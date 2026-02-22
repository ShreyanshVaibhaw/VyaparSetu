"""Format and validate ONDC catalog payloads."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.common.models import ONDCCatalogItem


class ONDCFormatter:
    """Convert Pydantic catalog objects into ONDC-compatible JSON."""

    def __init__(self, attribute_schemas_path: str) -> None:
        self.schemas = self._load_schemas(attribute_schemas_path)

    def _load_schemas(self, attribute_schemas_path: str) -> dict[str, Any]:
        path = Path(attribute_schemas_path)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def format_catalog_item(self, item: ONDCCatalogItem) -> dict[str, Any]:
        """Convert ONDCCatalogItem into ONDC-like catalog schema."""
        return {
            "id": item.item_id,
            "descriptor": {
                "name": item.product_name_en,
                "short_desc": item.short_description,
                "long_desc": item.long_description,
                "images": [{"url": img, "size_type": "sm"} for img in item.images],
                "code": f"HSN:{item.hsn_code}",
            },
            "category": {
                "l1": item.category_l1,
                "l2": item.category_l2,
                "l3": item.category_l3,
            },
            "price": {
                "currency": "INR",
                "maximum_value": str(round(item.price_mrp, 2)),
                "value": str(round(item.price_selling, 2)),
            },
            "quantity": {
                "unitized": {
                    "measure": {
                        "value": str(item.quantity_value),
                        "unit": item.quantity_unit,
                    }
                }
            },
            "tags": [{"code": key, "value": value} for key, value in item.tags.items()],
            "attributes": item.attributes,
            "metadata": {
                "origin_country": item.origin_country,
                "returnable": item.returnable,
                "cancellable": item.cancellable,
                "cod_available": item.available_on_cod,
                "time_to_ship": item.time_to_ship,
                "generated_by_ai": item.generated_by_ai,
                "reviewed_by_mse": item.reviewed_by_mse,
                "created_at": item.created_at.isoformat(),
                "mse_udyam": item.mse_udyam,
            },
        }

    def validate_catalog(self, formatted_item: dict[str, Any]) -> dict[str, Any]:
        """Validate formatted ONDC payload and category-specific required attributes."""
        errors: list[str] = []
        warnings: list[str] = []

        descriptor = formatted_item.get("descriptor", {})
        category = formatted_item.get("category", {})
        price = formatted_item.get("price", {})
        quantity = formatted_item.get("quantity", {})
        attributes = formatted_item.get("attributes", {})

        for field in ["name", "short_desc", "long_desc", "code"]:
            if not descriptor.get(field):
                errors.append(f"Missing descriptor.{field}")
        for field in ["l1", "l2"]:
            if not category.get(field):
                errors.append(f"Missing category.{field}")
        for field in ["value", "maximum_value", "currency"]:
            if not price.get(field):
                errors.append(f"Missing price.{field}")

        measure = quantity.get("unitized", {}).get("measure", {})
        if not measure.get("value") or not measure.get("unit"):
            errors.append("Missing quantity.unitized.measure.value/unit")

        l1 = category.get("l1")
        schema = self.schemas.get(l1, {})
        required_attrs = schema.get("required", []) if isinstance(schema, dict) else []
        for required in required_attrs:
            if required not in attributes:
                warnings.append(f"Missing recommended attribute for {l1}: {required}")

        if descriptor.get("name") and len(descriptor["name"]) > 80:
            warnings.append("Product name exceeds 80 characters.")
        if descriptor.get("short_desc") and len(descriptor["short_desc"]) > 200:
            warnings.append("short_desc exceeds 200 characters.")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def export_bulk_csv(self, items: list[ONDCCatalogItem], output_path: str) -> None:
        """Export items to a flat CSV suitable for SNP bulk uploads."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "item_id",
            "mse_udyam",
            "product_name_en",
            "product_name_regional",
            "short_description",
            "long_description",
            "category_l1",
            "category_l2",
            "category_l3",
            "hsn_code",
            "price_mrp",
            "price_selling",
            "quantity_unit",
            "quantity_value",
            "images",
            "attributes",
            "tags",
            "origin_country",
            "returnable",
            "cancellable",
            "available_on_cod",
            "time_to_ship",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                writer.writerow(
                    {
                        "item_id": item.item_id,
                        "mse_udyam": item.mse_udyam,
                        "product_name_en": item.product_name_en,
                        "product_name_regional": item.product_name_regional or "",
                        "short_description": item.short_description,
                        "long_description": item.long_description,
                        "category_l1": item.category_l1,
                        "category_l2": item.category_l2,
                        "category_l3": item.category_l3 or "",
                        "hsn_code": item.hsn_code,
                        "price_mrp": item.price_mrp,
                        "price_selling": item.price_selling,
                        "quantity_unit": item.quantity_unit,
                        "quantity_value": item.quantity_value,
                        "images": "|".join(item.images),
                        "attributes": json.dumps(item.attributes, ensure_ascii=False),
                        "tags": json.dumps(item.tags, ensure_ascii=False),
                        "origin_country": item.origin_country,
                        "returnable": item.returnable,
                        "cancellable": item.cancellable,
                        "available_on_cod": item.available_on_cod,
                        "time_to_ship": item.time_to_ship,
                    }
                )


def format_ondc_item(item: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible minimal formatting helper."""
    return {
        "descriptor": {
            "name": item.get("name", item.get("product_name_en", "")),
            "short_desc": item.get("description", item.get("short_description", "")),
            "code": f"HSN:{item.get('hsn_code', '0000')}",
        },
        "price": {
            "value": str(item.get("price", item.get("price_selling", "0"))),
            "currency": "INR",
        },
    }

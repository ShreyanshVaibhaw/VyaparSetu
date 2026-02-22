"""Catalog export utilities for PDF, CSV, and ONDC JSON."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from src.common.models import MSEProfile, ONDCCatalogItem


def export_catalog_pdf(items: list[ONDCCatalogItem], mse: MSEProfile, output_path: str) -> None:
    """Export one-page-per-product catalog PDF."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    for idx, item in enumerate(items, start=1):
        y = height - 35
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30, y, f"Catalog Item {idx}")
        y -= 18

        c.setFont("Helvetica", 10)
        c.drawString(30, y, f"MSE: {mse.enterprise_name} ({mse.udyam_number})")
        y -= 16

        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, y, item.product_name_en[:80])
        y -= 14
        c.setFont("Helvetica", 10)
        c.drawString(30, y, item.product_name_regional[:100] if item.product_name_regional else "-")
        y -= 14
        c.drawString(30, y, f"Category: {item.category_l1} > {item.category_l2} > {item.category_l3 or '-'}")
        y -= 14
        c.drawString(30, y, f"HSN: {item.hsn_code} | Price: INR {item.price_selling:.2f} | MRP: INR {item.price_mrp:.2f}")
        y -= 14
        c.drawString(30, y, f"Quantity: {item.quantity_value} {item.quantity_unit}")
        y -= 18

        c.setFont("Helvetica-Bold", 11)
        c.drawString(30, y, "Short Description")
        y -= 14
        c.setFont("Helvetica", 10)
        c.drawString(30, y, item.short_description[:120])
        y -= 20

        c.setFont("Helvetica-Bold", 11)
        c.drawString(30, y, "Long Description")
        y -= 14
        c.setFont("Helvetica", 10)
        for chunk in _chunks(item.long_description, 115):
            c.drawString(30, y, chunk)
            y -= 12
            if y < 70:
                break

        y -= 8
        c.setFont("Helvetica-Bold", 11)
        c.drawString(30, y, "Attributes")
        y -= 14
        c.setFont("Helvetica", 10)
        for key, value in list(item.attributes.items())[:10]:
            c.drawString(30, y, f"- {key}: {value}")
            y -= 12
            if y < 50:
                break

        c.showPage()

    c.save()


def export_catalog_csv(items: list[ONDCCatalogItem], output_path: str) -> None:
    """Export SNP-compatible bulk CSV."""
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


def export_catalog_ondc_json(items: list[ONDCCatalogItem], output_path: str) -> None:
    """Export ONDC API-compatible JSON payload."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {"items": []}
    for item in items:
        payload["items"].append(
            {
                "id": item.item_id,
                "descriptor": {
                    "name": item.product_name_en,
                    "short_desc": item.short_description,
                    "long_desc": item.long_description,
                    "images": [{"url": img} for img in item.images],
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
                "attributes": item.attributes,
                "tags": item.tags,
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
        )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _chunks(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


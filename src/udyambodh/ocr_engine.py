"""OCR engine for Udyam documents and product labels."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class UdyamOCR:
    """OCR extractor with PaddleOCR lazy-loading and safe fallback."""

    def __init__(self) -> None:
        self.ocr = None
        self._ocr_available = None

    def extract_from_certificate(self, image_path: str) -> dict[str, Any]:
        """Extract key fields from Udyam certificate or visiting card."""
        result = self._perform_ocr(image_path)
        if not result["ok"]:
            return {
                "message": result["message"],
                "udyam_number": None,
                "enterprise_name": None,
                "owner_name": None,
                "address": None,
                "products": [],
            }

        text = result["text"]
        return {
            "message": "ok",
            "udyam_number": self._extract_udyam_number(text),
            "enterprise_name": self._extract_line_after_keyword(text, ["enterprise name", "name of enterprise"]),
            "owner_name": self._extract_line_after_keyword(text, ["owner", "proprietor", "authorized signatory"]),
            "address": self._extract_line_after_keyword(text, ["address"]),
            "products": self._extract_products(text),
        }

    def extract_from_product_label(self, image_path: str) -> dict[str, Any]:
        """Extract product fields from packaging label text."""
        result = self._perform_ocr(image_path)
        if not result["ok"]:
            return {
                "message": result["message"],
                "product_name": None,
                "weight": None,
                "price": None,
                "ingredients": None,
                "fssai_number": None,
            }

        text = result["text"]
        weight = self._first_match(r"(\d+(?:\.\d+)?\s?(?:g|gm|kg|ml|l|litre|liter))", text)
        price = self._first_match(r"(?:rs\.?|₹)\s?\d+(?:\.\d{1,2})?", text, flags=re.IGNORECASE)
        fssai = self._first_match(r"(?:fssai|lic(?:ense)?)\s*[:\-]?\s*(\d{14})", text, flags=re.IGNORECASE)

        return {
            "message": "ok",
            "product_name": self._extract_line_after_keyword(text, ["product", "name"]) or self._best_first_line(text),
            "weight": weight,
            "price": price,
            "ingredients": self._extract_line_after_keyword(text, ["ingredients"]),
            "fssai_number": fssai,
        }

    def _perform_ocr(self, image_path: str) -> dict[str, Any]:
        path = Path(image_path)
        if not path.exists():
            return {"ok": False, "message": f"File not found: {image_path}", "text": ""}

        if self._ocr_available is False:
            return {"ok": False, "message": "PaddleOCR not installed; OCR skipped.", "text": ""}

        try:
            if self.ocr is None:
                from paddleocr import PaddleOCR  # type: ignore

                self.ocr = PaddleOCR(use_angle_cls=True, lang="en")
                self._ocr_available = True

            raw = self.ocr.ocr(str(path), cls=True)
            lines: list[str] = []
            for page in raw or []:
                for item in page or []:
                    if len(item) >= 2 and isinstance(item[1], (list, tuple)) and item[1]:
                        lines.append(str(item[1][0]))
            text = "\n".join(lines).strip()
            return {"ok": True, "message": "ok", "text": text}
        except ImportError:
            self._ocr_available = False
            return {"ok": False, "message": "PaddleOCR not installed; OCR skipped.", "text": ""}
        except Exception as exc:
            return {"ok": False, "message": f"OCR failed: {exc}", "text": ""}

    def _extract_udyam_number(self, text: str) -> str | None:
        match = re.search(r"UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}", text.upper())
        return match.group(0) if match else None

    def _extract_products(self, text: str) -> list[str]:
        line = self._extract_line_after_keyword(text, ["products", "product", "goods", "services"])
        if not line:
            return []
        parts = [p.strip() for p in re.split(r"[,;/]| and ", line) if p.strip()]
        return parts[:8]

    def _extract_line_after_keyword(self, text: str, keywords: list[str]) -> str | None:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            lowered = line.lower()
            for keyword in keywords:
                if keyword in lowered:
                    if ":" in line:
                        value = line.split(":", 1)[1].strip()
                        if value:
                            return value
                    cleaned = re.sub(rf"(?i){re.escape(keyword)}", "", line).strip(" :-")
                    if cleaned:
                        return cleaned
        return None

    def _first_match(self, pattern: str, text: str, flags: int = 0) -> str | None:
        match = re.search(pattern, text, flags)
        if not match:
            return None
        if match.lastindex:
            return match.group(1)
        return match.group(0)

    def _best_first_line(self, text: str) -> str | None:
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned and len(cleaned) > 3:
                return cleaned
        return None


def extract_text(image_path: str) -> dict[str, str]:
    """Backward-compatible simple OCR entrypoint."""
    data = UdyamOCR().extract_from_certificate(image_path)
    return {
        "image_path": image_path,
        "text": "" if data.get("message") != "ok" else str(data),
        "status": data.get("message", "unknown"),
    }

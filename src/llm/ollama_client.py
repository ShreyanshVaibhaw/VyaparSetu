"""Ollama client with retry logic and demo fallbacks."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import requests


class LLMClient:
    """LLM client for Ollama with graceful fallback behaviour."""

    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 120

    def __init__(self, host: str = "localhost", port: int = 11434, model: str = "llama3.1:8b") -> None:
        self.host = host
        self.port = port
        self.model = model
        self.base_url = f"http://{host}:{port}"

    def health_check(self) -> bool:
        """Check whether Ollama is reachable."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.1) -> str:
        """Generate text with retries. Falls back to cached response when unavailable."""
        if not self.health_check():
            return self._fallback_response(prompt)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {"temperature": temperature},
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                data = response.json()
                text = str(data.get("response", "")).strip()
                if text:
                    return text
            except (requests.RequestException, ValueError):
                if attempt == self.MAX_RETRIES - 1:
                    break
                time.sleep(2**attempt)

        return self._fallback_response(prompt)

    def generate_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """Generate and parse JSON output. Retries parse failures up to 3 times."""
        last_error: Exception | None = None
        parse_prompt = prompt
        for attempt in range(self.MAX_RETRIES):
            try:
                raw = self.generate(parse_prompt, system=system, temperature=0.1)
                cleaned = self._strip_markdown(raw)
                return self._extract_json(cleaned)
            except (json.JSONDecodeError, ValueError) as err:
                last_error = err
                parse_prompt = (
                    f"{prompt}\n\nReturn strictly valid JSON only. "
                    "Do not add markdown, prose, or code fences."
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2**attempt)

        fallback = self._fallback_response(prompt)
        try:
            return self._extract_json(self._strip_markdown(fallback))
        except (json.JSONDecodeError, ValueError):
            if last_error:
                return {"error": str(last_error), "raw": fallback}
            return {"error": "Unable to parse JSON response", "raw": fallback}

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown fences and surrounding prose."""
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract first JSON object from text and parse it."""
        direct = text.strip()
        if direct.startswith("{") and direct.endswith("}"):
            return json.loads(direct)

        start = direct.find("{")
        end = direct.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in response")
        return json.loads(direct[start : end + 1])

    def _fallback_response(self, prompt: str) -> str:
        """Return cached demo responses when Ollama is unavailable."""
        p = prompt.lower()
        if "classify this mse" in p or "primary_category_l1" in p:
            return json.dumps(
                {
                    "primary_category_l1": "Food & Beverage",
                    "primary_category_l2": "Packaged Foods",
                    "secondary_categories": ["Grocery"],
                    "suggested_product_types": ["Pickles & Chutneys", "Spices & Masala"],
                    "confidence": 0.72,
                    "reasoning": "NIC code and products indicate packaged food business.",
                }
            )
        if "snp is recommended" in p or "explanation_regional" in p:
            return json.dumps(
                {
                    "explanation": "This SNP supports your product category and geography with strong seller success.",
                    "explanation_regional": "Yeh SNP aapke product aur shetra ke liye theek hai.",
                    "pros": ["Category fit", "Regional coverage", "Reasonable commission"],
                    "cons": ["Activation can take a few days"],
                    "tip": "Upload complete catalog attributes for faster activation.",
                }
            )
        if "registration_complete" in p or "extracted_fields" in p:
            return json.dumps(
                {
                    "extracted_fields": {
                        "udyam_number": None,
                        "products": [],
                        "price_info": None,
                        "delivery_area": None,
                        "language_preference": "hi",
                        "other_info": None,
                    },
                    "next_question": "Kripya apna Udyam number batayein.",
                    "registration_complete": False,
                }
            )
        if "product_name_en" in p or "ondc product catalog entry" in p:
            return json.dumps(
                {
                    "product_name_en": "Homemade Mango Pickle (500g)",
                    "product_name_regional": "घर का बना आम का अचार (500 ग्राम)",
                    "short_description": "Traditional mango pickle made with authentic spices.",
                    "long_description": "A handcrafted mango pickle made from raw mangoes and a traditional spice blend.",
                    "category_l1": "Food & Beverage",
                    "category_l2": "Packaged Foods",
                    "category_l3": "Pickles & Chutneys",
                    "hsn_code": "2001",
                    "suggested_price_range": "INR 180-260",
                    "attributes": {"net_quantity": "500g", "veg_nonveg": "veg"},
                    "tags": {"handmade": "yes"},
                    "seo_keywords": ["mango pickle", "homemade achaar", "traditional pickle"],
                }
            )
        return json.dumps({"message": "Demo response: Ollama unavailable, fallback used."})


class OllamaClient(LLMClient):
    """Backward-compatible alias for older imports."""

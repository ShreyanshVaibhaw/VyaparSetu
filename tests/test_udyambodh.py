"""Prompt 3 tests for UdyamBodh registration engine and conversation flow."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.common.models import MSEProfile
from src.udyambodh.business_classifier import BusinessClassifier
from src.udyambodh.gst_validator import GSTValidator
from src.udyambodh.registration_engine import RegistrationEngine
from src.udyambodh.udyam_fetcher import UdyamFetcher, fetch_udyam_record
from src.voice.bhashini_client import MockBhashiniClient
from src.voice.conversation_engine import ConversationEngine


class FakeLLMClient:
    """Fake LLM for classifier + conversation extraction tests."""

    def generate_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        text = prompt.lower()
        if "extract registration data from what they say" in text:
            latest = self._extract_latest_message(prompt)
            return {"extracted_fields": self._extract_fields_from_latest(latest), "next_question": "", "registration_complete": False}
        if "pickl" in text or "achaar" in text or "papad" in text:
            return {
                "primary_category_l1": "Food & Beverage",
                "primary_category_l2": "Packaged Foods",
                "secondary_categories": ["Grocery"],
                "suggested_product_types": ["Pickles & Chutneys", "Ready-to-Eat"],
                "confidence": 0.86,
                "reasoning": "Product keywords indicate packaged food business.",
            }
        if "saree" in text or "textile" in text or "weaving" in text:
            return {
                "primary_category_l1": "Fashion",
                "primary_category_l2": "Women's Apparel",
                "secondary_categories": ["Handicrafts & Handloom"],
                "suggested_product_types": ["Saree", "Handloom Apparel"],
                "confidence": 0.83,
                "reasoning": "Textile and saree context strongly matches fashion categories.",
            }
        if "brass" in text or "metal" in text:
            return {
                "primary_category_l1": "Home & Kitchen",
                "primary_category_l2": "Home Decor",
                "secondary_categories": ["Handicrafts & Handloom"],
                "suggested_product_types": ["Brassware", "Decorative Items"],
                "confidence": 0.8,
                "reasoning": "Brass and utensils map to home and decor products.",
            }
        return {
            "primary_category_l1": "General",
            "primary_category_l2": "General",
            "secondary_categories": [],
            "suggested_product_types": [],
            "confidence": 0.55,
            "reasoning": "Insufficient details, generic category selected.",
        }

    def _extract_latest_message(self, prompt: str) -> str:
        match = re.search(r'MSE JUST SAID:\s*"(.*)"', prompt, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ""

    def _extract_fields_from_latest(self, message: str) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "udyam_number": None,
            "products": [],
            "price_info": None,
            "delivery_area": None,
            "language_preference": "hi",
            "other_info": None,
        }
        match = re.search(r"UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}", message.upper())
        if match:
            fields["udyam_number"] = match.group(0)
        if "," in message:
            fields["products"] = [p.strip() for p in message.replace("और", ",").split(",") if p.strip()]
        return fields


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _classifier() -> BusinessClassifier:
    root = _project_root()
    return BusinessClassifier(
        llm_client=FakeLLMClient(),
        nic_to_ondc_path=str(root / "data" / "ondc_taxonomy" / "nic_to_ondc.json"),
        categories_path=str(root / "data" / "ondc_taxonomy" / "categories.json"),
    )


def _sample_profiles() -> list[MSEProfile]:
    data_path = _project_root() / "data" / "mse_data" / "sample_udyam_records.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))
    return [MSEProfile(**r) for r in rows]


def _registration_engine() -> RegistrationEngine:
    fetcher = UdyamFetcher()
    gst = GSTValidator()
    classifier = _classifier()
    return RegistrationEngine(fetcher, gst, classifier)


def test_fetch_udyam_record_returns_number() -> None:
    """Ensure compatibility helper returns requested Udyam number key."""
    data = fetch_udyam_record("UDYAM-RJ-01-1234567")
    assert data["udyam_number"] == "UDYAM-RJ-01-1234567"


def test_udyam_number_validation_valid_invalid() -> None:
    """Validate accepted and rejected Udyam number formats."""
    fetcher = UdyamFetcher()
    assert fetcher.validate_udyam_number("UDYAM-RJ-01-1234567")[0] is True
    assert fetcher.validate_udyam_number("udyam-rj-01-1234567")[0] is True
    assert fetcher.validate_udyam_number("UDYAM-RJ-1-1234567")[0] is False
    assert fetcher.validate_udyam_number("INVALID-123")[0] is False


def test_mock_data_generation_for_different_state_codes() -> None:
    """Mock generation should reflect state code in resulting profile."""
    fetcher = UdyamFetcher()
    profile_rj = fetcher.fetch_by_udyam_number("UDYAM-RJ-91-7654321")
    profile_tn = fetcher.fetch_by_udyam_number("UDYAM-TN-91-7654322")
    assert profile_rj.state == "Rajasthan"
    assert profile_tn.state == "Tamil Nadu"
    assert profile_rj.nic_2digit
    assert profile_tn.products_services


def test_gst_validation_format_checking() -> None:
    """GST validator should parse valid IDs and reject malformed values."""
    validator = GSTValidator()
    valid = validator.validate_gstin("08ABCDE1234F1Z5")
    invalid = validator.validate_gstin("08ABCDE1234F1")
    assert valid["valid"] is True
    assert valid["state_code"] == "08"
    assert valid["state_name"] == "Rajasthan"
    assert invalid["valid"] is False


def test_auto_registration_pipeline_end_to_end() -> None:
    """End-to-end auto registration should produce TEAMRegistration."""
    reg_engine = _registration_engine()
    registration = reg_engine.auto_register("UDYAM-RJ-01-1234567", language="hi")
    assert registration.registration_id.startswith("TEAM-")
    assert registration.mse_udyam == "UDYAM-RJ-01-1234567"
    assert registration.product_categories
    assert reg_engine.get_registration_status(registration.registration_id) in {"Submitted", "Draft"}


def test_conversation_engine_five_turn_hindi_dialogue() -> None:
    """Simulate 5-turn Hindi registration conversation flow."""
    engine = ConversationEngine(
        llm_client=FakeLLMClient(),
        registration_engine=_registration_engine(),
        bhashini_client=MockBhashiniClient(),
    )
    state = engine.start_session(language="hi")
    assert state.current_step == "udyam_input"

    turns = [
        "नमस्ते",
        "मेरा उद्यम नंबर UDYAM-RJ-01-1234567 है",
        "आम का अचार, पापड़",
        "फूड और ग्रोसरी",
        "1",
    ]
    responses: list[str] = []
    for msg in turns:
        state, response = engine.process_message(state, msg)
        responses.append(response)

    assert len(responses) == 5
    assert state.current_step == "confirmation"
    assert "registration_status" in state.collected_data
    assert state.mse_udyam == "UDYAM-RJ-01-1234567"


def test_business_classification_for_five_mse_types() -> None:
    """Run hybrid classification on five distinct sample MSE profiles."""
    classifier = _classifier()
    for profile in _sample_profiles()[:5]:
        result = classifier.classify_hybrid(profile)
        assert result["primary_l1"]
        assert 0.0 <= float(result["confidence"]) <= 1.0


def test_nic_code_mapping_nic10_to_food_and_beverage() -> None:
    """NIC 10 should map to Food & Beverage."""
    classifier = _classifier()
    mapped = classifier.classify_from_nic("10")
    assert "Food & Beverage" in mapped


def test_hybrid_classifier_pickle_textile_brass() -> None:
    """Hybrid classifier should produce stable categories for core personas."""
    classifier = _classifier()
    profiles = _sample_profiles()

    pickle_maker = next(p for p in profiles if "Pickle" in " ".join(p.products_services))
    textile_weaver = next(p for p in profiles if p.nic_2digit == "13")
    brass_artisan = next(p for p in profiles if "Brass" in " ".join(p.products_services))

    pickle_result = classifier.classify_hybrid(pickle_maker)
    textile_result = classifier.classify_hybrid(textile_weaver)
    brass_result = classifier.classify_hybrid(brass_artisan)

    assert pickle_result["primary_l1"] in {"Food & Beverage", "Grocery"}
    assert textile_result["primary_l1"] in {"Fashion", "Handicrafts & Handloom"}
    assert brass_result["primary_l1"] in {"Home & Kitchen", "Handicrafts & Handloom", "Electronics"}


def test_edge_cases_no_product_description_and_unusual_nic() -> None:
    """Classifier should stay robust for missing product data and unusual NIC."""
    classifier = _classifier()
    profile = _sample_profiles()[0]
    no_products = profile.model_copy(update={"products_services": []})
    weird_nic = profile.model_copy(update={"nic_2digit": "99", "nic_description": "Unusual NIC"})
    assert classifier.classify_hybrid(no_products)["primary_l1"]
    assert classifier.classify_from_nic(weird_nic.nic_2digit) == []

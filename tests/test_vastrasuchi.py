"""Prompt 4 tests for VastraSuchi AI catalog generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.common.models import MSEProfile, ProductGenerationRequest
from src.vastrasuchi.catalog_generator import CatalogGenerator, generate_catalog_entry
from src.vastrasuchi.hsn_mapper import HSNMapper
from src.vastrasuchi.ondc_formatter import ONDCFormatter
from src.vastrasuchi.pricing_engine import PricingEngine
from src.vastrasuchi.product_classifier import ProductClassifier


class FakeCatalogLLM:
    """Deterministic LLM responses for Prompt 4 scenarios."""

    def generate_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        text = prompt.lower()
        if "classify this product into ondc categories" in text:
            if "achaar" in text or "pickle" in text:
                return {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Pickles & Chutneys"}
            if "kanchipuram" in text or "saree" in text:
                return {"l1": "Fashion", "l2": "Women's Apparel", "l3": "Saree"}
            if "brass" in text and "vase" in text:
                return {"l1": "Home & Kitchen", "l2": "Home Decor", "l3": "Metal Crafts"}
            if "turmeric" in text or "spice" in text:
                return {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Spices & Masala"}
            if "leather" in text and "bag" in text:
                return {"l1": "Fashion", "l2": "Accessories", "l3": "Bags & Wallets"}
            return {"l1": "Grocery", "l2": "Basics", "l3": "General"}

        if "generate a professional ondc product catalog entry" in text:
            if "achaar" in text or "pickle" in text:
                return {
                    "product_name_en": "Homemade Mango Pickle (500g)",
                    "product_name_regional": "घर का बना आम का अचार (500 ग्राम)",
                    "short_description": "Traditional mango pickle made with desi ghee.",
                    "long_description": "Handmade mango pickle prepared using traditional spices and desi ghee.",
                    "attributes": {"ingredients": "mango, spices, desi ghee"},
                    "tags": {"handmade": "yes"},
                }
            if "kanchipuram" in text:
                return {
                    "product_name_en": "Pure Silk Kanchipuram Saree (6.5m)",
                    "product_name_regional": "காஞ்சிபுரம் பட்டு சேலை",
                    "short_description": "Traditional temple design silk saree with zari border.",
                    "long_description": "Authentic Kanchipuram silk saree featuring gold zari border and temple motifs.",
                    "attributes": {"material": "silk", "length": "6.5 meter"},
                    "tags": {"handmade": "yes"},
                }
            if "brass decorative flower vase" in text:
                return {
                    "product_name_en": "Hand-Engraved Brass Flower Vase (12 inch)",
                    "product_name_regional": "पीतल का नक्काशीदार फूलदान",
                    "short_description": "Polished brass vase with Mughal engraving.",
                    "long_description": "Decorative brass vase handcrafted with Mughal-inspired engraving and polished finish.",
                    "attributes": {"material": "brass", "height": "12 inch"},
                    "tags": {"handmade": "yes"},
                }
            if "turmeric" in text:
                return {
                    "product_name_en": "Organic Turmeric Powder (200g)",
                    "product_name_regional": "ஆர்கானிக் மஞ்சள் தூள் (200g)",
                    "short_description": "Certified organic turmeric from Wayanad farms.",
                    "long_description": "Fine-ground organic turmeric powder sourced from Wayanad, suitable for cooking and wellness.",
                    "attributes": {"organic_certification": "yes", "net_quantity": "200 gram"},
                    "tags": {"organic": "yes"},
                }
            if "leather laptop bag" in text:
                return {
                    "product_name_en": "Genuine Leather Laptop Bag (15 inch)",
                    "product_name_regional": "চামড়ার ল্যাপটপ ব্যাগ",
                    "short_description": "Handstitched brown leather laptop bag for 15-inch devices.",
                    "long_description": "Durable genuine leather laptop bag with handstitched construction and padded compartment.",
                    "attributes": {"material": "genuine leather", "size": "15 inch"},
                    "tags": {"handmade": "yes"},
                }
            return {
                "product_name_en": "MSE Product",
                "product_name_regional": None,
                "short_description": "ONDC-ready listing",
                "long_description": "Generated listing.",
                "attributes": {},
                "tags": {},
            }
        return {}


def _paths() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1] / "data"
    return {
        "categories": str(root / "ondc_taxonomy" / "categories.json"),
        "hsn": str(root / "ondc_taxonomy" / "hsn_mapping.json"),
        "schemas": str(root / "catalog_templates" / "attribute_schemas.json"),
    }


def _generator() -> tuple[CatalogGenerator, ONDCFormatter]:
    paths = _paths()
    llm = FakeCatalogLLM()
    classifier = ProductClassifier(paths["categories"], paths["hsn"], llm)
    mapper = HSNMapper(paths["hsn"])
    pricing = PricingEngine()
    generator = CatalogGenerator(llm, classifier, mapper, pricing)
    formatter = ONDCFormatter(paths["schemas"])
    return generator, formatter


def _profile(
    udyam_number: str,
    enterprise_name: str,
    nic_2digit: str,
    nic_5digit: str,
    nic_description: str,
    state: str,
    district: str,
    language: str,
    products: list[str],
) -> MSEProfile:
    return MSEProfile(
        udyam_number=udyam_number,
        enterprise_name=enterprise_name,
        owner_name="Owner",
        owner_gender="Female",
        enterprise_type="Micro",
        major_activity="Manufacturing",
        nic_2digit=nic_2digit,
        nic_5digit=nic_5digit,
        nic_description=nic_description,
        state=state,
        district=district,
        pincode="000000",
        address=f"{district}, {state}",
        mobile=None,
        email=None,
        date_of_incorporation=None,
        date_of_udyam=None,
        investment_plant=10.0,
        turnover=100.0,
        gstin=None,
        pan=None,
        social_category=None,
        is_women_owned=True,
        language_preference=language,
        products_services=products,
    )


@pytest.mark.parametrize(
    ("catalog_request", "profile", "expected"),
    [
        (
            ProductGenerationRequest(
                mse_udyam="UDYAM-RJ-08-0001543",
                product_description_raw="aam ka achaar, ghar ka bana hua, 500 gram ka dabba, desi ghee mein bana",
                product_images=[],
                language="hi",
                category_hint=None,
            ),
            _profile(
                "UDYAM-RJ-08-0001543",
                "Maru Mahila Foods",
                "10",
                "10795",
                "Manufacture of papads, appalam and similar foods",
                "Rajasthan",
                "Jodhpur",
                "hi",
                ["Pickle"],
            ),
            {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Pickles & Chutneys", "hsn": "2001"},
        ),
        (
            ProductGenerationRequest(
                mse_udyam="UDYAM-TN-33-0012451",
                product_description_raw="Pure silk Kanchipuram saree, 6.5 meter, with gold zari border, traditional temple design",
                product_images=[],
                language="ta",
                category_hint=None,
            ),
            _profile(
                "UDYAM-TN-33-0012451",
                "Kanchi Loom Collective",
                "13",
                "13121",
                "Weaving, manufacture of cotton textiles",
                "Tamil Nadu",
                "Kanchipuram",
                "ta",
                ["Saree"],
            ),
            {"l1_any": {"Fashion", "Handicrafts & Handloom"}, "l3_any": {"Saree", "Silk Products"}},
        ),
        (
            ProductGenerationRequest(
                mse_udyam="UDYAM-UP-09-0078901",
                product_description_raw="Brass decorative flower vase, 12 inch height, hand-engraved Mughal design, polished finish",
                product_images=[],
                language="en",
                category_hint=None,
            ),
            _profile(
                "UDYAM-UP-09-0078901",
                "Moradabad Brass Udyog",
                "25",
                "25931",
                "Manufacture of metal utensils",
                "Uttar Pradesh",
                "Moradabad",
                "en",
                ["Brassware"],
            ),
            {"l1": "Home & Kitchen", "l2": "Home Decor", "l3": "Metal Crafts"},
        ),
        (
            ProductGenerationRequest(
                mse_udyam="UDYAM-KL-32-0007321",
                product_description_raw="Organic turmeric powder, 200g pack, certified organic, from Wayanad farms",
                product_images=[],
                language="en",
                category_hint=None,
            ),
            _profile(
                "UDYAM-KL-32-0007321",
                "Malabar Spice Works",
                "10",
                "10792",
                "Manufacture of spices and condiments",
                "Kerala",
                "Wayanad",
                "en",
                ["Turmeric Powder"],
            ),
            {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Spices & Masala", "hsn": "0910"},
        ),
        (
            ProductGenerationRequest(
                mse_udyam="UDYAM-WB-19-0041122",
                product_description_raw="Genuine leather laptop bag, fits 15 inch laptop, brown color, handstitched",
                product_images=[],
                language="en",
                category_hint=None,
            ),
            _profile(
                "UDYAM-WB-19-0041122",
                "Kolkata Leather Line",
                "15",
                "15121",
                "Manufacture of luggage, handbags and similar articles",
                "West Bengal",
                "Kolkata",
                "en",
                ["Leather Bags"],
            ),
            {"l1": "Fashion", "l2": "Accessories", "l3": "Bags & Wallets"},
        ),
    ],
)
def test_prompt4_scenarios_generate_valid_ondc_items(
    catalog_request: ProductGenerationRequest,
    profile: MSEProfile,
    expected: dict[str, Any],
) -> None:
    """All 5 Prompt 4 scenarios should create complete, valid ONDC items."""
    generator, formatter = _generator()
    item = generator.generate_catalog_item(catalog_request, profile)
    formatted = formatter.format_catalog_item(item)
    validation = formatter.validate_catalog(formatted)

    assert item.product_name_en
    assert item.short_description
    assert item.long_description
    assert item.hsn_code
    assert validation["valid"] is True

    if "l1" in expected:
        assert item.category_l1 == expected["l1"]
    if "l2" in expected:
        assert item.category_l2 == expected["l2"]
    if "l3" in expected:
        assert item.category_l3 == expected["l3"]
    if "hsn" in expected:
        assert item.hsn_code == expected["hsn"]
    if "l1_any" in expected:
        assert item.category_l1 in expected["l1_any"]
    if "l3_any" in expected:
        assert item.category_l3 in expected["l3_any"]


def test_generate_catalog_entry_status_draft() -> None:
    """Backward-compatible helper should remain unchanged."""
    item = generate_catalog_entry("Test", "Desc")
    assert item["status"] == "draft"

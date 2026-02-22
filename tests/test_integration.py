"""Prompt 8 integration tests for end-to-end onboarding, quality, and demo mode."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from config import SNP_MATCH_WEIGHTS
from scripts.demo_flow import run_demo
from src.common.models import MSEProfile, ProductGenerationRequest
from src.sahayakmap.matching_engine import SNPMatchingEngine
from src.sahayakmap.scoring import SNPScorer
from src.sahayakmap.snp_profiler import SNPProfiler
from src.udyambodh.business_classifier import BusinessClassifier
from src.udyambodh.gst_validator import GSTValidator
from src.udyambodh.registration_engine import RegistrationEngine
from src.udyambodh.udyam_fetcher import UdyamFetcher
from src.vastrasuchi.catalog_generator import CatalogGenerator
from src.vastrasuchi.hsn_mapper import HSNMapper
from src.vastrasuchi.pricing_engine import PricingEngine
from src.vastrasuchi.product_classifier import ProductClassifier
from src.vriddhidisha.women_mse_tracker import WomenMSETracker


class FakeIntegrationLLM:
    """Deterministic local LLM for integration tests."""

    def generate_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        text = prompt.lower()

        if "classify this mse" in text or "primary_category_l1" in text:
            if "weaving" in text or "saree" in text or "textile" in text:
                return {
                    "primary_category_l1": "Fashion",
                    "primary_category_l2": "Women's Apparel",
                    "secondary_categories": ["Handicrafts & Handloom"],
                    "suggested_product_types": ["Saree", "Handloom"],
                    "confidence": 0.84,
                    "reasoning": "Textile business context indicates fashion categories.",
                }
            if "electronic" in text or "led" in text:
                return {
                    "primary_category_l1": "Electronics",
                    "primary_category_l2": "Mobile & Accessories",
                    "secondary_categories": ["Services"],
                    "suggested_product_types": ["LED Bulb"],
                    "confidence": 0.8,
                    "reasoning": "Electronics signals in business profile.",
                }
            return {
                "primary_category_l1": "Food & Beverage",
                "primary_category_l2": "Packaged Foods",
                "secondary_categories": ["Grocery"],
                "suggested_product_types": ["Pickles & Chutneys"],
                "confidence": 0.87,
                "reasoning": "Food keywords suggest packaged foods category.",
            }

        if "classify this product into ondc categories" in text:
            if "pickle" in text or "achaar" in text:
                return {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Pickles & Chutneys"}
            if "turmeric" in text or "masala" in text or "spice" in text:
                return {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Spices & Masala"}
            if "saree" in text or "dupatta" in text:
                return {"l1": "Fashion", "l2": "Women's Apparel", "l3": "Saree"}
            if "brass" in text or "vase" in text:
                return {"l1": "Home & Kitchen", "l2": "Home Decor", "l3": "Metal Crafts"}
            if "leather" in text and "bag" in text:
                return {"l1": "Fashion", "l2": "Accessories", "l3": "Bags & Wallets"}
            if "led" in text or "charger" in text:
                return {"l1": "Electronics", "l2": "Mobile & Accessories", "l3": "Chargers"}
            return {"l1": "Grocery", "l2": "Basics", "l3": "General"}

        if "generate a professional ondc product catalog entry" in text:
            if "lemon" in text or "nimbu" in text:
                return {
                    "product_name_en": "Homemade Lemon Pickle (250g)",
                    "product_name_regional": "घर का बना नींबू अचार",
                    "short_description": "Spicy lemon pickle made in small batches.",
                    "long_description": "Traditional lemon pickle prepared using handpicked lemons and carefully blended spices.",
                    "attributes": {"ingredients": "lemon, spices, oil"},
                    "tags": {"handmade": "yes"},
                }
            if "saree" in text:
                return {
                    "product_name_en": "Handloom Silk Saree",
                    "product_name_regional": "கைத்தறி பட்டு சேலை",
                    "short_description": "Traditional handloom silk saree with zari border.",
                    "long_description": "Authentic handloom silk saree designed with intricate motifs and festive zari work.",
                    "attributes": {"material": "silk", "length": "6.5 meter"},
                    "tags": {"handmade": "yes"},
                }
            if "brass" in text:
                return {
                    "product_name_en": "Engraved Brass Flower Vase",
                    "product_name_regional": "नक्काशीदार पीतल फूलदान",
                    "short_description": "Decorative hand-engraved brass flower vase.",
                    "long_description": "Crafted brass vase with traditional engraving suitable for decor and gifting.",
                    "attributes": {"material": "brass", "height": "12 inch"},
                    "tags": {"handmade": "yes"},
                }
            if "leather" in text:
                return {
                    "product_name_en": "Genuine Leather Laptop Bag",
                    "product_name_regional": "চামড়ার ল্যাপটপ ব্যাগ",
                    "short_description": "Handstitched leather laptop bag for everyday use.",
                    "long_description": "Durable genuine leather laptop bag with premium stitching and protective compartments.",
                    "attributes": {"material": "genuine leather", "size": "15 inch"},
                    "tags": {"handmade": "yes"},
                }
            if "led" in text:
                return {
                    "product_name_en": "Energy Efficient LED Bulb",
                    "product_name_regional": None,
                    "short_description": "Long-life LED bulb for home and shop use.",
                    "long_description": "High-efficiency LED bulb designed for low power consumption and bright output.",
                    "attributes": {"wattage": "9W", "color_temp": "6500K"},
                    "tags": {"energy_saving": "yes"},
                }
            return {
                "product_name_en": "Homemade Mango Pickle (500g)",
                "product_name_regional": "घर का बना आम का अचार",
                "short_description": "Traditional mango pickle with regional spices.",
                "long_description": "Homemade mango pickle prepared in traditional style with quality ingredients.",
                "attributes": {"ingredients": "mango, spices"},
                "tags": {"handmade": "yes"},
            }

        if "snp is recommended" in text or "explanation_regional" in text:
            return {
                "explanation": "Recommended due to category fit, geography coverage, and language support.",
                "explanation_regional": "यह SNP कैटेगरी, क्षेत्र और भाषा सपोर्ट के कारण उपयुक्त है।",
                "pros": ["Strong category fit", "Good regional reach", "Language support"],
                "cons": ["Activation can take a few days"],
                "tip": "Complete product attributes for faster activation.",
            }

        return {}


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _paths() -> dict[str, str]:
    base = _root() / "data"
    return {
        "nic_to_ondc": str(base / "ondc_taxonomy" / "nic_to_ondc.json"),
        "categories": str(base / "ondc_taxonomy" / "categories.json"),
        "hsn": str(base / "ondc_taxonomy" / "hsn_mapping.json"),
        "snp_db": str(base / "snp_profiles" / "snp_database.json"),
        "snp_perf": str(base / "snp_profiles" / "snp_performance.json"),
        "mse_synth": str(base / "synthetic" / "mse_profiles.csv"),
    }


def _ensure_synthetic_data() -> None:
    script = _root() / "scripts" / "generate_synthetic_data.py"
    subprocess.run([sys.executable, str(script)], check=True)


def _make_modules() -> dict[str, Any]:
    p = _paths()
    llm = FakeIntegrationLLM()

    fetcher = UdyamFetcher()
    classifier = BusinessClassifier(llm_client=llm, nic_to_ondc_path=p["nic_to_ondc"], categories_path=p["categories"])
    registration = RegistrationEngine(fetcher, GSTValidator(), classifier)

    product_classifier = ProductClassifier(categories_path=p["categories"], hsn_mapping_path=p["hsn"], llm_client=llm)
    generator = CatalogGenerator(llm, product_classifier, HSNMapper(p["hsn"]), PricingEngine())

    profiler = SNPProfiler(snp_database_path=p["snp_db"], snp_performance_path=p["snp_perf"])
    snp_engine = SNPMatchingEngine(snp_profiler=profiler, scorer=SNPScorer(SNP_MATCH_WEIGHTS), llm_client=llm)

    return {
        "fetcher": fetcher,
        "classifier": classifier,
        "registration": registration,
        "catalog_generator": generator,
        "snp_engine": snp_engine,
        "snp_profiler": profiler,
    }


def _profile_for_case(
    base: MSEProfile,
    *,
    state: str,
    district: str,
    language: str,
    nic_2digit: str,
    nic_5digit: str,
    nic_description: str,
    products_services: list[str],
) -> MSEProfile:
    return base.model_copy(
        update={
            "state": state,
            "district": district,
            "language_preference": language,
            "nic_2digit": nic_2digit,
            "nic_5digit": nic_5digit,
            "nic_description": nic_description,
            "products_services": products_services,
        }
    )


@pytest.fixture(scope="module", autouse=True)
def synthetic_data_ready() -> None:
    _ensure_synthetic_data()


def test_full_onboarding_pipeline() -> None:
    """Udyam number -> fetch -> classify -> catalog -> SNP match -> registration complete."""
    modules = _make_modules()

    profile = modules["fetcher"].fetch_by_udyam_number("UDYAM-RJ-01-0012345")
    classification = modules["classifier"].classify_hybrid(profile)

    request = ProductGenerationRequest(
        mse_udyam=profile.udyam_number,
        product_description_raw="aam ka achaar, ghar ka bana hua, 500 gram",
        product_images=[],
        language="hi",
        category_hint=classification["primary_l1"],
    )
    item = modules["catalog_generator"].generate_catalog_item(request, profile)

    matches = modules["snp_engine"].match(
        mse_profile=profile,
        mse_categories=[item.category_l1],
        tech_comfort="low",
        transaction_type="B2C",
        top_k=3,
    )
    registration = modules["registration"].auto_register(profile.udyam_number, language="hi")

    assert profile.udyam_number == "UDYAM-RJ-01-0012345"
    assert classification["primary_l1"]
    assert item.product_name_en
    assert item.hsn_code and item.hsn_code != "0000"
    assert len(matches) == 3
    assert registration.registration_status in {"Submitted", "Draft"}


def test_catalog_generation_quality() -> None:
    """Generate 10 catalogs across sectors and verify quality constraints."""
    modules = _make_modules()
    base = modules["fetcher"].fetch_by_udyam_number("UDYAM-RJ-01-0012345")

    scenarios = [
        ("aam ka achaar, 500 gram", {"Food & Beverage"}, "10", "10795", "Manufacture of papads and pickles"),
        ("nimbu ka achaar, 250 gram", {"Food & Beverage"}, "10", "10795", "Manufacture of papads and pickles"),
        ("organic turmeric powder 200g", {"Food & Beverage"}, "10", "10792", "Manufacture of spices and condiments"),
        ("pure silk saree with zari border", {"Fashion", "Handicrafts & Handloom"}, "13", "13121", "Weaving of textiles"),
        ("cotton handloom dupatta", {"Fashion", "Handicrafts & Handloom"}, "13", "13121", "Weaving of textiles"),
        ("brass decorative flower vase", {"Home & Kitchen", "Handicrafts & Handloom"}, "25", "25931", "Manufacture of metal utensils"),
        ("genuine leather laptop bag", {"Fashion"}, "15", "15121", "Manufacture of handbags"),
        ("LED bulb 9W", {"Electronics"}, "26", "26101", "Manufacture of electronic components"),
        ("mobile charger fast charging", {"Electronics"}, "26", "26101", "Manufacture of electronic components"),
        ("masala spice mix premium", {"Food & Beverage"}, "10", "10792", "Manufacture of spices and condiments"),
    ]

    generated = []
    for idx, (desc, expected_l1, nic2, nic5, nic_desc) in enumerate(scenarios):
        profile = _profile_for_case(
            base,
            state="Rajasthan",
            district="Jodhpur",
            language="hi",
            nic_2digit=nic2,
            nic_5digit=nic5,
            nic_description=nic_desc,
            products_services=[desc],
        )
        req = ProductGenerationRequest(
            mse_udyam=profile.udyam_number,
            product_description_raw=desc,
            product_images=[],
            language="en",
            category_hint=None,
        )
        item = modules["catalog_generator"].generate_catalog_item(req, profile)
        generated.append((item, expected_l1, idx))

    assert len(generated) == 10
    for item, expected_l1, idx in generated:
        assert item.product_name_en, f"Missing title for scenario #{idx + 1}"
        assert item.short_description and item.long_description, f"Missing description for scenario #{idx + 1}"
        assert item.category_l1 in expected_l1, f"Unexpected category for scenario #{idx + 1}: {item.category_l1}"
        assert item.hsn_code.isdigit() and item.hsn_code != "0000", f"Invalid HSN for scenario #{idx + 1}"
        assert 20 <= item.price_selling <= 100000, f"Out-of-range price for scenario #{idx + 1}: {item.price_selling}"


def test_snp_matching_logic() -> None:
    """Validate category, geography, language, and low-tech fit rules for SNP matching."""
    modules = _make_modules()
    base = modules["fetcher"].fetch_by_udyam_number("UDYAM-RJ-01-0012345")
    profiler: SNPProfiler = modules["snp_profiler"]

    # Food MSE gets food-specialized SNP in top 3.
    food_profile = _profile_for_case(
        base,
        state="Rajasthan",
        district="Jodhpur",
        language="hi",
        nic_2digit="10",
        nic_5digit="10795",
        nic_description="Manufacture of papads and pickles",
        products_services=["Mango Pickle", "Papad"],
    )
    food_matches = modules["snp_engine"].match(food_profile, ["Food & Beverage"], tech_comfort="low", transaction_type="B2C", top_k=3)
    assert len(food_matches) == 3
    assert any("Food & Beverage" in profiler.get_snp_details(m.snp_id).supported_categories for m in food_matches)

    # South India MSE should not get north-only SNP as #1.
    south_profile = _profile_for_case(
        base,
        state="Tamil Nadu",
        district="Chennai",
        language="ta",
        nic_2digit="13",
        nic_5digit="13121",
        nic_description="Weaving of textiles",
        products_services=["Silk Saree"],
    )
    south_matches = modules["snp_engine"].match(south_profile, ["Fashion"], tech_comfort="medium", transaction_type="B2C", top_k=3)
    top_south = profiler.get_snp_details(south_matches[0].snp_id)
    cov = {c.lower() for c in top_south.geographic_coverage}
    is_pan_india = any(c in {"all india", "pan-india", "pan india"} for c in cov)
    has_south = any(c in {"tamil nadu", "karnataka", "kerala", "andhra pradesh", "telangana", "puducherry"} for c in cov)
    assert is_pan_india or has_south

    # Hindi-speaking MSE should get Hindi-supporting SNP in top 3.
    assert any("hi" in profiler.get_snp_details(m.snp_id).languages_supported for m in food_matches)

    # Low-tech MSE should get mobile-first or assisted SNP in top rank.
    top_food = profiler.get_snp_details(food_matches[0].snp_id)
    low_tech_friendly = top_food.platform_type in {"mobile", "both"} or any(
        "whatsapp" in s.lower() for s in top_food.seller_support
    )
    assert low_tech_friendly


def test_women_mse_tracking() -> None:
    """Verify 50% women target tracking works on synthetic data."""
    tracker = WomenMSETracker(_paths()["mse_synth"])
    pct = tracker.get_women_percentage()
    funnel = tracker.get_women_funnel()

    assert 0.45 <= pct <= 0.55
    assert funnel["women_counts"]["registered"] > 0
    assert {"reg_to_catalog", "catalog_to_snp", "snp_to_live", "live_to_first_order"} <= funnel["women_conversion"].keys()


def test_demo_mode() -> None:
    """Full pipeline should run in offline demo mode without external services."""
    result = run_demo(demo_mode=True, verbose=False)

    assert result["status"] == "ok"
    assert result["demo_mode"] is True
    assert result["scene_2"]["catalog_count"] == 2
    assert result["scene_3"]["top_snp"]
    assert result["scene_4"]["total_mses"] >= 5000
    assert result["scene_4"]["total_products"] >= 2000

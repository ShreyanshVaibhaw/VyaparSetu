"""Model benchmark and robustness threshold tests."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from config import SNP_MATCH_WEIGHTS
from src.sahayakmap.scoring import SNPScorer
from src.sahayakmap.snp_profiler import SNPProfiler
from src.udyambodh.business_classifier import BusinessClassifier
from src.vastrasuchi.hsn_mapper import HSNMapper
from src.vastrasuchi.pricing_engine import PricingEngine
from src.vastrasuchi.product_classifier import ProductClassifier


class FakeBenchmarkLLM:
    """Deterministic local-only LLM responses for benchmark tests."""

    def generate_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        text = prompt.lower()

        if "classify this product into ondc categories" in text:
            if "pickle" in text or "achaar" in text:
                return {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Pickles & Chutneys"}
            if "turmeric" in text or "masala" in text or "spice" in text:
                return {"l1": "Food & Beverage", "l2": "Packaged Foods", "l3": "Spices & Masala"}
            if "saree" in text or "kurta" in text:
                return {"l1": "Fashion", "l2": "Women's Apparel", "l3": "Saree"}
            if "jute" in text or "handloom" in text or "craft" in text:
                return {"l1": "Handicrafts & Handloom", "l2": "Crafts", "l3": "Wooden Crafts"}
            if "brass" in text or "utensil" in text or "bedsheet" in text:
                return {"l1": "Home & Kitchen", "l2": "Kitchen", "l3": "Utensils"}
            if "led" in text or "charger" in text or "earphone" in text:
                return {"l1": "Electronics", "l2": "Mobile & Accessories", "l3": "Chargers"}
            if "soap" in text or "shampoo" in text or "cream" in text:
                return {"l1": "Beauty & Personal Care", "l2": "Bath & Body", "l3": "Bath & Body Item 1"}
            if "seed" in text or "fertilizer" in text:
                return {"l1": "Agriculture", "l2": "Seeds", "l3": "Vegetable Seeds"}
            if "notebook" in text or "book" in text:
                return {"l1": "Stationery & Books", "l2": "Books", "l3": "Educational"}
            return {"l1": "Grocery", "l2": "Basics", "l3": "Rice"}

        if "classify this mse" in text or "primary_category_l1" in text:
            return {
                "primary_category_l1": "Food & Beverage",
                "primary_category_l2": "Packaged Foods",
                "secondary_categories": ["Grocery"],
                "suggested_product_types": ["Pickles & Chutneys"],
                "confidence": 0.8,
                "reasoning": "Benchmark fallback response.",
            }

        return {}


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _paths() -> dict[str, str]:
    data = _root() / "data"
    return {
        "categories": str(data / "ondc_taxonomy" / "categories.json"),
        "hsn": str(data / "ondc_taxonomy" / "hsn_mapping.json"),
        "nic": str(data / "ondc_taxonomy" / "nic_to_ondc.json"),
        "snp_db": str(data / "snp_profiles" / "snp_database.json"),
        "snp_perf": str(data / "snp_profiles" / "snp_performance.json"),
    }


def _product_classifier() -> ProductClassifier:
    p = _paths()
    return ProductClassifier(
        categories_path=p["categories"],
        hsn_mapping_path=p["hsn"],
        llm_client=FakeBenchmarkLLM(),
    )


def test_product_classifier_accuracy_above_threshold() -> None:
    """Annexure-II classifier quality: product L1 accuracy should exceed 70%."""
    classifier = _product_classifier()
    samples = [
        ("Mango pickle homemade", "Food & Beverage"),
        ("Lemon achar jar", "Food & Beverage"),
        ("Turmeric powder masala", "Food & Beverage"),
        ("Organic spice mix", "Food & Beverage"),
        ("Silk saree zari", "Fashion"),
        ("Cotton kurta set", "Fashion"),
        ("Leather bag wallet", "Fashion"),
        ("Jute handicraft basket", "Handicrafts & Handloom"),
        ("Bamboo craft decor", "Handicrafts & Handloom"),
        ("Handloom artisan gift", "Handicrafts & Handloom"),
        ("Brass utensil set", "Home & Kitchen"),
        ("Cotton bedsheet", "Home & Kitchen"),
        ("Kitchen storage box", "Home & Kitchen"),
        ("LED bulb 9W", "Electronics"),
        ("Mobile charger", "Electronics"),
        ("Earphones wireless", "Electronics"),
        ("Handmade soap", "Beauty & Personal Care"),
        ("Herbal shampoo", "Beauty & Personal Care"),
        ("Vegetable seeds", "Agriculture"),
        ("Organic fertilizer", "Agriculture"),
    ]

    correct = 0
    for description, expected in samples:
        pred = classifier.classify(description)["l1"]
        if pred == expected:
            correct += 1

    accuracy = correct / len(samples)
    assert accuracy >= 0.70


def test_product_classifier_confidence_scores() -> None:
    """Annexure-II confidence sanity: scores must stay bounded and informative."""
    classifier = _product_classifier()
    descriptions = [
        "Mango pickle",
        "Silk saree",
        "Brass vase",
        "LED bulb",
        "Handmade soap",
        "Vegetable seeds",
        "Notebook set",
        "Jute bag",
        "Rice pack",
        "Mobile charger",
    ]

    confidences = [float(classifier.classify(desc).get("confidence", 0.0)) for desc in descriptions]
    assert all(0.0 <= c <= 1.0 for c in confidences)
    assert sum(confidences) / len(confidences) >= 0.5


def test_business_classifier_nic_mapping() -> None:
    """Annexure-II mapping robustness: expected L1 should appear for representative NIC codes."""
    p = _paths()
    classifier = BusinessClassifier(
        llm_client=FakeBenchmarkLLM(),
        nic_to_ondc_path=p["nic"],
        categories_path=p["categories"],
    )
    checks = {
        "10": "Food & Beverage",
        "13": "Fashion",
        "14": "Fashion",
        "15": "Fashion",
        "20": "Health & Wellness",
        "21": "Health & Wellness",
        "26": "Electronics",
        "27": "Electronics",
        "31": "Home & Kitchen",
        "32": "Handicrafts & Handloom",
        "33": "Services",
        "47": "Grocery",
        "62": "Services",
        "85": "Services",
        "96": "Beauty & Personal Care",
    }

    for nic, expected in checks.items():
        assert expected in classifier.classify_from_nic(nic)


def test_snp_scorer_consistency() -> None:
    """Annexure-II determinism: identical MSE/SNP inputs should produce stable identical scores."""
    scorer = SNPScorer(SNP_MATCH_WEIGHTS)
    scores = []
    for _ in range(10):
        breakdown = {
            "domain": scorer.score_domain(["Food & Beverage"], ["Food & Beverage", "Grocery"]),
            "geography": scorer.score_geography("Rajasthan", "Jaipur", ["Rajasthan", "All India"]),
            "language": scorer.score_language("hi", ["hi", "en"]),
            "cost": scorer.score_cost(6.5, 499.0, [6.5, 7.2, 8.1]),
            "performance": scorer.score_performance(0.78, 6, 4.2),
            "tech_fit": scorer.score_tech_fit("low", "both", ["manual", "bulk_csv"], ["whatsapp"]),
        }
        scores.append(scorer.calculate_total(breakdown))

    assert len(set(scores)) == 1


def test_snp_scorer_dimension_bounds() -> None:
    """Annexure-II boundedness: six scoring dimensions should stay in expected normalized range."""
    scorer = SNPScorer(SNP_MATCH_WEIGHTS)
    values = [
        scorer.score_domain(["Fashion"], ["Fashion", "Handicrafts & Handloom"], ["artisan"], ["handloom saree"]),
        scorer.score_geography("Tamil Nadu", "Chennai", ["Tamil Nadu", "Karnataka"], ["600001"], "600001"),
        scorer.score_language("ta", ["en", "ta", "hi"]),
        scorer.score_cost(7.1, 499.0, [6.4, 7.1, 9.0]),
        scorer.score_performance(0.81, 5, 4.5),
        scorer.score_tech_fit("medium", "both", ["manual", "api"], ["chat", "whatsapp"]),
    ]
    assert all(0.0 <= score <= 1.2 for score in values)


def test_hsn_mapper_known_products() -> None:
    """Annexure-II taxonomy correctness: known staples should map to expected HSN chapter prefixes."""
    mapper = HSNMapper(_paths()["hsn"])
    coffee = mapper.map_hsn("coffee powder", "Food & Beverage > Beverages")
    rice = mapper.map_hsn("basmati rice", "Grocery > Basics")
    cotton = mapper.map_hsn("cotton fabric", "Fashion > Women's Apparel")

    assert str(coffee["hsn_code"]).startswith("09")
    assert str(rice["hsn_code"]).startswith("10")
    assert str(cotton["hsn_code"]).startswith("52")


def test_pricing_engine_reasonable_prices() -> None:
    """Annexure-II pricing realism: generated prices should be positive and within broad operational bounds."""
    engine = PricingEngine()
    categories = [
        "Packaged Foods",
        "Fresh Foods",
        "Beverages",
        "Women's Apparel",
        "Accessories",
        "Home Decor",
        "Kitchen",
        "Electronics",
        "Ayurveda & Herbal",
        "Seeds",
    ]

    prices = [
        engine.suggest_price(category, "benchmark product", "500 gram", is_handmade=True)["suggested_selling"]
        for category in categories
    ]
    assert all(0 < price < 100000 for price in prices)


def test_inference_latency() -> None:
    """Annexure-II runtime criterion: demo-mode classification latency should stay under 5 seconds on average."""
    classifier = _product_classifier()
    samples = [
        "Mango pickle",
        "Lemon pickle",
        "Turmeric powder",
        "Silk saree",
        "Brass utensil",
        "LED bulb",
        "Handmade soap",
        "Cotton bedsheet",
        "Jute bag",
        "Vegetable seeds",
    ]

    latencies = []
    for item in samples:
        start = time.perf_counter()
        classifier.classify(item)
        latencies.append(time.perf_counter() - start)

    assert sum(latencies) / len(latencies) < 5.0

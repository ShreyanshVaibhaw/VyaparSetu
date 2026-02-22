"""Prompt 5 tests for SahayakMap SNP matching engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import SNP_MATCH_WEIGHTS
from src.common.models import MSEProfile
from src.sahayakmap.explainer import MatchExplainer
from src.sahayakmap.matching_engine import SNPMatchingEngine
from src.sahayakmap.scoring import SNPScorer, compute_match_score
from src.sahayakmap.snp_profiler import SNPProfiler


class FakeExplainLLM:
    """Deterministic explanation generator for tests."""

    def generate_json(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        return {
            "explanation": "SNP is recommended due to category fit, regional coverage, and language support.",
            "explanation_regional": "यह SNP कैटेगरी, क्षेत्र और भाषा सपोर्ट के कारण उपयुक्त है।",
            "pros": ["Strong category support", "Good language support", "Competitive onboarding"],
            "cons": ["Activation may take a few days"],
            "tip": "Upload complete catalog for faster go-live.",
        }


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _engine() -> tuple[SNPMatchingEngine, SNPProfiler]:
    root = _root() / "data" / "snp_profiles"
    profiler = SNPProfiler(
        snp_database_path=str(root / "snp_database.json"),
        snp_performance_path=str(root / "snp_performance.json"),
    )
    scorer = SNPScorer(SNP_MATCH_WEIGHTS)
    engine = SNPMatchingEngine(profiler, scorer, FakeExplainLLM())
    return engine, profiler


def _mse(
    udyam_number: str,
    name: str,
    state: str,
    district: str,
    language: str,
    nic2: str,
    nic5: str,
    nic_desc: str,
    products: list[str],
    major_activity: str = "Manufacturing",
    women_owned: bool = False,
) -> MSEProfile:
    return MSEProfile(
        udyam_number=udyam_number,
        enterprise_name=name,
        owner_name="Owner",
        owner_gender="Female" if women_owned else "Male",
        enterprise_type="Micro",
        major_activity=major_activity,  # type: ignore[arg-type]
        nic_2digit=nic2,
        nic_5digit=nic5,
        nic_description=nic_desc,
        state=state,
        district=district,
        pincode="302001",
        address=f"{district}, {state}",
        mobile=None,
        email=None,
        date_of_incorporation=None,
        date_of_udyam=None,
        investment_plant=10.0,
        turnover=90.0,
        gstin=None,
        pan=None,
        social_category=None,
        is_women_owned=women_owned,
        language_preference=language,
        products_services=products,
    )


def test_compute_match_score_bounded() -> None:
    """Ensure score helper remains bounded."""
    score = compute_match_score(1, 1, 1, 1, 1, 1)
    assert 0 <= score <= 1


def test_prompt5_scenario_1_pickle_maker_jodhpur() -> None:
    """Food SNP + Rajasthan + Hindi + low-tech fit should rank in top 3."""
    engine, _ = _engine()
    profile = _mse(
        "UDYAM-RJ-08-0001543",
        "Maru Pickles",
        "Rajasthan",
        "Jodhpur",
        "hi",
        "10",
        "10795",
        "Manufacture of papads and pickles",
        ["Mango Pickle", "Papad"],
    )
    matches = engine.match(profile, mse_categories=["Food & Beverage"], tech_comfort="low", transaction_type="B2C", top_k=3)
    assert len(matches) == 3
    assert all(m.explanation for m in matches)
    assert any(m.domain_score >= 0.5 and m.language_score >= 0.5 and m.tech_fit_score >= 0.7 for m in matches)


def test_prompt5_scenario_2_silk_saree_kanchipuram() -> None:
    """Fashion/textile + Tamil support should appear in top matches."""
    engine, _ = _engine()
    profile = _mse(
        "UDYAM-TN-33-0012451",
        "Kanchi Loom",
        "Tamil Nadu",
        "Kanchipuram",
        "ta",
        "13",
        "13121",
        "Weaving of cotton/silk textiles",
        ["Silk Saree", "Temple Design Saree"],
    )
    matches = engine.match(profile, mse_categories=["Fashion", "Handicrafts & Handloom"], tech_comfort="medium", transaction_type="Both", top_k=3)
    assert len(matches) == 3
    assert any(m.domain_score >= 0.45 for m in matches)
    assert any(m.language_score >= 0.5 for m in matches)


def test_prompt5_scenario_3_electronics_repair_bangalore() -> None:
    """Services/electronics in Bangalore with high-tech comfort should prefer tech-capable SNPs."""
    engine, _ = _engine()
    profile = _mse(
        "UDYAM-KA-29-0019988",
        "Bangalore Repair Tech",
        "Karnataka",
        "Bengaluru Urban",
        "en",
        "95",
        "95210",
        "Repair of consumer electronics",
        ["Electronics Repair Service"],
        major_activity="Services",
    )
    matches = engine.match(profile, mse_categories=["Services", "Electronics"], tech_comfort="high", transaction_type="B2C", top_k=3)
    assert len(matches) == 3
    assert any(m.tech_fit_score >= 0.75 for m in matches)
    assert any(m.geography_score >= 0.3 for m in matches)


def test_prompt5_scenario_4_women_owned_papad_gujarat() -> None:
    """Low-tech Gujarati papad maker should get food SNP with language support."""
    engine, _ = _engine()
    profile = _mse(
        "UDYAM-GJ-24-0023432",
        "Hetal Papad Gruh",
        "Gujarat",
        "Ahmedabad",
        "gu",
        "10",
        "10795",
        "Manufacture of papads",
        ["Papad", "Fryums"],
        women_owned=True,
    )
    matches = engine.match(profile, mse_categories=["Food & Beverage"], tech_comfort="low", transaction_type="B2C", top_k=3)
    assert len(matches) == 3
    assert any(m.language_score >= 0.5 for m in matches)
    assert any(m.tech_fit_score >= 0.7 for m in matches)


def test_prompt5_scenario_5_handicraft_kashmir() -> None:
    """Kashmir handicraft seller should get handicraft-focused or pan-India support options."""
    engine, _ = _engine()
    profile = _mse(
        "UDYAM-JK-01-0007765",
        "Kashmir Papier Art",
        "Jammu and Kashmir",
        "Srinagar",
        "hi",
        "32",
        "32909",
        "Other manufacturing n.e.c.",
        ["Papier-mâché", "Handicraft Decor"],
    )
    matches = engine.match(profile, mse_categories=["Handicrafts & Handloom"], tech_comfort="medium", transaction_type="B2C", top_k=3)
    assert len(matches) == 3
    assert any(m.domain_score >= 0.4 for m in matches)
    assert any(m.language_score >= 0.5 for m in matches)


def test_compare_and_explainer_outputs() -> None:
    """Comparison table and explainer should return structured outputs."""
    engine, _ = _engine()
    profile = _mse(
        "UDYAM-RJ-08-0001543",
        "Maru Pickles",
        "Rajasthan",
        "Jodhpur",
        "hi",
        "10",
        "10795",
        "Manufacture of papads and pickles",
        ["Mango Pickle", "Papad"],
    )
    matches = engine.match(profile, mse_categories=["Food & Beverage"], tech_comfort="low", top_k=3)
    comparison = engine.compare_snps(matches)
    summary = engine.get_match_summary(matches)
    explainer = MatchExplainer(FakeExplainLLM())
    card = explainer.generate_comparison_card(matches)

    assert "comparison_table" in comparison and len(comparison["comparison_table"]) == 3
    assert summary.startswith("Recommended SNP:")
    assert "cards" in card and len(card["cards"]) == 3

"""Scoring logic for SNP matching."""

from __future__ import annotations

from typing import Any


class SNPScorer:
    """Compute six-dimensional SNP fit scores and weighted totals."""

    NEIGHBOR_STATES = {
        "rajasthan": {"gujarat", "haryana", "punjab", "madhya pradesh", "uttar pradesh", "delhi"},
        "tamil nadu": {"kerala", "karnataka", "andhra pradesh", "telangana", "puducherry"},
        "karnataka": {"kerala", "tamil nadu", "telangana", "andhra pradesh", "maharashtra", "goa"},
        "gujarat": {"rajasthan", "maharashtra", "madhya pradesh", "daman and diu"},
        "jammu and kashmir": {"ladakh", "himachal pradesh", "punjab"},
        "west bengal": {"bihar", "jharkhand", "odisha", "sikkim", "assam"},
    }

    def __init__(self, weights: dict[str, float]) -> None:
        self.weights = weights

    def score_domain(
        self,
        mse_categories: list[str],
        snp_categories: list[str],
        specialization_tags: list[str] | None = None,
        mse_product_types: list[str] | None = None,
    ) -> float:
        """Jaccard overlap with optional specialization bonus."""
        mse_set = {c.strip().lower() for c in mse_categories if c}
        snp_set = {c.strip().lower() for c in snp_categories if c}
        if not mse_set or not snp_set:
            base = 0.0
        else:
            base = len(mse_set & snp_set) / len(mse_set | snp_set)

        bonus = 0.0
        if specialization_tags and mse_product_types:
            tags = " ".join(t.lower() for t in specialization_tags)
            products = " ".join(p.lower() for p in mse_product_types)
            if any(token in tags for token in products.split() if len(token) > 3):
                bonus = 0.1
        return min(1.0, round(base + bonus, 4))

    def score_geography(
        self,
        mse_state: str,
        mse_district: str,
        snp_coverage: list[str],
        snp_pincodes: list[str] | None = None,
        mse_pincode: str | None = None,
    ) -> float:
        """State coverage score with pan-India and neighboring-state handling."""
        state = mse_state.strip().lower()
        coverage = {c.strip().lower() for c in snp_coverage if c}

        if state in coverage:
            score = 1.0
        elif any(c in {"all india", "pan-india", "pan india"} for c in coverage):
            score = 0.7
        else:
            neighbors = self.NEIGHBOR_STATES.get(state, set())
            score = 0.3 if neighbors.intersection(coverage) else 0.0

        if mse_pincode and snp_pincodes and mse_pincode in set(snp_pincodes):
            score += 0.1
        if mse_district and any(mse_district.lower() in c for c in coverage):
            score += 0.1
        return min(1.0, round(score, 4))

    def score_language(self, mse_language: str, snp_languages: list[str]) -> float:
        """Language compatibility score."""
        language = mse_language.strip().lower()
        langs = {l.strip().lower() for l in snp_languages if l}
        if language in langs:
            return 1.0
        if {"hi", "en"}.intersection(langs):
            return 0.5
        return 0.2

    def score_cost(
        self,
        snp_commission: float,
        snp_monthly_fee: float,
        all_snp_commissions: list[float],
    ) -> float:
        """Cost score using normalized commission and monthly-fee penalty."""
        commissions = [c for c in all_snp_commissions if c is not None]
        if not commissions:
            commission_score = 0.5
        else:
            min_c, max_c = min(commissions), max(commissions)
            if max_c == min_c:
                commission_score = 1.0
            else:
                commission_score = 1.0 - ((snp_commission - min_c) / (max_c - min_c))
        fee_penalty = 0.0 if snp_monthly_fee <= 0 else min(0.4, snp_monthly_fee / 2500.0)
        return max(0.0, min(1.0, round(commission_score - fee_penalty, 4)))

    def score_performance(
        self,
        snp_success_rate: float,
        snp_avg_activation_days: int,
        snp_rating: float,
    ) -> float:
        """Performance score: success + activation speed + rating."""
        success = max(0.0, min(1.0, float(snp_success_rate)))
        # Assume 1 day best, 30 days worst for normalization.
        activation_norm = 1.0 - max(0.0, min(1.0, (snp_avg_activation_days - 1) / 29.0))
        rating_norm = max(0.0, min(1.0, snp_rating / 5.0))
        score = 0.5 * success + 0.3 * activation_norm + 0.2 * rating_norm
        return round(score, 4)

    def score_tech_fit(
        self,
        mse_tech_comfort: str,
        snp_platform: str,
        snp_catalog_method: list[str],
        seller_support: list[str] | None = None,
    ) -> float:
        """Tech compatibility between MSE comfort and SNP platform complexity."""
        comfort = mse_tech_comfort.lower().strip()
        platform = snp_platform.lower().strip()
        methods = {m.lower() for m in snp_catalog_method}
        support = {s.lower() for s in (seller_support or [])}

        if comfort == "low":
            score = 0.9 if platform in {"mobile", "both"} else 0.5
            if "api" in methods and "manual" not in methods and "bulk_csv" not in methods:
                score -= 0.3
            if "whatsapp" in support:
                score += 0.1
        elif comfort == "high":
            score = 0.9 if "api" in methods or platform in {"web", "both"} else 0.6
        else:  # medium
            score = 0.8 if platform in {"both", "mobile"} else 0.65
            if "bulk_csv" in methods or "api" in methods:
                score += 0.05

        return max(0.0, min(1.0, round(score, 4)))

    def calculate_total(self, scores: dict[str, float]) -> float:
        """Weighted sum of domain/geography/language/cost/performance/tech_fit."""
        total = 0.0
        for key, weight in self.weights.items():
            total += weight * float(scores.get(key, 0.0))
        return max(0.0, min(1.0, round(total, 4)))


def compute_match_score(
    domain: float,
    geography: float,
    language: float,
    cost: float,
    performance: float,
    tech_fit: float,
) -> float:
    """Backward-compatible fixed-weight score helper."""
    score = (
        domain * 0.30
        + geography * 0.20
        + language * 0.15
        + cost * 0.15
        + performance * 0.10
        + tech_fit * 0.10
    )
    return max(0.0, min(round(score, 4), 1.0))

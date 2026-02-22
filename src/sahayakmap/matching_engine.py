"""SNP matching engine implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.common.models import MSEProfile, SNPMatch, SNPProfile
from src.llm.prompt_templates import SNP_EXPLANATION_TEMPLATE, SYSTEM_PROMPT_VYAPARSETU


class SNPMatchingEngine:
    """Find and rank best-fit SNPs for a given MSE."""

    def __init__(self, snp_profiler: Any, scorer: Any, llm_client: Any) -> None:
        self.profiler = snp_profiler
        self.scorer = scorer
        self.llm = llm_client

    def match(
        self,
        mse_profile: MSEProfile,
        mse_categories: list[str],
        tech_comfort: str = "medium",
        transaction_type: str = "B2C",
        top_k: int = 3,
    ) -> list[SNPMatch]:
        """Run full SNP ranking pipeline and return top K match objects."""
        all_snps = self.profiler.get_all_snps()
        team_snps = self.profiler.get_team_partner_snps()
        eligible_snps = team_snps if len(team_snps) >= top_k else all_snps

        filtered: list[SNPProfile] = []
        for snp in eligible_snps:
            domain_score = self.scorer.score_domain(
                mse_categories,
                snp.supported_categories,
                specialization_tags=snp.specialization_tags,
                mse_product_types=mse_profile.products_services,
            )
            if domain_score > 0:
                filtered.append(snp)

        if not filtered:
            filtered = eligible_snps

        commissions = [s.commission_rate for s in filtered]
        scored: list[tuple[SNPProfile, dict[str, float], float]] = []

        for snp in filtered:
            scores = {
                "domain": self.scorer.score_domain(
                    mse_categories,
                    snp.supported_categories,
                    specialization_tags=snp.specialization_tags,
                    mse_product_types=mse_profile.products_services,
                ),
                "geography": self.scorer.score_geography(
                    mse_profile.state,
                    mse_profile.district,
                    snp.geographic_coverage,
                    snp_pincodes=snp.pincode_coverage or [],
                    mse_pincode=mse_profile.pincode,
                ),
                "language": self.scorer.score_language(
                    mse_profile.language_preference,
                    snp.languages_supported,
                ),
                "cost": self.scorer.score_cost(
                    snp.commission_rate,
                    snp.monthly_fee,
                    commissions,
                ),
                "performance": self.scorer.score_performance(
                    snp.seller_success_rate,
                    snp.avg_activation_days,
                    snp.rating,
                ),
                "tech_fit": self.scorer.score_tech_fit(
                    tech_comfort,
                    snp.platform_type,
                    snp.catalog_upload_method,
                    seller_support=snp.seller_support,
                ),
            }
            total = self.scorer.calculate_total(scores)
            scored.append((snp, scores, total))

        scored.sort(key=lambda x: x[2], reverse=True)
        top = scored[: max(1, top_k)]

        matches: list[SNPMatch] = []
        for idx, (snp, scores, total) in enumerate(top, start=1):
            explanation_payload = self.explain_match(mse_profile, snp, scores)
            match = SNPMatch(
                match_id=f"MATCH-{uuid4().hex[:12].upper()}",
                mse_udyam=mse_profile.udyam_number,
                snp_id=snp.snp_id,
                snp_name=snp.name,
                overall_score=total,
                domain_score=scores["domain"],
                geography_score=scores["geography"],
                language_score=scores["language"],
                cost_score=scores["cost"],
                performance_score=scores["performance"],
                tech_fit_score=scores["tech_fit"],
                explanation=str(explanation_payload.get("explanation", "")),
                pros=[str(p) for p in explanation_payload.get("pros", [])][:3],
                cons=[str(c) for c in explanation_payload.get("cons", [])][:2],
                rank=idx,
                generated_at=datetime.now(timezone.utc),
            )
            matches.append(match)

        return matches

    def explain_match(
        self,
        mse_profile: MSEProfile,
        snp_profile: SNPProfile,
        scores: dict[str, float],
    ) -> dict[str, Any]:
        """Generate natural-language rationale for SNP recommendation."""
        prompt = SNP_EXPLANATION_TEMPLATE.format(
            mse_name=mse_profile.enterprise_name,
            district=mse_profile.district,
            state=mse_profile.state,
            products=", ".join(mse_profile.products_services),
            language=mse_profile.language_preference,
            snp_name=snp_profile.name,
            snp_specialization=", ".join(snp_profile.specialization_tags),
            snp_coverage=", ".join(snp_profile.geographic_coverage),
            commission=snp_profile.commission_rate,
            domain_score=round(scores.get("domain", 0.0), 2),
            geo_score=round(scores.get("geography", 0.0), 2),
            lang_score=round(scores.get("language", 0.0), 2),
            cost_score=round(scores.get("cost", 0.0), 2),
            perf_score=round(scores.get("performance", 0.0), 2),
        )
        try:
            data = self.llm.generate_json(prompt=prompt, system=SYSTEM_PROMPT_VYAPARSETU)
            if isinstance(data, dict) and data.get("explanation"):
                data.setdefault("pros", [])
                data.setdefault("cons", [])
                return data
        except Exception:
            pass

        return {
            "explanation": (
                f"{snp_profile.name} fits your category mix, supports your language, and "
                f"offers coverage in/near {mse_profile.state} with competitive cost."
            ),
            "pros": [
                f"Category coverage: {', '.join(snp_profile.supported_categories[:3])}",
                f"Language support: {', '.join(snp_profile.languages_supported[:3])}",
                f"Commission: {snp_profile.commission_rate:.1f}%",
            ],
            "cons": [f"Avg activation time: {snp_profile.avg_activation_days} days"],
            "tip": "Upload complete catalog attributes to improve onboarding speed.",
        }

    def compare_snps(self, matches: list[SNPMatch]) -> dict[str, Any]:
        """Build side-by-side comparison view for top recommendations."""
        table: list[dict[str, Any]] = []
        for m in matches:
            table.append(
                {
                    "rank": m.rank,
                    "snp_name": m.snp_name,
                    "overall_score": round(m.overall_score, 4),
                    "domain": round(m.domain_score, 3),
                    "geography": round(m.geography_score, 3),
                    "language": round(m.language_score, 3),
                    "cost": round(m.cost_score, 3),
                    "performance": round(m.performance_score, 3),
                    "tech_fit": round(m.tech_fit_score, 3),
                    "pros": m.pros,
                    "cons": m.cons,
                }
            )
        return {"comparison_table": table}

    def get_match_summary(self, matches: list[SNPMatch]) -> str:
        """Return one-paragraph recommendation summary."""
        if not matches:
            return "No suitable SNP matches found with current inputs."
        top = matches[0]
        return (
            f"Recommended SNP: {top.snp_name} (score {top.overall_score:.2f}). "
            f"It performs strongly on domain ({top.domain_score:.2f}) and geography "
            f"({top.geography_score:.2f}), with language support score {top.language_score:.2f}. "
            f"Alternative options are available in ranks 2 and 3."
        )


def match_snps(mse_profile: dict[str, Any], snp_profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backward-compatible lightweight ranker."""
    results: list[dict[str, Any]] = []
    for snp in snp_profiles:
        results.append({"snp": snp, "score": 0.65})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]

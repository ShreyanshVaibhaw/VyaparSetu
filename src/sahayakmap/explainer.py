"""Explanation utilities for SNP matching results."""

from __future__ import annotations

from typing import Any

from src.common.models import SNPMatch


class MatchExplainer:
    """Generate language-friendly SNP explanation outputs."""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def explain_in_language(self, match: SNPMatch, language: str) -> str:
        """Generate explanation in MSE's preferred language."""
        if language == "hi":
            return (
                f"{match.snp_name} आपके लिए उपयुक्त है क्योंकि इसका स्कोर {match.overall_score:.2f} है और "
                "यह आपके बिज़नेस कैटेगरी व क्षेत्र के लिए अच्छा सपोर्ट देता है।"
            )
        if language == "ta":
            return (
                f"{match.snp_name} உங்கள் வணிகத்திற்கு பொருத்தமானது. மொத்த மதிப்பெண் "
                f"{match.overall_score:.2f} மற்றும் நல்ல பகுதி/மொழி ஆதரவு உள்ளது."
            )
        if language == "gu":
            return (
                f"{match.snp_name} તમારા બિઝનેસ માટે યોગ્ય છે. કુલ સ્કોર {match.overall_score:.2f} છે "
                "અને કેટેગરી તથા વિસ્તાર માટે સારો સપોર્ટ આપે છે."
            )

        # English fallback
        return (
            f"{match.snp_name} is a strong fit (score {match.overall_score:.2f}) based on "
            f"domain ({match.domain_score:.2f}) and geography ({match.geography_score:.2f}) alignment."
        )

    def generate_comparison_card(self, matches: list[SNPMatch]) -> dict[str, Any]:
        """Return comparison cards for dashboard rendering."""
        cards = []
        for match in matches:
            cards.append(
                {
                    "snp_name": match.snp_name,
                    "score": round(match.overall_score, 4),
                    "pros": match.pros,
                    "cons": match.cons,
                    "best_for": self._best_for(match),
                    "commission": self._commission_hint(match.cost_score),
                    "delivery_area": self._delivery_hint(match.geography_score),
                }
            )
        return {"cards": cards}

    def _best_for(self, match: SNPMatch) -> str:
        if match.tech_fit_score > 0.8 and match.cost_score > 0.7:
            return "Low-tech sellers seeking affordable onboarding"
        if match.domain_score > 0.8:
            return "Category-specialized sellers"
        if match.geography_score > 0.8:
            return "Strong regional coverage needs"
        return "Balanced category and growth needs"

    def _commission_hint(self, cost_score: float) -> str:
        if cost_score >= 0.8:
            return "Low commission"
        if cost_score >= 0.5:
            return "Moderate commission"
        return "Relatively high commission"

    def _delivery_hint(self, geography_score: float) -> str:
        if geography_score >= 0.9:
            return "Excellent local coverage"
        if geography_score >= 0.6:
            return "Good coverage"
        return "Limited coverage"


def explain_recommendation(mse_profile: dict[str, Any], snp_result: dict[str, Any]) -> str:
    """Backward-compatible recommendation summary helper."""
    snp_name = snp_result.get("snp", {}).get("name", "Unknown SNP")
    score = snp_result.get("score", 0)
    language = mse_profile.get("language_preference", "preferred language")
    return f"Recommended {snp_name} with score {score:.2f} due to category fit and support for {language}."

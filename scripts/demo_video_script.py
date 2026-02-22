"""Narrated demo-video script with 5 preloaded MSE scenarios."""

from __future__ import annotations

import json
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _scenarios() -> list[dict]:
    path = _root() / "data" / "mse_data" / "demo_scenarios.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def run_video_script() -> None:
    scenarios = _scenarios()
    print("VyaparSetu Demo Video Script")
    print("===========================")
    print("Scene 0 (Intro, 10s):")
    print("Narration: 'VyaparSetu helps MSMEs move from Udyam to ONDC in minutes.'")
    print("")

    print("Scene 1 (Registration, 45s):")
    print("Narration: 'Enter Udyam number and auto-fetch enterprise details with UdyamBodh.'")
    print("Show: UDYAM input -> business profile -> ONDC classification")
    print("")

    print("Scene 2 (Catalog, 60s):")
    print("Narration: 'VastraSuchi converts local-language product input into ONDC-ready catalog entries.'")
    print("Show: product description -> category, HSN, pricing, attributes")
    print("")

    print("Scene 3 (SNP Match, 45s):")
    print("Narration: 'SahayakMap recommends the right SNP with explainable scoring.'")
    print("Show: top 3 SNP cards + score breakdown + selected SNP")
    print("")

    print("Scene 4 (Admin Analytics, 30s):")
    print("Narration: 'VriddhiDisha tracks funnel performance and women MSE goals.'")
    print("Show: funnel chart, women gauge, state heatmap")
    print("")

    print("Preloaded Demo Scenarios (no LLM wait):")
    for idx, scn in enumerate(scenarios, start=1):
        print(
            f"{idx}. {scn.get('scenario_id')} | {scn.get('enterprise_name')} | "
            f"{scn.get('state')} | {scn.get('language')} | "
            f"{scn.get('category_l1')} > {scn.get('category_l2')}"
        )
    print("")
    print("Narration: 'VyaparSetu enables inclusive, explainable ONDC onboarding at national scale.'")


if __name__ == "__main__":
    run_video_script()


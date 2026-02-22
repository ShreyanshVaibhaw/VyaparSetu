"""Validate key reference datasets for demo readiness."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> dict[str, bool]:
    results: dict[str, bool] = {}

    categories = _read_json(ROOT / "data" / "ondc_taxonomy" / "categories.json")
    results["ondc_categories_present"] = isinstance(categories, dict) and len(categories.get("categories", [])) >= 8

    hsn = _read_json(ROOT / "data" / "ondc_taxonomy" / "hsn_mapping.json")
    results["hsn_mapping_present"] = isinstance(hsn, list) and len(hsn) >= 100
    results["hsn_has_required_fields"] = bool(
        hsn and {"hsn", "description", "ondc_l1", "ondc_l2"}.issubset(hsn[0].keys())
    )

    nic = _read_json(ROOT / "data" / "mse_data" / "nic_codes.json")
    results["nic_divisions_present"] = isinstance(nic, dict) and len(nic.get("nic_2digit_divisions", [])) >= 20
    results["nic_details_present"] = isinstance(nic, dict) and len(nic.get("common_5digit_details", [])) >= 20

    snp = _read_json(ROOT / "data" / "snp_profiles" / "snp_database.json")
    results["snp_profiles_present"] = isinstance(snp, list) and len(snp) >= 10
    results["snp_has_realistic_fields"] = bool(
        snp and {"snp_id", "name", "supported_categories", "languages_supported", "geographic_coverage"}.issubset(snp[0].keys())
    )

    geo = _read_json(ROOT / "data" / "mse_data" / "state_districts.json")
    states = geo.get("states", []) if isinstance(geo, dict) else []
    has_latlon = False
    if states and isinstance(states[0], dict):
        districts = states[0].get("districts", [])
        if districts and isinstance(districts[0], dict):
            has_latlon = "lat" in districts[0] and "lon" in districts[0]
    results["geo_data_with_latlon"] = has_latlon

    return results


if __name__ == "__main__":
    checks = validate()
    print("Reference Data Validation")
    print("=========================")
    all_ok = True
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'} | {name}")
        all_ok = all_ok and ok
    print(f"\nOverall: {'PASS' if all_ok else 'FAIL'}")

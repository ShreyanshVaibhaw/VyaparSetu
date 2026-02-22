"""SNP profile loading and filtering utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.models import SNPProfile


class SNPProfiler:
    """Manage SNP reference data with convenient filters."""

    def __init__(self, snp_database_path: str, snp_performance_path: str) -> None:
        self.snps = self._load_snps(snp_database_path)
        self.performance = self._load_performance(snp_performance_path)
        self._merge_performance()

    def _load_snps(self, path: str) -> list[SNPProfile]:
        file_path = Path(path)
        if not file_path.exists():
            return []
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                return []
            profiles: list[SNPProfile] = []
            for row in payload:
                if not isinstance(row, dict):
                    continue
                try:
                    profiles.append(SNPProfile(**row))
                except Exception:
                    continue
            return profiles
        except (OSError, json.JSONDecodeError):
            return []

    def _load_performance(self, path: str) -> dict[str, dict[str, Any]]:
        file_path = Path(path)
        if not file_path.exists():
            return {}
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                return {}
            output: dict[str, dict[str, Any]] = {}
            for row in payload:
                if isinstance(row, dict) and row.get("snp_id"):
                    output[str(row["snp_id"])] = row
            return output
        except (OSError, json.JSONDecodeError):
            return {}

    def _merge_performance(self) -> None:
        merged: list[SNPProfile] = []
        for snp in self.snps:
            perf = self.performance.get(snp.snp_id, {})
            merged.append(
                snp.model_copy(
                    update={
                        "seller_success_rate": float(perf.get("seller_success_rate", snp.seller_success_rate)),
                        "avg_activation_days": int(perf.get("avg_activation_days", snp.avg_activation_days)),
                        "rating": float(perf.get("rating", snp.rating)),
                        "active_sellers": int(perf.get("active_sellers", snp.active_sellers)),
                    }
                )
            )
        self.snps = merged

    def get_all_snps(self) -> list[SNPProfile]:
        """Return all SNP profiles."""
        return list(self.snps)

    def get_snps_by_category(self, category_l1: str) -> list[SNPProfile]:
        """Return SNPs supporting a given ONDC L1 category."""
        target = category_l1.strip().lower()
        return [
            snp
            for snp in self.snps
            if any(c.lower() == target for c in snp.supported_categories)
        ]

    def get_snps_by_state(self, state: str) -> list[SNPProfile]:
        """Return SNPs covering a given state."""
        target = state.strip().lower()
        return [
            snp
            for snp in self.snps
            if any(c.lower() == target for c in snp.geographic_coverage) or any(
                c.lower() in {"all india", "pan-india", "pan india"} for c in snp.geographic_coverage
            )
        ]

    def get_snp_details(self, snp_id: str) -> SNPProfile:
        """Return SNP profile by id."""
        for snp in self.snps:
            if snp.snp_id == snp_id:
                return snp
        raise ValueError(f"SNP not found: {snp_id}")

    def get_team_partner_snps(self) -> list[SNPProfile]:
        """Return TEAM Initiative partner SNPs only."""
        return [snp for snp in self.snps if snp.team_initiative_partner]


def load_snp_profiles(path: str | None = None) -> list[dict[str, Any]]:
    """Backward-compatible raw SNP JSON loader."""
    if not path:
        return []
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (json.JSONDecodeError, OSError):
        return []

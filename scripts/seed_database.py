"""Seed VyaparSetu reference + synthetic datasets into PostgreSQL/SQLite."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from config import POSTGRES_URI


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _data_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath("data", *parts)


def _ensure_synthetic_data() -> None:
    required = [
        _data_path("synthetic", "mse_profiles.csv"),
        _data_path("synthetic", "products.csv"),
        _data_path("synthetic", "onboarding_funnel.csv"),
        _data_path("synthetic", "snp_assignments.csv"),
    ]
    if all(path.exists() for path in required):
        return
    script = PROJECT_ROOT / "scripts" / "generate_synthetic_data.py"
    subprocess.run([sys.executable, str(script)], check=True)


def _create_engine() -> tuple[Engine, str]:
    """Create PostgreSQL engine; fallback to local SQLite if unavailable."""
    try:
        pg_engine = create_engine(POSTGRES_URI, pool_pre_ping=True, future=True)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return pg_engine, "postgresql"
    except Exception:
        sqlite_url = f"sqlite:///{(PROJECT_ROOT / 'vyaparsetu.db').as_posix()}"
        sqlite_engine = create_engine(sqlite_url, pool_pre_ping=True, future=True)
        return sqlite_engine, "sqlite"


def _flatten_categories() -> pd.DataFrame:
    payload = json.loads(_data_path("ondc_taxonomy", "categories.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for l1 in payload.get("categories", []):
        l1_name = l1.get("l1")
        for l2 in l1.get("l2_categories", []):
            l2_name = l2.get("l2")
            l3_values = l2.get("l3_categories", []) or [None]
            for l3_name in l3_values:
                rows.append({"l1": l1_name, "l2": l2_name, "l3": l3_name})
    return pd.DataFrame(rows)


def _flatten_nic_codes() -> pd.DataFrame:
    payload = json.loads(_data_path("mse_data", "nic_codes.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

    for row in payload.get("nic_2digit_divisions", []):
        rows.append(
            {
                "row_type": "division",
                "nic_2digit": row.get("code"),
                "nic_5digit": None,
                "description": row.get("description"),
                "major_activity": None,
            }
        )
    for row in payload.get("common_5digit_details", []):
        rows.append(
            {
                "row_type": "detail",
                "nic_2digit": str(row.get("nic_5digit", ""))[:2],
                "nic_5digit": row.get("nic_5digit"),
                "description": row.get("description"),
                "major_activity": row.get("major_activity"),
            }
        )
    return pd.DataFrame(rows)


def _build_onboarding_events(funnel_df: pd.DataFrame) -> pd.DataFrame:
    stages = ["registered", "catalog_created", "snp_matched", "live", "first_order"]
    melted = funnel_df.melt(
        id_vars=["month", "state"],
        value_vars=stages,
        var_name="stage",
        value_name="event_count",
    )
    melted["generated_at"] = datetime.now(timezone.utc).isoformat()
    return melted


def _sanitize_for_sql(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert Python list/dict cells to JSON strings for SQL compatibility."""
    out = frame.copy()
    for col in out.columns:
        out[col] = out[col].apply(
            lambda val: json.dumps(val, ensure_ascii=False) if isinstance(val, (list, dict)) else val
        )
    return out


def seed_database() -> dict[str, Any]:
    """Seed all required tables and return a summary."""
    _ensure_synthetic_data()
    engine, backend = _create_engine()

    # Core synthetic tables.
    mse_profiles = pd.read_csv(_data_path("synthetic", "mse_profiles.csv"))
    products = pd.read_csv(_data_path("synthetic", "products.csv"))
    snp_assignments = pd.read_csv(_data_path("synthetic", "snp_assignments.csv"))
    funnel = pd.read_csv(_data_path("synthetic", "onboarding_funnel.csv"))
    onboarding_events = _build_onboarding_events(funnel)

    # Reference tables.
    ondc_categories_ref = _flatten_categories()
    hsn_mapping_ref = pd.DataFrame(
        json.loads(_data_path("ondc_taxonomy", "hsn_mapping.json").read_text(encoding="utf-8"))
    )
    nic_codes_ref = _flatten_nic_codes()
    snp_profiles_ref = pd.DataFrame(
        json.loads(_data_path("snp_profiles", "snp_database.json").read_text(encoding="utf-8"))
    )

    catalog_items = products.rename(columns={"product_id": "item_id"})
    snp_matches = snp_assignments.rename(columns={"rank": "match_rank"})

    tables: dict[str, pd.DataFrame] = {
        "mse_profiles": mse_profiles,
        "catalog_items": catalog_items,
        "snp_matches": snp_matches,
        "onboarding_events": onboarding_events,
        "ondc_categories_ref": ondc_categories_ref,
        "hsn_mapping_ref": hsn_mapping_ref,
        "nic_codes_ref": nic_codes_ref,
        "snp_profiles_ref": snp_profiles_ref,
    }

    counts: dict[str, int] = {}
    for table_name, frame in tables.items():
        _sanitize_for_sql(frame).to_sql(table_name, engine, if_exists="replace", index=False)
        counts[table_name] = int(len(frame))

    summary: dict[str, Any] = {
        "status": "ok",
        "backend": backend,
        "database": str(engine.url),
        "tables_seeded": len(tables),
        "counts": counts,
    }
    return summary


def seed() -> dict[str, Any]:
    """Backward-compatible wrapper."""
    return seed_database()


if __name__ == "__main__":
    result = seed_database()
    print("Seed Summary")
    print(f"Backend: {result['backend']}")
    print(f"Database: {result['database']}")
    for table_name, row_count in result["counts"].items():
        print(f"- {table_name}: {row_count}")

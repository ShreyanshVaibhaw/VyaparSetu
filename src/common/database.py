"""Database utilities with PostgreSQL-first and SQLite fallback behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.common.logger import get_logger


logger = get_logger(__name__)


def create_engine_with_fallback(postgres_uri: str, sqlite_path: str = "sqlite:///vyaparsetu.db") -> Engine | None:
    """Create SQLAlchemy engine, falling back to SQLite when PostgreSQL is unavailable."""
    try:
        pg_engine = create_engine(postgres_uri, pool_pre_ping=True, future=True)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connected via PostgreSQL")
        return pg_engine
    except Exception as exc:
        logger.warning("PostgreSQL unavailable (%s); using SQLite fallback", exc)

    try:
        sqlite_url = sqlite_path
        if not sqlite_url.startswith("sqlite:///"):
            sqlite_url = f"sqlite:///{Path(sqlite_path).as_posix()}"
        sqlite_engine = create_engine(sqlite_url, pool_pre_ping=True, future=True)
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connected via SQLite fallback")
        return sqlite_engine
    except Exception as exc:
        logger.error("SQLite fallback failed: %s", exc)
        return None


class DatabaseClient:
    """Thin CRUD wrapper for core onboarding tables."""

    CORE_TABLES = {
        "mse_profiles": """
            CREATE TABLE IF NOT EXISTS mse_profiles (
                mse_id TEXT PRIMARY KEY,
                udyam_number TEXT,
                enterprise_name TEXT,
                state TEXT,
                district TEXT,
                is_women_owned INTEGER,
                created_at TEXT
            )
        """,
        "catalog_items": """
            CREATE TABLE IF NOT EXISTS catalog_items (
                item_id TEXT PRIMARY KEY,
                mse_udyam TEXT,
                product_name_en TEXT,
                category_l1 TEXT,
                category_l2 TEXT,
                hsn_code TEXT,
                price_selling REAL,
                created_at TEXT
            )
        """,
        "snp_matches": """
            CREATE TABLE IF NOT EXISTS snp_matches (
                match_id TEXT PRIMARY KEY,
                mse_udyam TEXT,
                snp_id TEXT,
                snp_name TEXT,
                overall_score REAL,
                rank INTEGER,
                generated_at TEXT
            )
        """,
        "onboarding_events": """
            CREATE TABLE IF NOT EXISTS onboarding_events (
                event_id TEXT PRIMARY KEY,
                mse_udyam TEXT,
                stage TEXT,
                timestamp TEXT,
                state TEXT,
                district TEXT
            )
        """,
    }

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def ensure_tables(self) -> None:
        """Create core tables if not present."""
        with self.engine.begin() as conn:
            for ddl in self.CORE_TABLES.values():
                conn.execute(text(ddl))

    def insert(self, table: str, row: dict[str, Any]) -> None:
        """Insert a single row into a table."""
        cols = ", ".join(row.keys())
        params = ", ".join(f":{k}" for k in row.keys())
        stmt = text(f"INSERT INTO {table} ({cols}) VALUES ({params})")
        with self.engine.begin() as conn:
            conn.execute(stmt, row)

    def update(self, table: str, values: dict[str, Any], where_clause: str, where_params: dict[str, Any]) -> int:
        """Update records matching condition and return affected row count."""
        set_expr = ", ".join(f"{k} = :set_{k}" for k in values.keys())
        payload = {f"set_{k}": v for k, v in values.items()}
        payload.update(where_params)
        stmt = text(f"UPDATE {table} SET {set_expr} WHERE {where_clause}")
        with self.engine.begin() as conn:
            result = conn.execute(stmt, payload)
            return int(result.rowcount or 0)

    def delete(self, table: str, where_clause: str, where_params: dict[str, Any]) -> int:
        """Delete records matching condition and return affected row count."""
        stmt = text(f"DELETE FROM {table} WHERE {where_clause}")
        with self.engine.begin() as conn:
            result = conn.execute(stmt, where_params)
            return int(result.rowcount or 0)

    def fetch_all(self, table: str, where_clause: str | None = None, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch records from a table as dictionaries."""
        query = f"SELECT * FROM {table}"
        if where_clause:
            query += f" WHERE {where_clause}"
        stmt = text(query)
        with self.engine.connect() as conn:
            result = conn.execute(stmt, params or {})
            rows = result.mappings().all()
        return [dict(r) for r in rows]


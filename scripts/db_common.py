#!/usr/bin/env python3
"""Shared database paths and helpers for app-download-estimator."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "app_estimator.db"
DEFAULT_SNAPSHOTS_CSV = BASE_DIR / "data" / "snapshots" / "ratings.csv"
DEFAULT_BENCHMARKS_DIR = BASE_DIR / "benchmarks"

# Rating deltas and benchmark windows are normalized to 30 days.
DELTA_BASELINE_DAYS = 30

SNAPSHOT_KEY_FIELDS = ("platform", "app_id", "package", "bundle", "country")


@dataclass(frozen=True)
class SnapshotKey:
    platform: str
    app_id: str
    package: str
    bundle: str
    country: str

    def as_tuple(self) -> tuple[str, str, str, str, str]:
        return (
            self.platform,
            self.app_id,
            self.package,
            self.bundle,
            self.country,
        )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_platform(value: Any) -> str:
    platform = normalize_text(value).lower()
    if platform not in {"ios", "android"}:
        raise ValueError(f"invalid platform: {value!r}")
    return platform


def normalize_country(value: Any) -> str:
    country = normalize_text(value).upper()
    if not country:
        raise ValueError("country is required")
    return country


def snapshot_key_from_row(row: dict[str, Any]) -> SnapshotKey:
    return SnapshotKey(
        platform=normalize_platform(row["platform"]),
        app_id=normalize_text(row.get("app_id")),
        package=normalize_text(row.get("package")),
        bundle=normalize_text(row.get("bundle")),
        country=normalize_country(row.get("country")),
    )


def parse_snapshot_date(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        raise ValueError("snapshot_date is required")
    datetime.strptime(text, "%Y-%m-%d")
    return text


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def connect_db(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or DEFAULT_DB_PATH)
    ensure_parent_dir(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn: sqlite3.Connection, schema_path: Path | None = None) -> None:
    sql_path = schema_path or (SCRIPT_DIR / "db_schema.sql")
    schema_sql = sql_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def upsert_many(
    conn: sqlite3.Connection,
    table: str,
    columns: Iterable[str],
    conflict_columns: Iterable[str],
    rows: list[tuple[Any, ...]],
) -> int:
    if not rows:
        return 0

    cols = list(columns)
    placeholders = ", ".join("?" for _ in cols)
    update_cols = [c for c in cols if c not in conflict_columns]
    update_sql = ", ".join(f"{c} = excluded.{c}" for c in update_cols)
    conflict_sql = ", ".join(conflict_columns)

    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({conflict_sql}) DO UPDATE SET {update_sql}"
    )
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def today_iso() -> str:
    return date.today().isoformat()


def normalize_delta_to_baseline(
    delta_ratings: float | int | None,
    snapshot_days: int | None,
    baseline_days: int = DELTA_BASELINE_DAYS,
) -> float | None:
    """Scale an observed rating delta to the model baseline window (default 30 days)."""
    if delta_ratings is None or snapshot_days is None or snapshot_days <= 0:
        return None
    return float(delta_ratings) * (baseline_days / snapshot_days)


def benchmarks_dir_from_env() -> Path:
    override = os.environ.get("APP_ESTIMATOR_BENCHMARKS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_BENCHMARKS_DIR

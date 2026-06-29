#!/usr/bin/env python3
"""Import ratings.csv snapshots into rating_snapshots table."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from db_common import (
    DEFAULT_DB_PATH,
    DEFAULT_SNAPSHOTS_CSV,
    connect_db,
    init_schema,
    normalize_platform,
    normalize_text,
    parse_snapshot_date,
    snapshot_key_from_row,
    table_exists,
    upsert_many,
)


SNAPSHOT_COLUMNS = [
    "snapshot_date",
    "platform",
    "app_id",
    "package",
    "bundle",
    "country",
    "rating_count",
    "avg_rating",
    "source_url",
    "source_quality",
]


def parse_int(value: str) -> int:
    text = normalize_text(value)
    if not text:
        raise ValueError("rating_count is required")
    return int(float(text))


def parse_float_or_none(value: str) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    return float(text)


def detect_source_quality(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], str]:
    """Flag keys where multiple countries share identical rating_count on same day."""
    grouped: dict[tuple[str, str, str, str, str], list[str]] = defaultdict(list)
    for row in rows:
        key = (
            parse_snapshot_date(row["date"]),
            normalize_platform(row["platform"]),
            normalize_text(row.get("app_id")),
            normalize_text(row.get("package")),
            normalize_text(row.get("bundle")),
        )
        grouped[key].append(normalize_text(row.get("country")).upper())

    suspicious: dict[tuple[str, str, str, str], str] = {}
    values_by_key: dict[tuple[str, str, str, str, str], set[int]] = defaultdict(set)
    for row in rows:
        base = (
            parse_snapshot_date(row["date"]),
            normalize_platform(row["platform"]),
            normalize_text(row.get("app_id")),
            normalize_text(row.get("package")),
            normalize_text(row.get("bundle")),
        )
        values_by_key[base].add(parse_int(row["rating_count"]))

    for base, countries in grouped.items():
        if len(countries) > 1 and len(values_by_key[base]) == 1:
            day, platform, app_id, package, bundle = base
            suspicious[(platform, app_id, package, bundle)] = "global_not_country"
    return suspicious


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"date", "platform", "country", "rating_count"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV missing required columns: {sorted(required)}")
        return [dict(row) for row in reader]


def build_snapshot_rows(csv_rows: list[dict[str, str]]) -> list[tuple]:
    suspicious = detect_source_quality(csv_rows)
    out: list[tuple] = []
    for row in csv_rows:
        key = snapshot_key_from_row(
            {
                "platform": row["platform"],
                "app_id": row.get("app_id", ""),
                "package": row.get("package", ""),
                "bundle": row.get("bundle", ""),
                "country": row["country"],
            }
        )
        source_quality = "country_specific"
        susp_key = (key.platform, key.app_id, key.package, key.bundle)
        if susp_key in suspicious:
            source_quality = suspicious[susp_key]

        out.append(
            (
                parse_snapshot_date(row["date"]),
                key.platform,
                key.app_id,
                key.package,
                key.bundle,
                key.country,
                parse_int(row["rating_count"]),
                parse_float_or_none(row.get("avg_rating", "")),
                normalize_text(row.get("source_url")),
                source_quality,
            )
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ratings.csv into SQLite")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--csv", type=Path, default=DEFAULT_SNAPSHOTS_CSV)
    parser.add_argument("--init", action="store_true", help="Initialize schema if missing")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not write")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    csv_rows = read_csv_rows(args.csv)
    snapshot_rows = build_snapshot_rows(csv_rows)

    if args.dry_run:
        result = {
            "csv": str(args.csv),
            "rows_read": len(csv_rows),
            "rows_ready": len(snapshot_rows),
            "dry_run": True,
        }
        print(json.dumps(result, indent=2) if args.json else result)
        return 0

    conn = connect_db(args.db)
    try:
        if args.init or not table_exists(conn, "rating_snapshots"):
            init_schema(conn)

        imported = upsert_many(
            conn,
            "rating_snapshots",
            SNAPSHOT_COLUMNS,
            (
                "snapshot_date",
                "platform",
                "app_id",
                "package",
                "bundle",
                "country",
            ),
            snapshot_rows,
        )
        result = {
            "db": str(args.db),
            "csv": str(args.csv),
            "rows_read": len(csv_rows),
            "rows_upserted": imported,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Imported {imported} snapshot rows into {args.db}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

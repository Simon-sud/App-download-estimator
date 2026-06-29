#!/usr/bin/env python3
"""Compute rating velocity rows from rating_snapshots."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from db_common import (
    DEFAULT_DB_PATH,
    SnapshotKey,
    connect_db,
    init_schema,
    table_exists,
    upsert_many,
)


VELOCITY_COLUMNS = [
    "platform",
    "app_id",
    "package",
    "bundle",
    "country",
    "as_of_date",
    "previous_date",
    "current_rating_count",
    "previous_rating_count",
    "delta_ratings",
    "snapshot_days",
    "rating_velocity_daily",
    "confidence",
    "confidence_score",
    "calc_method",
]


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def linear_slope(points: list[tuple[int, int]]) -> float | None:
    if len(points) < 2:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(points)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    numer = sum((x - mean_x) * (y - mean_y) for x, y in points)
    return numer / denom


def score_confidence(
    *,
    snapshot_days: int | None,
    delta_ratings: int | None,
    point_count: int,
    source_quality: str,
) -> tuple[str, float]:
    score = 0.0
    if point_count >= 14:
        score += 0.35
    elif point_count >= 7:
        score += 0.25
    elif point_count >= 2:
        score += 0.15

    if snapshot_days is not None:
        if 1 <= snapshot_days <= 7:
            score += 0.30
        elif snapshot_days <= 14:
            score += 0.15
        else:
            score -= 0.20

    if delta_ratings is not None and delta_ratings >= 0:
        score += 0.25
    else:
        score -= 0.30

    if source_quality == "country_specific":
        score += 0.10
    elif source_quality == "global_not_country":
        score -= 0.20

    score = max(0.0, min(1.0, score))
    if score >= 0.70:
        return "high", round(score, 3)
    if score >= 0.45:
        return "medium", round(score, 3)
    return "low", round(score, 3)


def fetch_snapshot_groups(conn, as_of: str | None) -> dict[tuple, list]:
    params: list = []
    where = ""
    if as_of:
        where = "WHERE snapshot_date <= ?"
        params.append(as_of)

    rows = conn.execute(
        f"""
        SELECT
            snapshot_date,
            platform,
            app_id,
            package,
            bundle,
            country,
            rating_count,
            source_quality
        FROM rating_snapshots
        {where}
        ORDER BY platform, app_id, package, bundle, country, snapshot_date
        """,
        params,
    ).fetchall()

    groups: dict[tuple, list] = {}
    for row in rows:
        key = (
            row["platform"],
            row["app_id"],
            row["package"],
            row["bundle"],
            row["country"],
        )
        groups.setdefault(key, []).append(dict(row))
    return groups


def build_adjacent_velocity(key: tuple, rows: list[dict]) -> tuple | None:
    if len(rows) < 2:
        return None
    prev_row, curr_row = rows[-2], rows[-1]
    current_date = curr_row["snapshot_date"]
    previous_date = prev_row["snapshot_date"]
    snapshot_days = (parse_date(current_date) - parse_date(previous_date)).days
    if snapshot_days <= 0:
        return None

    delta = int(curr_row["rating_count"]) - int(prev_row["rating_count"])
    velocity = delta / snapshot_days
    confidence, confidence_score = score_confidence(
        snapshot_days=snapshot_days,
        delta_ratings=delta,
        point_count=len(rows),
        source_quality=curr_row.get("source_quality", "unknown"),
    )
    return (
        key[0],
        key[1],
        key[2],
        key[3],
        key[4],
        current_date,
        previous_date,
        int(curr_row["rating_count"]),
        int(prev_row["rating_count"]),
        delta,
        snapshot_days,
        round(velocity, 4),
        confidence,
        confidence_score,
        "adjacent",
    )


def build_window_velocity(key: tuple, rows: list[dict], window_days: int, method: str) -> tuple | None:
    if len(rows) < 2:
        return None

    curr_row = rows[-1]
    curr_date = parse_date(curr_row["snapshot_date"])
    window_rows = [
        row
        for row in rows
        if (curr_date - parse_date(row["snapshot_date"])).days <= window_days
    ]
    if len(window_rows) < 2:
        return None

    first_row = window_rows[0]
    points = [
        ((parse_date(row["snapshot_date"]) - parse_date(first_row["snapshot_date"])).days, int(row["rating_count"]))
        for row in window_rows
    ]
    slope = linear_slope(points)
    if slope is None:
        return None

    snapshot_days = (parse_date(curr_row["snapshot_date"]) - parse_date(first_row["snapshot_date"])).days
    if snapshot_days <= 0:
        return None

    delta = int(curr_row["rating_count"]) - int(first_row["rating_count"])
    confidence, confidence_score = score_confidence(
        snapshot_days=snapshot_days,
        delta_ratings=delta,
        point_count=len(window_rows),
        source_quality=curr_row.get("source_quality", "unknown"),
    )
    return (
        key[0],
        key[1],
        key[2],
        key[3],
        key[4],
        curr_row["snapshot_date"],
        first_row["snapshot_date"],
        int(curr_row["rating_count"]),
        int(first_row["rating_count"]),
        delta,
        snapshot_days,
        round(slope, 4),
        confidence,
        confidence_score,
        method,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate rating velocity from snapshots")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--as-of", default=None, help="Only use snapshots up to this date (YYYY-MM-DD)")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    conn = connect_db(args.db)
    try:
        if args.init or not table_exists(conn, "rating_velocity"):
            init_schema(conn)

        groups = fetch_snapshot_groups(conn, args.as_of)
        velocity_rows: list[tuple] = []
        for key, rows in groups.items():
            adjacent = build_adjacent_velocity(key, rows)
            if adjacent:
                velocity_rows.append(adjacent)
            window_7d = build_window_velocity(key, rows, 7, "window_7d")
            if window_7d:
                velocity_rows.append(window_7d)
            window_14d = build_window_velocity(key, rows, 14, "window_14d")
            if window_14d:
                velocity_rows.append(window_14d)

        written = upsert_many(
            conn,
            "rating_velocity",
            VELOCITY_COLUMNS,
            (
                "platform",
                "app_id",
                "package",
                "bundle",
                "country",
                "as_of_date",
                "calc_method",
            ),
            velocity_rows,
        )

        result = {
            "db": str(args.db),
            "groups": len(groups),
            "velocity_rows": written,
            "as_of": args.as_of,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Calculated {written} velocity rows from {len(groups)} snapshot groups")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

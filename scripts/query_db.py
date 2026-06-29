#!/usr/bin/env python3
"""Query helpers for app-download-estimator database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from db_common import (
    DEFAULT_DB_PATH,
    DELTA_BASELINE_DAYS,
    connect_db,
    normalize_delta_to_baseline,
    rows_to_dicts,
    table_exists,
)


def query_latest_snapshots(conn, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM v_latest_snapshots
        ORDER BY snapshot_date DESC, platform, package, bundle, country
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return rows_to_dicts(rows)


def query_latest_velocity(conn, limit: int = 20, method: str = "adjacent") -> list[dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM v_latest_velocity
        WHERE calc_method = ?
        ORDER BY as_of_date DESC, confidence_score DESC
        LIMIT ?
        """,
        (method, limit),
    ).fetchall()
    return rows_to_dicts(rows)


def query_app_inputs(
    conn,
    *,
    platform: str,
    country: str,
    app_id: str = "",
    package: str = "",
    bundle: str = "",
    calc_method: str = "adjacent",
) -> dict | None:
    snapshot = conn.execute(
        """
        SELECT *
        FROM rating_snapshots
        WHERE platform = ?
          AND country = ?
          AND app_id = ?
          AND package = ?
          AND bundle = ?
        ORDER BY snapshot_date DESC
        LIMIT 1
        """,
        (platform, country, app_id, package, bundle),
    ).fetchone()

    velocity = conn.execute(
        """
        SELECT *
        FROM rating_velocity
        WHERE platform = ?
          AND country = ?
          AND app_id = ?
          AND package = ?
          AND bundle = ?
          AND calc_method = ?
        ORDER BY as_of_date DESC
        LIMIT 1
        """,
        (platform, country, app_id, package, bundle, calc_method),
    ).fetchone()

    if not snapshot and not velocity:
        return None

    waterline = None
    if snapshot:
        benchmark = conn.execute(
            """
            SELECT downloads
            FROM market_benchmarks
            WHERE country = ?
              AND (
                    (? != '' AND app_id = ?)
                 OR (? != '' AND package = ?)
                 OR (? != '' AND bundle = ?)
              )
            ORDER BY downloads DESC
            LIMIT 1
            """,
            (
                country,
                app_id,
                app_id,
                package,
                package,
                bundle,
                bundle,
            ),
        ).fetchone()
        if benchmark:
            waterline = benchmark["downloads"]

    delta_observed = velocity["delta_ratings"] if velocity else None
    snapshot_days = velocity["snapshot_days"] if velocity else None
    delta_30d = normalize_delta_to_baseline(delta_observed, snapshot_days)

    return {
        "snapshot": dict(snapshot) if snapshot else None,
        "velocity": dict(velocity) if velocity else None,
        "benchmark_waterline": waterline,
        "recommended_inputs": {
            "total_ratings": snapshot["rating_count"] if snapshot else None,
            "delta_ratings": round(delta_30d, 2) if delta_30d is not None else None,
            "delta_ratings_observed": delta_observed,
            "snapshot_days": snapshot_days,
            "delta_baseline_days": DELTA_BASELINE_DAYS,
            "rating_velocity_daily": velocity["rating_velocity_daily"] if velocity else None,
            "confidence": velocity["confidence"] if velocity else None,
        },
    }


def query_stats(conn) -> dict:
    tables = [
        "rating_snapshots",
        "rating_velocity",
        "market_benchmarks",
        "k_calibration",
        "download_estimates",
    ]
    stats = {}
    for table in tables:
        if not table_exists(conn, table):
            stats[table] = 0
            continue
        stats[table] = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Query app-download-estimator database")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="Show table row counts")

    p_snap = sub.add_parser("latest-snapshots", help="Show latest snapshots")
    p_snap.add_argument("--limit", type=int, default=20)

    p_vel = sub.add_parser("latest-velocity", help="Show latest velocity rows")
    p_vel.add_argument("--limit", type=int, default=20)
    p_vel.add_argument("--method", default="adjacent", choices=["adjacent", "window_7d", "window_14d"])

    p_app = sub.add_parser("app-inputs", help="Show estimate-ready inputs for one app")
    p_app.add_argument("--platform", required=True, choices=["ios", "android"])
    p_app.add_argument("--country", required=True)
    p_app.add_argument("--app-id", default="")
    p_app.add_argument("--package", default="")
    p_app.add_argument("--bundle", default="")
    p_app.add_argument("--method", default="adjacent", choices=["adjacent", "window_7d", "window_14d"])

    args = parser.parse_args()
    conn = connect_db(args.db)
    try:
        if args.command == "stats":
            result = query_stats(conn)
        elif args.command == "latest-snapshots":
            result = query_latest_snapshots(conn, args.limit)
        elif args.command == "latest-velocity":
            result = query_latest_velocity(conn, args.limit, args.method)
        else:
            result = query_app_inputs(
                conn,
                platform=args.platform,
                country=args.country,
                app_id=args.app_id,
                package=args.package,
                bundle=args.bundle,
                calc_method=args.method,
            )
            if result is None:
                print(json.dumps({"error": "app not found"}, indent=2))
                return 1

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

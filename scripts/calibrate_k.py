#!/usr/bin/env python3
"""Calibrate effective K values from market benchmarks and rating velocity."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from db_common import (
    DEFAULT_DB_PATH,
    connect_db,
    init_schema,
    normalize_delta_to_baseline,
    table_exists,
    upsert_many,
)


CALIBRATION_COLUMNS = [
    "platform",
    "category",
    "country",
    "effective_k",
    "sample_count",
    "mape",
    "p50_error",
]


def median_absolute_percentage_error(actuals: list[float], preds: list[float]) -> float | None:
    if not actuals:
        return None
    errors = [abs(a - p) / a for a, p in zip(actuals, preds) if a > 0]
    if not errors:
        return None
    return statistics.median(errors)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    idx = int(round((len(values) - 1) * q))
    return values[max(0, min(len(values) - 1, idx))]


def fetch_calibration_samples(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            mb.country,
            mb.platform,
            mb.category_name AS category,
            mb.downloads AS actual_monthly_downloads,
            rv.delta_ratings,
            rv.snapshot_days,
            rv.rating_velocity_daily,
            rv.confidence,
            rv.confidence_score
        FROM market_benchmarks mb
        JOIN v_latest_velocity rv
          ON mb.country = rv.country
         AND mb.platform = rv.platform
         AND (
              (mb.app_id != '' AND mb.app_id = rv.app_id)
              OR (mb.package != '' AND mb.package = rv.package)
              OR (mb.bundle != '' AND mb.bundle = rv.bundle)
         )
        WHERE rv.calc_method = 'adjacent'
          AND rv.delta_ratings IS NOT NULL
          AND rv.delta_ratings > 0
          AND rv.snapshot_days IS NOT NULL
          AND rv.snapshot_days > 0
          AND mb.downloads > 0
        """
    ).fetchall()
    return [dict(row) for row in rows]


def implied_k(sample: dict) -> float | None:
    delta_30d = normalize_delta_to_baseline(
        sample.get("delta_ratings"),
        sample.get("snapshot_days"),
    )
    if delta_30d is None or delta_30d <= 0:
        return None
    return float(sample["actual_monthly_downloads"]) / delta_30d


def aggregate_calibration(samples: list[dict]) -> list[tuple]:
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for sample in samples:
        platform = sample.get("platform") or ""
        category = sample.get("category") or "Default"
        country = sample.get("country") or ""
        grouped.setdefault((platform, category, country), []).append(sample)

    rows: list[tuple] = []
    for (platform, category, country), items in grouped.items():
        ks: list[float] = []
        actuals: list[float] = []
        preds: list[float] = []
        for item in items:
            k = implied_k(item)
            if k is None or k <= 0:
                continue
            ks.append(k)
            actual = float(item["actual_monthly_downloads"])
            pred = float(item["delta_ratings"]) * k
            actuals.append(actual)
            preds.append(pred)

        if not ks:
            continue

        effective_k = statistics.median(ks)
        mape = median_absolute_percentage_error(actuals, preds)
        p50_error = percentile([abs(a - p) for a, p in zip(actuals, preds)], 0.5)
        rows.append(
            (
                platform,
                category,
                country,
                round(effective_k, 4),
                len(ks),
                round(mape, 4) if mape is not None else None,
                round(p50_error, 4) if p50_error is not None else None,
            )
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate effective K values")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    conn = connect_db(args.db)
    try:
        if args.init or not table_exists(conn, "k_calibration"):
            init_schema(conn)

        samples = fetch_calibration_samples(conn)
        rows = aggregate_calibration(samples)
        written = upsert_many(
            conn,
            "k_calibration",
            CALIBRATION_COLUMNS,
            ("platform", "category", "country"),
            rows,
        )

        result = {
            "db": str(args.db),
            "matched_samples": len(samples),
            "calibration_groups": written,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(
                f"Calibrated {written} K groups from {len(samples)} matched app samples"
            )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

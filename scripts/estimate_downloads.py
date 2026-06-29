#!/usr/bin/env python3
"""Estimate monthly app downloads from public rating signals and optional benchmarks."""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from pathlib import Path

from db_common import DEFAULT_BENCHMARKS_DIR, DELTA_BASELINE_DAYS, benchmarks_dir_from_env

# Industry K-factor defaults (downloads per new rating over a 30-day window).
K_MATRIX = {
    "Finance / Banking": 8,
    "Finance / Trading": 120,
    "Utilities": 180,
    "Social / Video": 35,
    "Games (Hyper-casual)": 40,
    "Games (RPG/SLG)": 70,
    "Travel / Food": 150,
    "Health & Fitness": 180,
    "Games": 60,
    "Finance": 50,
    "Default": 100,
}

REGIONAL_FACTORS = {
    "TH": 0.8,
    "VN": 0.8,
    "ID": 0.8,
    "PH": 0.8,
    "JP": 1.2,
    "KR": 1.2,
    "BR": 0.9,
    "MX": 0.9,
    "US": 1.0,
    "GB": 1.0,
    "CA": 1.0,
    "DE": 1.0,
}

CATEGORY_ALIASES = {
    "social": "Social / Video",
    "social networking": "Social / Video",
    "photo and video": "Social / Video",
    "photography": "Social / Video",
    "utilities": "Utilities",
    "tools": "Utilities",
    "finance": "Finance / Banking",
    "banking": "Finance / Banking",
    "business": "Finance / Banking",
    "games": "Games",
    "puzzle": "Games (Hyper-casual)",
    "arcade": "Games (Hyper-casual)",
    "casual": "Games (Hyper-casual)",
    "action": "Games (RPG/SLG)",
    "adventure": "Games (RPG/SLG)",
    "role playing": "Games (RPG/SLG)",
    "strategy": "Games (RPG/SLG)",
    "travel": "Travel / Food",
    "travel & local": "Travel / Food",
    "food & drink": "Travel / Food",
    "food and drink": "Travel / Food",
    "health & fitness": "Health & Fitness",
    "health and fitness": "Health & Fitness",
}

MODEL_VERSION = "1.0.0"


def get_maturity_modifier(total_ratings: int) -> float:
    if total_ratings < 1000:
        return 1.5
    if total_ratings < 10000:
        return 1.0
    if total_ratings < 100000:
        return 0.5
    return 0.1


def resolve_k_key(category: str) -> str:
    cat_lower = category.lower().strip()
    if category in K_MATRIX:
        return category
    for alias, key in CATEGORY_ALIASES.items():
        if alias in cat_lower or cat_lower in alias:
            return key
    for key in K_MATRIX:
        if key.lower() in cat_lower or cat_lower in key.lower():
            return key
    return "Default"


def normalize_delta_ratings(
    delta_ratings: float,
    snapshot_days: int,
    baseline_days: int = DELTA_BASELINE_DAYS,
) -> float:
    if snapshot_days <= 0:
        return float(delta_ratings)
    if snapshot_days == baseline_days:
        return float(delta_ratings)
    return float(delta_ratings) * (baseline_days / snapshot_days)


def category_matches(row_category: str, target_category: str) -> bool:
    row_cat = row_category.lower().strip()
    cat_lower = target_category.lower().strip()
    if not row_cat or not cat_lower:
        return False
    return cat_lower in row_cat or row_cat in cat_lower


def parse_downloads(value: str | None) -> float:
    text = (value or "").replace(",", "").strip()
    if not text:
        return 0.0
    return float(text)


def load_simple_benchmark_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def load_intelligence_benchmark_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_idx = next((i for i, line in enumerate(lines) if line.startswith("App,App Name")), None)
    if header_idx is None:
        return []
    reader = csv.DictReader(lines[header_idx:])
    return [dict(row) for row in reader]


def load_benchmark_file(path: Path) -> list[dict[str, str]]:
    if path.name.endswith(".simple.csv"):
        return load_simple_benchmark_rows(path)
    simple = load_simple_benchmark_rows(path)
    if simple and "downloads" in simple[0]:
        return simple
    return load_intelligence_benchmark_rows(path)


def collect_category_downloads(
    country: str,
    category: str,
    benchmark_dir: Path,
) -> list[float]:
    downloads: list[float] = []
    patterns = [
        str(benchmark_dir / f"*_{country}_*.csv"),
        str(benchmark_dir / f"*{country}*.csv"),
        str(benchmark_dir / "*.csv"),
    ]
    seen_files: set[str] = set()
    for pattern in patterns:
        for file_path in sorted(glob.glob(pattern)):
            if file_path in seen_files:
                continue
            seen_files.add(file_path)
            for row in load_benchmark_file(Path(file_path)):
                row_country = (row.get("country") or row.get("Country/Region") or "").strip().upper()
                if row_country and row_country != country:
                    continue
                row_category = row.get("category_name") or row.get("App Category Name") or row.get("category") or ""
                if not category_matches(str(row_category), category):
                    continue
                value = parse_downloads(row.get("downloads") or row.get("Downloads"))
                if value > 0:
                    downloads.append(value)
    return downloads


def find_waterline(country: str, category: str, rank: int, benchmark_dir: Path) -> float | None:
    """Pick a benchmark ceiling from sorted category downloads and chart rank."""
    if not benchmark_dir.is_dir():
        return None

    values = sorted(collect_category_downloads(country, category, benchmark_dir), reverse=True)
    if not values:
        return None

    if rank and rank > 0:
        index = min(max(rank - 1, 0), len(values) - 1)
        return values[index]

    mid = len(values) // 2
    return values[mid]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate app downloads from rating velocity and optional market benchmarks",
    )
    parser.add_argument("--appid", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--total-ratings", type=int, required=True)
    parser.add_argument(
        "--delta-ratings",
        type=float,
        required=True,
        help="Observed rating delta over --snapshot-days (default 30)",
    )
    parser.add_argument(
        "--snapshot-days",
        type=int,
        default=DELTA_BASELINE_DAYS,
        help="Days covered by --delta-ratings; auto-normalize to 30-day window",
    )
    parser.add_argument("--rank", type=int, default=500, help="Chart rank used for benchmark ceiling")
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=None,
        help="Directory with benchmark CSV files (default: ./benchmarks or APP_ESTIMATOR_BENCHMARKS_DIR)",
    )
    args = parser.parse_args()

    benchmark_dir = args.benchmark_dir or benchmarks_dir_from_env()
    k_key = resolve_k_key(args.category)
    k_base = K_MATRIX.get(k_key, K_MATRIX["Default"])
    beta = get_maturity_modifier(args.total_ratings)
    regional = REGIONAL_FACTORS.get(args.country.upper(), 1.0)

    delta_30d = normalize_delta_ratings(args.delta_ratings, args.snapshot_days)
    raw_monthly = delta_30d * k_base * beta * regional

    waterline = find_waterline(args.country.upper(), args.category, args.rank, benchmark_dir)
    final_monthly = raw_monthly
    status = "pure_calculation"
    confidence = "medium"

    if waterline is not None:
        cap = waterline * 1.5
        if raw_monthly > cap:
            final_monthly = cap
            status = "waterline_capped"
        else:
            status = "waterline_validated"
        confidence = "high"

    result = {
        "appid": args.appid,
        "country": args.country.upper(),
        "category": args.category,
        "k_key_used": k_key,
        "rank": args.rank,
        "model_version": MODEL_VERSION,
        "est_monthly_downloads": round(final_monthly),
        "est_daily_downloads": round(final_monthly / 30),
        "confidence": confidence,
        "methodology": status,
        "disclaimer": "Heuristic estimate only; not official store download data.",
        "factors": {
            "base_k": k_base,
            "maturity_beta": beta,
            "regional_m": regional,
            "benchmark_waterline": round(waterline) if waterline is not None else None,
            "benchmark_dir": str(benchmark_dir),
            "delta_ratings_input": round(args.delta_ratings, 2),
            "snapshot_days": args.snapshot_days,
            "delta_ratings_30d": round(delta_30d, 2),
        },
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

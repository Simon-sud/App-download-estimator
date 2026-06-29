#!/usr/bin/env python3
"""Import market benchmark CSV files into market_benchmarks."""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from pathlib import Path

from db_common import (
    DEFAULT_BENCHMARKS_DIR,
    DEFAULT_DB_PATH,
    benchmarks_dir_from_env,
    connect_db,
    init_schema,
    normalize_text,
    table_exists,
    upsert_many,
)
from estimate_downloads import load_benchmark_file, parse_downloads


BENCHMARK_COLUMNS = [
    "country",
    "app_id",
    "app_name",
    "bundle",
    "package",
    "platform",
    "category",
    "category_name",
    "chart_rank",
    "downloads",
    "report_start",
    "report_end",
    "source_file",
]

COUNTRY_RE = re.compile(r"_([A-Z]{2})_", re.IGNORECASE)
DATE_RANGE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse_country_from_filename(path: Path) -> str | None:
    match = COUNTRY_RE.search(path.name)
    return match.group(1).upper() if match else None


def parse_report_dates(path: Path, lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines[:20]:
        if line.startswith("Date,"):
            matches = DATE_RANGE_RE.findall(line)
            if len(matches) >= 2:
                return matches[0], matches[1]
    matches = DATE_RANGE_RE.findall(path.name)
    if len(matches) >= 2:
        return matches[0], matches[1]
    return None, None


def detect_platform(market: str, package: str, bundle: str) -> str:
    market_l = normalize_text(market).lower()
    if "google" in market_l:
        return "android"
    if "apple" in market_l:
        return "ios"
    if package and not bundle:
        return "android"
    if bundle and not package:
        return "ios"
    return normalize_text(market).lower()


def parse_simple_file(path: Path) -> list[tuple]:
    rows: list[tuple] = []
    for row in load_benchmark_file(path):
        country = normalize_text(row.get("country")).upper()
        if not country:
            country = parse_country_from_filename(path) or ""
        downloads = int(parse_downloads(row.get("downloads")))
        if not country or downloads <= 0:
            continue
        rows.append(
            (
                country,
                normalize_text(row.get("app_id")),
                normalize_text(row.get("app_name")),
                normalize_text(row.get("bundle")),
                normalize_text(row.get("package")),
                normalize_text(row.get("platform")).lower(),
                normalize_text(row.get("category")),
                normalize_text(row.get("category_name") or row.get("category")),
                int(float(row.get("chart_rank") or 0)) or None,
                downloads,
                normalize_text(row.get("report_start")) or None,
                normalize_text(row.get("report_end")) or None,
                path.name,
            )
        )
    return rows


def parse_intelligence_file(path: Path) -> list[tuple]:
    country = parse_country_from_filename(path)
    if not country:
        return []

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_idx = next((i for i, line in enumerate(lines) if line.startswith("App,App Name")), None)
    if header_idx is None:
        return []

    report_start, report_end = parse_report_dates(path, lines)
    reader = csv.DictReader(lines[header_idx:])
    rows: list[tuple] = []

    for index, row in enumerate(reader, start=1):
        downloads = int(parse_downloads(row.get("Downloads")))
        if downloads <= 0:
            continue

        app_id = normalize_text(row.get("App"))
        package = normalize_text(row.get("App Package Name"))
        bundle = normalize_text(row.get("App Bundle ID"))
        platform = detect_platform(row.get("Market", ""), package, bundle)

        rows.append(
            (
                country,
                app_id,
                normalize_text(row.get("App Name")),
                bundle,
                package,
                platform,
                normalize_text(row.get("App Category")),
                normalize_text(row.get("App Category Name")),
                index,
                downloads,
                report_start,
                report_end,
                path.name,
            )
        )
    return rows


def parse_benchmark_file(path: Path) -> list[tuple]:
    simple = parse_simple_file(path)
    if simple:
        return simple
    return parse_intelligence_file(path)


def discover_benchmark_files(benchmark_dir: Path) -> list[Path]:
    patterns = ["*.csv", "**/*.csv"]
    files: list[Path] = []
    seen: set[str] = set()
    for pattern in patterns:
        for file_path in sorted(benchmark_dir.glob(pattern)):
            resolved = str(file_path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(file_path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Import benchmark CSV files into SQLite")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--benchmark-dir", type=Path, default=None)
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    benchmark_dir = args.benchmark_dir or benchmarks_dir_from_env()
    files = discover_benchmark_files(benchmark_dir)
    all_rows: list[tuple] = []
    per_file: dict[str, int] = {}

    for file_path in files:
        parsed = parse_benchmark_file(file_path)
        per_file[file_path.name] = len(parsed)
        all_rows.extend(parsed)

    if args.dry_run:
        result = {
            "benchmark_dir": str(benchmark_dir),
            "files": len(files),
            "rows_ready": len(all_rows),
            "per_file": per_file,
            "dry_run": True,
        }
        print(json.dumps(result, indent=2) if args.json else result)
        return 0

    conn = connect_db(args.db)
    try:
        if args.init or not table_exists(conn, "market_benchmarks"):
            init_schema(conn)

        imported = upsert_many(
            conn,
            "market_benchmarks",
            BENCHMARK_COLUMNS,
            ("country", "app_id", "package", "bundle", "report_start", "report_end"),
            all_rows,
        )
        result = {
            "db": str(args.db),
            "benchmark_dir": str(benchmark_dir),
            "files": len(files),
            "rows_upserted": imported,
            "per_file": per_file,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Imported {imported} benchmark rows from {len(files)} files")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

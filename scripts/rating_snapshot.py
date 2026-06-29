#!/usr/bin/env python3
"""Collect app store rating snapshots from a watchlist into ratings.csv."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

try:
    from google_play_scraper import app as gp_app  # pyright: ignore[reportMissingImports]
except ImportError as exc:
    raise SystemExit(
        "Missing dependency google-play-scraper. "
        "Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    ) from exc

from db_common import DEFAULT_SNAPSHOTS_CSV, normalize_text, today_iso


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_WATCHLIST_PATH = SCRIPT_DIR.parent / "examples" / "watchlist.json"

CSV_COLUMNS = [
    "date",
    "platform",
    "app_id",
    "package",
    "bundle",
    "country",
    "rating_count",
    "avg_rating",
    "source_url",
]


def load_watchlist(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        entries = data.get("entries", [])
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError(f"Invalid watchlist format: {path}")

    targets: list[dict] = []
    for entry in entries:
        platform = normalize_text(entry.get("platform")).lower()
        app_id = normalize_text(entry.get("app_id"))
        package = normalize_text(entry.get("package"))
        bundle = normalize_text(entry.get("bundle"))
        countries = entry.get("countries") or []
        if isinstance(countries, str):
            countries = [countries]
        for country in countries:
            cc = normalize_text(country).upper()
            if not cc:
                continue
            targets.append(
                {
                    "platform": platform,
                    "app_id": app_id,
                    "package": package,
                    "bundle": bundle,
                    "country": cc,
                    "app_name": normalize_text(entry.get("app_name")),
                }
            )
    return targets


def snapshot_key(row: dict) -> tuple[str, str, str, str, str, str]:
    return (
        row["date"],
        row["platform"],
        row["app_id"],
        row["package"],
        row["bundle"],
        row["country"],
    )


def read_existing_csv(path: Path) -> tuple[list[dict], set[tuple[str, str, str, str, str, str]]]:
    if not path.exists():
        return [], set()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    keys = {snapshot_key(row) for row in rows}
    return rows, keys


def fetch_android(package: str, country: str) -> tuple[int, float | None, str]:
    cc = country.lower()
    result = gp_app(package, lang="en", country=cc)
    rating_count = int(result.get("ratings") or 0)
    score = result.get("score")
    avg_rating = float(score) if score is not None else None
    source_url = f"https://play.google.com/store/apps/details?id={package}&gl={cc}&hl=en"
    return rating_count, avg_rating, source_url


def fetch_ios(app_id: str, bundle: str, country: str) -> tuple[int, float | None, str]:
    cc = country.lower()
    if app_id:
        query = f"id={app_id}"
        source_url = f"https://apps.apple.com/{cc}/app/id{app_id}"
    elif bundle:
        query = f"bundleId={bundle}"
        source_url = f"https://apps.apple.com/{cc}/app/{bundle}"
    else:
        raise ValueError("ios target requires app_id or bundle")

    url = f"https://itunes.apple.com/lookup?{query}&country={cc}"
    request = urllib.request.Request(url, headers={"User-Agent": "app-download-estimator/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    results = payload.get("results") or []
    if not results:
        raise LookupError(f"itunes lookup returned no results for {query} in {country}")

    item = results[0]
    rating_count = int(item.get("userRatingCount") or 0)
    avg_rating_raw = item.get("averageUserRating")
    avg_rating = float(avg_rating_raw) if avg_rating_raw is not None else None
    return rating_count, avg_rating, source_url


def collect_target(target: dict, snapshot_date: str) -> dict:
    platform = target["platform"]
    country = target["country"]
    app_id = target["app_id"]
    package = target["package"]
    bundle = target["bundle"]

    if platform == "android":
        if not package:
            raise ValueError("android target requires package")
        rating_count, avg_rating, source_url = fetch_android(package, country)
    elif platform == "ios":
        rating_count, avg_rating, source_url = fetch_ios(app_id, bundle, country)
    else:
        raise ValueError(f"unsupported platform: {platform}")

    return {
        "date": snapshot_date,
        "platform": platform,
        "app_id": app_id,
        "package": package,
        "bundle": bundle,
        "country": country,
        "rating_count": rating_count,
        "avg_rating": avg_rating if avg_rating is not None else "",
        "source_url": source_url,
    }


def append_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect rating snapshots from watchlist")
    parser.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST_PATH)
    parser.add_argument("--csv", type=Path, default=DEFAULT_SNAPSHOTS_CSV)
    parser.add_argument("--date", default="", help="Snapshot date YYYY-MM-DD (default: today)")
    parser.add_argument("--limit", type=int, default=0, help="Only process first N targets")
    parser.add_argument("--throttle-seconds", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.watchlist.exists():
        print(f"watchlist not found: {args.watchlist}", file=sys.stderr)
        print("Copy examples/watchlist.json or create your own watchlist file.", file=sys.stderr)
        return 1

    snapshot_date = args.date or today_iso()
    targets = load_watchlist(args.watchlist)
    if args.limit > 0:
        targets = targets[: args.limit]

    _, existing_keys = read_existing_csv(args.csv)
    collected: list[dict] = []
    skipped = 0
    failures: list[dict] = []

    for index, target in enumerate(targets, start=1):
        row = {
            "date": snapshot_date,
            "platform": target["platform"],
            "app_id": target["app_id"],
            "package": target["package"],
            "bundle": target["bundle"],
            "country": target["country"],
        }
        if snapshot_key(row) in existing_keys:
            skipped += 1
            continue

        if args.dry_run:
            collected.append({**row, "rating_count": 0, "avg_rating": "", "source_url": "dry-run"})
            continue

        try:
            result = collect_target(target, snapshot_date)
            collected.append(result)
            existing_keys.add(snapshot_key(result))
        except Exception as exc:  # noqa: BLE001 - collect failures and continue
            failures.append(
                {
                    "platform": target["platform"],
                    "country": target["country"],
                    "package": target["package"],
                    "bundle": target["bundle"],
                    "app_id": target["app_id"],
                    "error": str(exc),
                }
            )

        if index < len(targets) and args.throttle_seconds > 0:
            time.sleep(args.throttle_seconds)

    if collected and not args.dry_run:
        append_rows(args.csv, collected)

    summary = {
        "watchlist": str(args.watchlist),
        "csv": str(args.csv),
        "snapshot_date": snapshot_date,
        "targets": len(targets),
        "collected": len(collected),
        "skipped_existing": skipped,
        "failed": len(failures),
        "failures": failures[:20],
        "dry_run": args.dry_run,
    }

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(
            f"Collected {summary['collected']} rows, skipped {summary['skipped_existing']}, "
            f"failed {summary['failed']} (date={snapshot_date})"
        )
        if failures:
            print("First failure:", failures[0], file=sys.stderr)

    return 0 if not failures or collected else 1


if __name__ == "__main__":
    sys.exit(main())

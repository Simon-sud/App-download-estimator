#!/usr/bin/env python3
"""Initialize SQLite schema for app-download-estimator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from db_common import DEFAULT_DB_PATH, connect_db, init_schema, table_exists


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize app-download-estimator database")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path")
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Optional custom schema SQL path",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    conn = connect_db(args.db)
    try:
        init_schema(conn, args.schema)
        tables = [
            "apps",
            "rating_snapshots",
            "snapshot_quality_flags",
            "rating_velocity",
            "market_benchmarks",
            "k_calibration",
            "download_estimates",
        ]
        summary = {
            "db": str(args.db),
            "initialized": True,
            "tables": {name: table_exists(conn, name) for name in tables},
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"Database initialized: {args.db}")
            for name, exists in summary["tables"].items():
                print(f"  - {name}: {'ok' if exists else 'missing'}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

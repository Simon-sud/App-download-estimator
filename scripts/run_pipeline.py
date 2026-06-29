#!/usr/bin/env python3
"""Run the full app-download-estimator data pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from db_common import (
    DEFAULT_BENCHMARKS_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_SNAPSHOTS_CSV,
    SCRIPT_DIR,
    benchmarks_dir_from_env,
)


def run_step(name: str, cmd: list[str], dry_run: bool = False) -> dict:
    if dry_run:
        return {"step": name, "command": cmd, "dry_run": True}
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "step": name,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run import -> velocity -> calibration pipeline")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--csv", type=Path, default=DEFAULT_SNAPSHOTS_CSV)
    parser.add_argument("--benchmark-dir", type=Path, default=None)
    parser.add_argument("--skip-benchmarks", action="store_true")
    parser.add_argument("--skip-calibration", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    benchmark_dir = args.benchmark_dir or benchmarks_dir_from_env()
    py = sys.executable
    steps = [
        (
            "init_db",
            [py, str(SCRIPT_DIR / "init_db.py"), "--db", str(args.db), "--json"],
        ),
        (
            "import_snapshots",
            [
                py,
                str(SCRIPT_DIR / "import_snapshots.py"),
                "--db",
                str(args.db),
                "--csv",
                str(args.csv),
                "--init",
                "--json",
            ],
        ),
        (
            "calc_velocity",
            [py, str(SCRIPT_DIR / "calc_velocity.py"), "--db", str(args.db), "--json"],
        ),
    ]

    if not args.skip_benchmarks:
        steps.append(
            (
                "import_benchmarks",
                [
                    py,
                    str(SCRIPT_DIR / "import_benchmarks.py"),
                    "--db",
                    str(args.db),
                    "--benchmark-dir",
                    str(benchmark_dir),
                    "--init",
                    "--json",
                ],
            )
        )

    if not args.skip_calibration:
        steps.append(
            (
                "calibrate_k",
                [py, str(SCRIPT_DIR / "calibrate_k.py"), "--db", str(args.db), "--json"],
            )
        )

    results = [run_step(name, cmd, dry_run=args.dry_run) for name, cmd in steps]
    failed = [r for r in results if not args.dry_run and r.get("returncode", 0) != 0]

    summary = {
        "db": str(args.db),
        "csv": str(args.csv),
        "benchmark_dir": str(benchmark_dir),
        "steps": results,
        "success": len(failed) == 0,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for item in results:
            status = "dry-run" if item.get("dry_run") else ("ok" if item.get("returncode", 0) == 0 else "failed")
            print(f"[{status}] {item['step']}")
            if item.get("stdout"):
                print(item["stdout"])
            if item.get("stderr"):
                print(item["stderr"], file=sys.stderr)
        print("Pipeline success" if summary["success"] else "Pipeline failed")

    return 0 if summary["success"] else 1


if __name__ == "__main__":
    sys.exit(main())

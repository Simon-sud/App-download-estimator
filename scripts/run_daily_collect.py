#!/usr/bin/env python3
"""Daily entrypoint: collect snapshots and refresh DB velocity."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from db_common import DEFAULT_DB_PATH, DEFAULT_SNAPSHOTS_CSV, SCRIPT_DIR


DEFAULT_WATCHLIST_PATH = SCRIPT_DIR.parent / "examples" / "watchlist.json"
DEFAULT_VENV_PYTHON = SCRIPT_DIR.parent / ".venv" / "bin" / "python"


def resolve_python() -> str:
    if DEFAULT_VENV_PYTHON.exists():
        return str(DEFAULT_VENV_PYTHON)
    return sys.executable


def run_step(name: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "step": name,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run daily snapshot collection pipeline")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--csv", type=Path, default=DEFAULT_SNAPSHOTS_CSV)
    parser.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST_PATH)
    parser.add_argument("--throttle-seconds", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=0, help="Only collect first N watchlist targets")
    parser.add_argument("--calibrate", action="store_true", help="Also run calibrate_k.py")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    py = resolve_python()
    steps = [
        (
            "rating_snapshot",
            [
                py,
                str(SCRIPT_DIR / "rating_snapshot.py"),
                "--watchlist",
                str(args.watchlist),
                "--csv",
                str(args.csv),
                "--throttle-seconds",
                str(args.throttle_seconds),
                "--json",
            ]
            + (["--limit", str(args.limit)] if args.limit > 0 else []),
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
                "--json",
            ],
        ),
        (
            "calc_velocity",
            [py, str(SCRIPT_DIR / "calc_velocity.py"), "--db", str(args.db), "--json"],
        ),
    ]

    if args.calibrate:
        steps.append(
            (
                "calibrate_k",
                [py, str(SCRIPT_DIR / "calibrate_k.py"), "--db", str(args.db), "--json"],
            )
        )

    results = [run_step(name, cmd) for name, cmd in steps]
    failed = [item for item in results if item["returncode"] != 0]
    summary = {
        "db": str(args.db),
        "csv": str(args.csv),
        "watchlist": str(args.watchlist),
        "steps": results,
        "success": len(failed) == 0,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for item in results:
            status = "ok" if item["returncode"] == 0 else "failed"
            print(f"[{status}] {item['step']}")
            if item["stdout"]:
                print(item["stdout"])
            if item["stderr"]:
                print(item["stderr"], file=sys.stderr)
        print("Daily collect success" if summary["success"] else "Daily collect failed")

    return 0 if summary["success"] else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

mkdir -p benchmarks data/snapshots
if [ ! -f benchmarks/.gitkeep ] && [ -z "$(ls -A benchmarks 2>/dev/null || true)" ]; then
  cp -n examples/benchmarks/US_finance.sample.csv benchmarks/ 2>/dev/null || true
fi

echo "Ready."
echo "Quick test:"
echo "  .venv/bin/python scripts/estimate_downloads.py --appid demo --category Finance --country US --total-ratings 5000 --delta-ratings 120 --rank 25 --benchmark-dir examples/benchmarks"

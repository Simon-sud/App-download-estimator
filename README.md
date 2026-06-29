# app-download-estimator

Estimate mobile app download volume from **public store signals** (rating counts and velocity) with optional **market benchmark calibration**.

This project is a standalone, open-source toolchain. It does **not** ship proprietary benchmark datasets or internal watchlists. You bring your own licensed benchmark CSVs when you want waterline calibration.

> **Disclaimer:** All outputs are heuristic estimates for research and planning. They are not official App Store or Google Play download figures.

## Features

- K-factor model with maturity and regional modifiers
- Optional benchmark waterline validation and rank-aware ceiling
- Rating snapshot collector for iOS (iTunes Lookup) and Android (`google-play-scraper`)
- SQLite pipeline for snapshots, velocity, benchmark import, and K calibration
- JSON CLI output for automation and agent integration

## Quick start

```bash
git clone <your-repo-url>
cd app-download-estimator-oss
bash scripts/setup_env.sh

# One-off estimate using the included synthetic sample benchmarks
.venv/bin/python scripts/estimate_downloads.py \
  --appid demo-wallet \
  --category "Finance / Banking" \
  --country US \
  --total-ratings 4200 \
  --delta-ratings 180 \
  --rank 15 \
  --benchmark-dir examples/benchmarks
```

Or run the bundled example:

```bash
bash examples/run_estimate.sh
```

## Project layout

```text
app-download-estimator-oss/
├── scripts/                 # CLI tools and pipeline
├── references/k_matrix.md   # Model coefficient reference
├── examples/
│   ├── benchmarks/          # Synthetic sample CSV (safe to publish)
│   ├── watchlist.json       # Small public-app example list
│   └── run_estimate.sh
├── benchmarks/              # Your licensed benchmark CSVs (not committed)
└── data/                    # Local SQLite DB and snapshot CSV (not committed)
```

## Core commands

### Estimate downloads

```bash
python3 scripts/estimate_downloads.py \
  --appid <id> \
  --category "<category>" \
  --country <CC> \
  --total-ratings <int> \
  --delta-ratings <float> \
  --rank <int> \
  --benchmark-dir benchmarks
```

Notes:

- `--delta-ratings` is normalized to a **30-day window** by default
- Pass `--snapshot-days 7` if your delta covers only 7 days
- Without benchmark files, the tool still returns a pure formula estimate

### Snapshot collection

```bash
python3 scripts/rating_snapshot.py \
  --watchlist examples/watchlist.json \
  --limit 5
```

### Database pipeline

```bash
python3 scripts/init_db.py
python3 scripts/run_pipeline.py --skip-calibration
python3 scripts/query_db.py stats
```

Import your own benchmark CSVs:

```bash
python3 scripts/import_benchmarks.py --benchmark-dir benchmarks
```

## Benchmark CSV formats

### Simple format (recommended for custom data)

```csv
country,platform,app_id,package,bundle,app_name,category,category_name,chart_rank,downloads,report_start,report_end
US,android,,com.example.app,,Example,Finance,Finance / Banking,20,12000,2026-01-01,2026-01-31
```

### Intelligence export format

The importer also accepts vendor intelligence exports that contain a header row starting with `App,App Name`. **Only import files you are licensed to use.** Do not redistribute those files in public repositories.

## Model overview

```text
monthly_downloads = delta_ratings_30d × K × maturity_beta × regional_factor
```

If benchmark data exists, the result may be capped by a rank-aware category waterline.

See [references/k_matrix.md](references/k_matrix.md) for default coefficients.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `APP_ESTIMATOR_BENCHMARKS_DIR` | Override default `./benchmarks` directory |

## Testing

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

## Agent / automation integration

The CLI prints JSON to stdout. A typical agent flow:

1. Collect or query `total_ratings` and `delta_ratings`
2. Run `estimate_downloads.py`
3. Present `est_monthly_downloads`, `confidence`, and `methodology` to the user

For richer workflows, use `query_db.py app-inputs` after building a local snapshot history.

## License

MIT. See [LICENSE](LICENSE).

## What not to open source

Keep these private in your deployment:

- Licensed intelligence exports (for example data.ai / Sensor Tower downloads)
- Large production watchlists derived from paid datasets
- Internal SQLite databases with operational history

This repository is intentionally structured so the **toolchain is public** while **your market data stays local**.

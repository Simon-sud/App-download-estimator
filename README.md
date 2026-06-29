<div align="center">

# 📊 App Download Estimator

**Estimate mobile app downloads from public store rating signals**

Optional market-benchmark calibration · SQLite snapshot pipeline · **OpenClaw skill ready**

<br/>

<p>
  <a href="README.md"><strong>English</strong></a>
  &nbsp;·&nbsp;
  <a href="README.zh-CN.md">简体中文</a>
</p>

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](requirements.txt)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill%20Ready-5B6EE1)](SKILL.md)
[![AppsFlyer Workbench](https://img.shields.io/badge/AppsFlyer--API--Tools-UI%20Integration-0A7BFF)](https://github.com/Simon-sud/AppsFlyer-API-Tools)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)](tests/)

<br/>

<p>
  <em>K-factor modeling · maturity & regional modifiers · rank-aware waterline · JSON CLI output</em>
</p>

<p>
  <a href="#quick-start">Quick Start</a>
  &nbsp;·&nbsp;
  <a href="#openclaw-skill">OpenClaw</a>
  &nbsp;·&nbsp;
  <a href="#appsflyer-workbench">AppsFlyer UI</a>
  &nbsp;·&nbsp;
  <a href="#model">Model</a>
  &nbsp;·&nbsp;
  <a href="#license">License</a>
</p>

<br/>

> **Disclaimer:** Heuristic estimates for research and planning only — not official App Store or Google Play download figures.

</div>

---

## Overview

**app-download-estimator** is an open-source toolchain that estimates monthly and daily app downloads using **public rating counts and growth velocity**, with optional calibration from **your own licensed benchmark CSVs**.

This repository ships **no proprietary datasets**. Bring your own benchmarks when you need waterline validation.

| Capability | Description |
| --- | --- |
| **Estimate** | `estimate_downloads.py` — K-factor model with 30-day delta normalization |
| **Collect** | `rating_snapshot.py` — iOS (iTunes Lookup) + Android (`google-play-scraper`) |
| **Pipeline** | SQLite snapshots, velocity, benchmark import, K calibration |
| **Agents** | JSON stdout + [`SKILL.md`](SKILL.md) for [OpenClaw](https://docs.openclaw.ai) workflows |

---

## AppsFlyer workbench

This repository is the **standalone open-source engine** behind the **App Estimator** module in [AppsFlyer-API-Tools](https://github.com/Simon-sud/AppsFlyer-API-Tools).

| Repo | Role |
| --- | --- |
| **[App-download-estimator](https://github.com/Simon-sud/App-download-estimator)** (this repo) | CLI scripts, SQLite pipeline, benchmarks import, OpenClaw `SKILL.md` |
| **[AppsFlyer-API-Tools](https://github.com/Simon-sud/AppsFlyer-API-Tools)** | Full data workbench — route `/app-estimator` UI talks to Go `:5001` and shares the same estimation model |

Use **this repo** for agent skills, scripting, and headless automation. Use **AppsFlyer-API-Tools** when you need the React UI inside the broader AppsFlyer analytics stack.

---

## Quick start

```bash
git clone https://github.com/Simon-sud/App-download-estimator.git
cd App-download-estimator
bash scripts/setup_env.sh

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

---

## OpenClaw skill

Install as a workspace skill (copy or symlink the repo into your OpenClaw skills directory):

```bash
# Example: install into default OpenClaw workspace
mkdir -p ~/.openclaw/workspace/skills
cp -R /path/to/App-download-estimator ~/.openclaw/workspace/skills/app-download-estimator
```

The agent reads [`SKILL.md`](SKILL.md) for triggers, CLI usage, and reporting rules. Requires `python3` on the host.

See [SKILL.md](SKILL.md) for full agent integration details.

---

## Project layout

```text
App-download-estimator/
├── SKILL.md                 # OpenClaw skill definition
├── scripts/                 # CLI tools and pipeline
├── references/k_matrix.md   # Model coefficients
├── examples/
│   ├── benchmarks/          # Synthetic sample CSV (safe to publish)
│   ├── watchlist.json
│   └── run_estimate.sh
├── benchmarks/              # Your licensed CSVs (local only)
└── data/                    # SQLite DB & snapshots (local only)
```

---

## Core commands

<details>
<summary><strong>Estimate downloads</strong></summary>

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

- `--delta-ratings` is normalized to a **30-day window** by default
- Use `--snapshot-days 7` when your delta covers only 7 days
- Without benchmarks, returns a pure formula estimate

</details>

<details>
<summary><strong>Snapshot collection</strong></summary>

```bash
python3 scripts/rating_snapshot.py \
  --watchlist examples/watchlist.json \
  --limit 5
```

</details>

<details>
<summary><strong>Database pipeline</strong></summary>

```bash
python3 scripts/init_db.py
python3 scripts/run_pipeline.py --skip-calibration
python3 scripts/import_benchmarks.py --benchmark-dir benchmarks
python3 scripts/query_db.py stats
```

</details>

---

## Benchmark CSV formats

**Simple format** (recommended):

```csv
country,platform,app_id,package,bundle,app_name,category,category_name,chart_rank,downloads,report_start,report_end
US,android,,com.example.app,,Example,Finance,Finance / Banking,20,12000,2026-01-01,2026-01-31
```

**Intelligence export format** — importer accepts vendor exports with an `App,App Name` header. **Only import files you are licensed to use.** Do not commit proprietary exports to public repos.

Sample file: [`examples/benchmarks/US_finance.sample.csv`](examples/benchmarks/US_finance.sample.csv)

---

## Model

```text
monthly_downloads = delta_ratings_30d × K × maturity_beta × regional_factor
```

When benchmark data is available, results may be capped by a **rank-aware category waterline** (`1.5 × waterline`).

Coefficients: [`references/k_matrix.md`](references/k_matrix.md)

| Variable | Purpose |
| --- | --- |
| `APP_ESTIMATOR_BENCHMARKS_DIR` | Override default `./benchmarks` directory |

---

## Testing

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

---

## Agent workflow

1. Collect or query `total_ratings` and `delta_ratings` (or use `query_db.py app-inputs`)
2. Run `estimate_downloads.py`
3. Present `est_monthly_downloads`, `confidence`, and `methodology` to the user

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

<br/>

**Keep private in production**

Licensed intelligence exports · large paid-data watchlists · operational SQLite history

<br/>

<p>
  <a href="README.md"><strong>English</strong></a>
  &nbsp;·&nbsp;
  <a href="README.zh-CN.md">简体中文</a>
</p>

</div>

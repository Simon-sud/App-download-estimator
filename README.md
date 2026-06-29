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
  <a href="#overview">Overview</a>
  &nbsp;·&nbsp;
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

<br/>

---

<h2 id="overview">Overview</h2>

<p>
<strong>app-download-estimator</strong> is an open-source toolchain that estimates monthly and daily app downloads using <strong>public rating counts and growth velocity</strong>, with optional calibration from <strong>your own licensed benchmark CSVs</strong>.
</p>

<p>
This repository ships <strong>no proprietary datasets</strong>. Bring your own benchmarks when you need waterline validation.
</p>

| Capability | Description |
| :---: | :---: |
| **Estimate** | `estimate_downloads.py` — K-factor model with 30-day delta normalization |
| **Collect** | `rating_snapshot.py` — iOS (iTunes Lookup) + Android (`google-play-scraper`) |
| **Pipeline** | SQLite snapshots, velocity, benchmark import, K calibration |
| **Agents** | JSON stdout + [`SKILL.md`](SKILL.md) for [OpenClaw](https://docs.openclaw.ai) workflows |

<br/>

---

<h2 id="appsflyer-workbench">AppsFlyer workbench</h2>

<p>
This repository is the <strong>standalone open-source engine</strong> behind the <strong>App Estimator</strong> module in <a href="https://github.com/Simon-sud/AppsFlyer-API-Tools">AppsFlyer-API-Tools</a>.
</p>

| Repo | Role |
| :---: | :---: |
| **[App-download-estimator](https://github.com/Simon-sud/App-download-estimator)** (this repo) | CLI scripts, SQLite pipeline, benchmarks import, OpenClaw `SKILL.md` |
| **[AppsFlyer-API-Tools](https://github.com/Simon-sud/AppsFlyer-API-Tools)** | Full data workbench — route `/app-estimator` UI talks to Go `:5001` and shares the same estimation model |

<p>
Use <strong>this repo</strong> for agent skills, scripting, and headless automation.<br/>
Use <strong>AppsFlyer-API-Tools</strong> when you need the React UI inside the broader AppsFlyer analytics stack.
</p>

<br/>

---

<h2 id="quick-start">Quick start</h2>

</div>

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

<div align="center">

<p>Or run the bundled example:</p>

</div>

```bash
bash examples/run_estimate.sh
```

<div align="center">

<br/>

---

<h2 id="openclaw-skill">OpenClaw skill</h2>

<p>Install as a workspace skill (copy or symlink the repo into your OpenClaw skills directory):</p>

</div>

```bash
# Example: install into default OpenClaw workspace
mkdir -p ~/.openclaw/workspace/skills
cp -R /path/to/App-download-estimator ~/.openclaw/workspace/skills/app-download-estimator
```

<div align="center">

<p>
The agent reads <a href="SKILL.md">SKILL.md</a> for triggers, CLI usage, and reporting rules. Requires <code>python3</code> on the host.
</p>

<p>See <a href="SKILL.md">SKILL.md</a> for full agent integration details.</p>

<br/>

---

<h2 id="project-layout">Project layout</h2>

</div>

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

<div align="center">

<br/>

---

<h2 id="core-commands">Core commands</h2>

<p><strong>Estimate downloads</strong> · <strong>Snapshot collection</strong> · <strong>Database pipeline</strong></p>

</div>

<details>
<summary align="center"><strong>Estimate downloads</strong></summary>

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

<div align="center">

- `--delta-ratings` is normalized to a **30-day window** by default
- Use `--snapshot-days 7` when your delta covers only 7 days
- Without benchmarks, returns a pure formula estimate

</div>

</details>

<details>
<summary align="center"><strong>Snapshot collection</strong></summary>

```bash
python3 scripts/rating_snapshot.py \
  --watchlist examples/watchlist.json \
  --limit 5
```

</details>

<details>
<summary align="center"><strong>Database pipeline</strong></summary>

```bash
python3 scripts/init_db.py
python3 scripts/run_pipeline.py --skip-calibration
python3 scripts/import_benchmarks.py --benchmark-dir benchmarks
python3 scripts/query_db.py stats
```

</details>

<div align="center">

<br/>

---

<h2 id="benchmark-csv">Benchmark CSV formats</h2>

<p><strong>Simple format</strong> (recommended):</p>

</div>

```csv
country,platform,app_id,package,bundle,app_name,category,category_name,chart_rank,downloads,report_start,report_end
US,android,,com.example.app,,Example,Finance,Finance / Banking,20,12000,2026-01-01,2026-01-31
```

<div align="center">

<p>
<strong>Intelligence export format</strong> — importer accepts vendor exports with an <code>App,App Name</code> header.<br/>
<strong>Only import files you are licensed to use.</strong> Do not commit proprietary exports to public repos.
</p>

<p>Sample file: <a href="examples/benchmarks/US_finance.sample.csv">examples/benchmarks/US_finance.sample.csv</a></p>

<br/>

---

<h2 id="model">Model</h2>

</div>

```text
monthly_downloads = delta_ratings_30d × K × maturity_beta × regional_factor
```

<div align="center">

<p>
When benchmark data is available, results may be capped by a <strong>rank-aware category waterline</strong> (<code>1.5 × waterline</code>).
</p>

<p>Coefficients: <a href="references/k_matrix.md">references/k_matrix.md</a></p>

| Variable | Purpose |
| :---: | :---: |
| `APP_ESTIMATOR_BENCHMARKS_DIR` | Override default `./benchmarks` directory |

<br/>

---

<h2 id="testing">Testing</h2>

</div>

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

<div align="center">

<br/>

---

<h2 id="agent-workflow">Agent workflow</h2>

<p>
1. Collect or query <code>total_ratings</code> and <code>delta_ratings</code> (or use <code>query_db.py app-inputs</code>)<br/>
2. Run <code>estimate_downloads.py</code><br/>
3. Present <code>est_monthly_downloads</code>, <code>confidence</code>, and <code>methodology</code> to the user
</p>

<br/>

---

<h2 id="license">License</h2>

<p>MIT — see <a href="LICENSE">LICENSE</a>.</p>

<br/>

---

<br/>

**Keep private in production**

<p>
Licensed intelligence exports · large paid-data watchlists · operational SQLite history
</p>

<br/>

<p>
  <a href="README.md"><strong>English</strong></a>
  &nbsp;·&nbsp;
  <a href="README.zh-CN.md">简体中文</a>
</p>

</div>

---
name: app-download-estimator
description: "Estimate mobile app download volume from public App Store / Google Play rating signals, with optional market-benchmark calibration. TRIGGER: user asks to estimate app downloads, analyze download trends, or benchmark competitor scale by country. Compatible with OpenClaw agent workflows."
metadata: {"openclaw": {"emoji": "📊", "requires": {"bins": ["python3"]}}}
---

# App Download Estimator (OpenClaw Skill)

When this skill is active, act as a mobile growth analyst. Estimate per-country downloads using public rating signals and the local CLI toolchain in `{baseDir}`.

## Data sources

1. **Public signals** — rating count, rating growth, category, chart rank (from store pages or `rating_snapshot.py`)
2. **Optional benchmarks** — user-provided CSV files under `{baseDir}/benchmarks/` (never assume proprietary data is present)

## Workflow

### Step 1 — Gather inputs

| Field | Description |
| --- | --- |
| `appid` | App identifier |
| `category` | Store category |
| `country` | ISO country code (e.g. US, VN, IN) |
| `total_ratings` | Lifetime rating count |
| `delta_ratings` | New ratings over the observation window |
| `rank` | Category chart rank (optional but improves waterline) |

If a local DB exists, prefer DB-backed inputs:

```bash
python3 {baseDir}/scripts/query_db.py app-inputs \
  --platform android \
  --package com.example.app \
  --country US
```

Use `recommended_inputs.delta_ratings` (already normalized to 30 days when available).

### Step 2 — Run estimator

```bash
python3 {baseDir}/scripts/estimate_downloads.py \
  --appid <ID> \
  --category "<Category>" \
  --country <CC> \
  --total-ratings <Total> \
  --delta-ratings <Delta> \
  --rank <Rank> \
  --benchmark-dir {baseDir}/benchmarks
```

Add `--snapshot-days N` when the observed delta is not over 30 days.

### Step 3 — Report to the user

Present a concise table per country:

- Estimated daily downloads
- Estimated monthly downloads
- Confidence (`high` / `medium` / `low`)
- Methodology (`pure_calculation`, `waterline_validated`, `waterline_capped`)

Always include the disclaimer: **heuristic estimate, not official store data.**

## Pipeline (optional)

```bash
python3 {baseDir}/scripts/init_db.py
python3 {baseDir}/scripts/run_pipeline.py --benchmark-dir {baseDir}/benchmarks
```

Daily collection:

```bash
python3 {baseDir}/scripts/run_daily_collect.py --watchlist {baseDir}/examples/watchlist.json
```

## Rules

- Do not expose internal server paths, credentials, or proprietary benchmark filenames in user-facing replies
- If `confidence` is `low`, state uncertainty explicitly
- One final message per user request; no tool-progress chatter on messaging channels
- Read [`references/k_matrix.md`](references/k_matrix.md) for coefficient semantics when explaining the model

## Documentation

- English: [`README.md`](README.md)
- 中文: [`README.zh-CN.md`](README.zh-CN.md)

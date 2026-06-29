<div align="center">

# 📊 App Download Estimator

**基于应用商店公开评分信号，估算移动应用下载量**

可选市场基准校准 · SQLite 快照流水线 · **兼容 OpenClaw Skill**

<br/>

<p>
  <a href="README.md">English</a>
  &nbsp;·&nbsp;
  <a href="README.zh-CN.md"><strong>简体中文</strong></a>
</p>

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](requirements.txt)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill%20Ready-5B6EE1)](SKILL.md)
[![AppsFlyer Workbench](https://img.shields.io/badge/AppsFlyer--API--Tools-UI%20集成-0A7BFF)](https://github.com/Simon-sud/AppsFlyer-API-Tools)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)](tests/)

<br/>

<p>
  <em>K 因子模型 · 成熟度与地区修正 · 排名水位线 · JSON CLI 输出</em>
</p>

<p>
  <a href="#快速开始">快速开始</a>
  &nbsp;·&nbsp;
  <a href="#openclaw-skill">OpenClaw</a>
  &nbsp;·&nbsp;
  <a href="#appsflyer-工作台">AppsFlyer UI</a>
  &nbsp;·&nbsp;
  <a href="#模型">模型</a>
  &nbsp;·&nbsp;
  <a href="#许可证">许可证</a>
</p>

<br/>

> **免责声明：** 输出为启发式估算，仅供研究与规划，不代表 App Store 或 Google Play 官方下载数据。

</div>

---

## 概述

**app-download-estimator** 是一套开源工具链，利用**公开评分数量与增速**估算应用月/日下载量，并可通过**你自备的、已获授权的市场基准 CSV** 做水位线校准。

本仓库**不包含任何专有数据集**。需要水位线校验时，请在本地放置你自己的 benchmark 文件。

| 能力 | 说明 |
| --- | --- |
| **估算** | `estimate_downloads.py` — K 因子模型，30 天评分增量归一化 |
| **采集** | `rating_snapshot.py` — iOS（iTunes Lookup）+ Android（`google-play-scraper`） |
| **流水线** | SQLite 快照、增速计算、基准导入、K 因子回测校准 |
| **Agent** | JSON 标准输出 + [`SKILL.md`](SKILL.md) 适配 [OpenClaw](https://docs.openclaw.ai) |

---

## AppsFlyer 工作台

本仓库是 [AppsFlyer-API-Tools](https://github.com/Simon-sud/AppsFlyer-API-Tools) 中 **App Estimator** 模块对应的**独立开源引擎**。

| 仓库 | 定位 |
| --- | --- |
| **[App-download-estimator](https://github.com/Simon-sud/App-download-estimator)**（本仓库） | CLI 脚本、SQLite 流水线、基准导入、OpenClaw `SKILL.md` |
| **[AppsFlyer-API-Tools](https://github.com/Simon-sud/AppsFlyer-API-Tools)** | 完整数据工作台 — `/app-estimator` 页面经 Go `:5001` 提供 UI，共用同一套估算模型 |

需要 Agent / 脚本 / 无头自动化时用**本仓库**；需要嵌入 AppsFlyer 分析栈的 React 界面时用 **AppsFlyer-API-Tools**。

---

## 快速开始

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

或运行内置示例：

```bash
bash examples/run_estimate.sh
```

---

## OpenClaw Skill

将本仓库安装为 OpenClaw 工作区技能（复制或软链到 skills 目录）：

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R /path/to/App-download-estimator ~/.openclaw/workspace/skills/app-download-estimator
```

Agent 通过 [`SKILL.md`](SKILL.md) 获取触发条件、CLI 用法与报告规范。运行环境需具备 `python3`。

完整集成说明见 [SKILL.md](SKILL.md)。

---

## 目录结构

```text
App-download-estimator/
├── SKILL.md                 # OpenClaw 技能定义
├── scripts/                 # CLI 与数据流水线
├── references/k_matrix.md   # 模型系数说明
├── examples/
│   ├── benchmarks/          # 合成示例 CSV（可公开）
│   ├── watchlist.json
│   └── run_estimate.sh
├── benchmarks/              # 你的授权基准数据（仅本地）
└── data/                    # SQLite 与快照（仅本地）
```

---

## 核心命令

<details>
<summary><strong>下载量估算</strong></summary>

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

- `--delta-ratings` 默认归一化到 **30 天窗口**
- 若增量覆盖 7 天，请加 `--snapshot-days 7`
- 无基准文件时仍返回纯公式估算结果

</details>

<details>
<summary><strong>评分快照采集</strong></summary>

```bash
python3 scripts/rating_snapshot.py \
  --watchlist examples/watchlist.json \
  --limit 5
```

</details>

<details>
<summary><strong>数据库流水线</strong></summary>

```bash
python3 scripts/init_db.py
python3 scripts/run_pipeline.py --skip-calibration
python3 scripts/import_benchmarks.py --benchmark-dir benchmarks
python3 scripts/query_db.py stats
```

</details>

---

## 基准 CSV 格式

**简单格式**（推荐）：

```csv
country,platform,app_id,package,bundle,app_name,category,category_name,chart_rank,downloads,report_start,report_end
US,android,,com.example.app,,Example,Finance,Finance / Banking,20,12000,2026-01-01,2026-01-31
```

**情报平台导出格式** — 支持以 `App,App Name` 为表头的厂商导出文件。**仅导入你已获授权的数据**，勿将专有导出提交到公开仓库。

示例文件：[`examples/benchmarks/US_finance.sample.csv`](examples/benchmarks/US_finance.sample.csv)

---

## 模型

```text
monthly_downloads = delta_ratings_30d × K × maturity_beta × regional_factor
```

存在基准数据时，结果可能受**与排名相关的水位线上限**约束（`1.5 × waterline`）。

系数说明：[`references/k_matrix.md`](references/k_matrix.md)

| 环境变量 | 用途 |
| --- | --- |
| `APP_ESTIMATOR_BENCHMARKS_DIR` | 覆盖默认 `./benchmarks` 目录 |

---

## 测试

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

---

## Agent 工作流

1. 采集或查询 `total_ratings`、`delta_ratings`（或使用 `query_db.py app-inputs`）
2. 运行 `estimate_downloads.py`
3. 向用户呈现 `est_monthly_downloads`、`confidence`、`methodology`

---

## 许可证

MIT — 见 [LICENSE](LICENSE)。

---

<div align="center">

<br/>

**生产环境请保持私有**

授权情报平台导出 · 基于付费数据的大型 watchlist · 运营中的 SQLite 历史库

<br/>

<p>
  <a href="README.md">English</a>
  &nbsp;·&nbsp;
  <a href="README.zh-CN.md"><strong>简体中文</strong></a>
</p>

</div>

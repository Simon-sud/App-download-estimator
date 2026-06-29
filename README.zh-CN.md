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
  <a href="#概述">概述</a>
  &nbsp;·&nbsp;
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

<br/>

---

<h2 id="概述">概述</h2>

<p>
<strong>app-download-estimator</strong> 是一套开源工具链，利用<strong>公开评分数量与增速</strong>估算应用月/日下载量，并可通过<strong>你自备的、已获授权的市场基准 CSV</strong> 做水位线校准。
</p>

<p>
本仓库<strong>不包含任何专有数据集</strong>。需要水位线校验时，请在本地放置你自己的 benchmark 文件。
</p>

| 能力 | 说明 |
| :---: | :---: |
| **估算** | `estimate_downloads.py` — K 因子模型，30 天评分增量归一化 |
| **采集** | `rating_snapshot.py` — iOS（iTunes Lookup）+ Android（`google-play-scraper`） |
| **流水线** | SQLite 快照、增速计算、基准导入、K 因子回测校准 |
| **Agent** | JSON 标准输出 + [`SKILL.md`](SKILL.md) 适配 [OpenClaw](https://docs.openclaw.ai) |

<br/>

---

<h2 id="appsflyer-工作台">AppsFlyer 工作台</h2>

<p>
本仓库是 <a href="https://github.com/Simon-sud/AppsFlyer-API-Tools">AppsFlyer-API-Tools</a> 中 <strong>App Estimator</strong> 模块对应的<strong>独立开源引擎</strong>。
</p>

| 仓库 | 定位 |
| :---: | :---: |
| **[App-download-estimator](https://github.com/Simon-sud/App-download-estimator)**（本仓库） | CLI 脚本、SQLite 流水线、基准导入、OpenClaw `SKILL.md` |
| **[AppsFlyer-API-Tools](https://github.com/Simon-sud/AppsFlyer-API-Tools)** | 完整数据工作台 — `/app-estimator` 页面经 Go `:5001` 提供 UI，共用同一套估算模型 |

<p>
需要 Agent / 脚本 / 无头自动化时用<strong>本仓库</strong>；<br/>
需要嵌入 AppsFlyer 分析栈的 React 界面时用 <strong>AppsFlyer-API-Tools</strong>。
</p>

<br/>

---

<h2 id="快速开始">快速开始</h2>

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

<p>或运行内置示例：</p>

</div>

```bash
bash examples/run_estimate.sh
```

<div align="center">

<br/>

---

<h2 id="openclaw-skill">OpenClaw Skill</h2>

<p>将本仓库安装为 OpenClaw 工作区技能（复制或软链到 skills 目录）：</p>

</div>

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R /path/to/App-download-estimator ~/.openclaw/workspace/skills/app-download-estimator
```

<div align="center">

<p>
Agent 通过 <a href="SKILL.md">SKILL.md</a> 获取触发条件、CLI 用法与报告规范。运行环境需具备 <code>python3</code>。
</p>

<p>完整集成说明见 <a href="SKILL.md">SKILL.md</a>。</p>

<br/>

---

<h2 id="目录结构">目录结构</h2>

</div>

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

<div align="center">

<br/>

---

<h2 id="核心命令">核心命令</h2>

<p><strong>下载量估算</strong> · <strong>评分快照采集</strong> · <strong>数据库流水线</strong></p>

</div>

<details>
<summary align="center"><strong>下载量估算</strong></summary>

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

- `--delta-ratings` 默认归一化到 **30 天窗口**
- 若增量覆盖 7 天，请加 `--snapshot-days 7`
- 无基准文件时仍返回纯公式估算结果

</div>

</details>

<details>
<summary align="center"><strong>评分快照采集</strong></summary>

```bash
python3 scripts/rating_snapshot.py \
  --watchlist examples/watchlist.json \
  --limit 5
```

</details>

<details>
<summary align="center"><strong>数据库流水线</strong></summary>

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

<h2 id="基准-csv-格式">基准 CSV 格式</h2>

<p><strong>简单格式</strong>（推荐）：</p>

</div>

```csv
country,platform,app_id,package,bundle,app_name,category,category_name,chart_rank,downloads,report_start,report_end
US,android,,com.example.app,,Example,Finance,Finance / Banking,20,12000,2026-01-01,2026-01-31
```

<div align="center">

<p>
<strong>情报平台导出格式</strong> — 支持以 <code>App,App Name</code> 为表头的厂商导出文件。<br/>
<strong>仅导入你已获授权的数据</strong>，勿将专有导出提交到公开仓库。
</p>

<p>示例文件：<a href="examples/benchmarks/US_finance.sample.csv">examples/benchmarks/US_finance.sample.csv</a></p>

<br/>

---

<h2 id="模型">模型</h2>

</div>

```text
monthly_downloads = delta_ratings_30d × K × maturity_beta × regional_factor
```

<div align="center">

<p>
存在基准数据时，结果可能受<strong>与排名相关的水位线上限</strong>约束（<code>1.5 × waterline</code>）。
</p>

<p>系数说明：<a href="references/k_matrix.md">references/k_matrix.md</a></p>

| 环境变量 | 用途 |
| :---: | :---: |
| `APP_ESTIMATOR_BENCHMARKS_DIR` | 覆盖默认 `./benchmarks` 目录 |

<br/>

---

<h2 id="测试">测试</h2>

</div>

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

<div align="center">

<br/>

---

<h2 id="agent-工作流">Agent 工作流</h2>

<p>
1. 采集或查询 <code>total_ratings</code>、<code>delta_ratings</code>（或使用 <code>query_db.py app-inputs</code>）<br/>
2. 运行 <code>estimate_downloads.py</code><br/>
3. 向用户呈现 <code>est_monthly_downloads</code>、<code>confidence</code>、<code>methodology</code>
</p>

<br/>

---

<h2 id="许可证">许可证</h2>

<p>MIT — 见 <a href="LICENSE">LICENSE</a>。</p>

<br/>

---

<br/>

**生产环境请保持私有**

<p>
授权情报平台导出 · 基于付费数据的大型 watchlist · 运营中的 SQLite 历史库
</p>

<br/>

<p>
  <a href="README.md">English</a>
  &nbsp;·&nbsp;
  <a href="README.zh-CN.md"><strong>简体中文</strong></a>
</p>

</div>

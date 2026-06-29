<div align="center">

# 贡献指南

<p>
  <a href="CONTRIBUTING.md">English</a>
  &nbsp;·&nbsp;
  <a href="CONTRIBUTING.zh-CN.md"><strong>简体中文</strong></a>
</p>

</div>

---

感谢为 **app-download-estimator** 做出贡献。

## 范围

- 变更应聚焦估算逻辑、数据流水线质量与文档。
- 勿提交专有基准导出、内部 watchlist 或客户相关数据。
- 修改估算行为时请补充或更新测试。

## 开发环境

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

## Pull Request 检查清单

- [ ] 本地测试通过
- [ ] 若 CLI 参数或数据格式有变，已更新 README（[EN](README.md) / [中文](README.zh-CN.md)）
- [ ] 未包含第三方授权数据集
- [ ] 估算输出仍包含公开免责声明

<div align="center">

<p>
  <a href="CONTRIBUTING.md">English</a>
  &nbsp;·&nbsp;
  <a href="CONTRIBUTING.zh-CN.md"><strong>简体中文</strong></a>
</p>

</div>

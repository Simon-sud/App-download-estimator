# Contributing

Thanks for helping improve app-download-estimator.

## Scope

- Keep changes focused on estimation logic, data pipeline quality, and documentation.
- Do not commit proprietary benchmark exports, internal watchlists, or customer-specific data.
- Add or update tests when changing estimator behavior.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

## Pull request checklist

- [ ] Tests pass locally
- [ ] README updated if CLI flags or data formats changed
- [ ] No licensed third-party datasets included
- [ ] Estimator output still includes the public disclaimer

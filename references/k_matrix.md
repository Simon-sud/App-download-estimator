# Industry K-factor reference (v1.0)

K is defined as estimated monthly downloads divided by new ratings over a 30-day window.

| Category | Base K | Notes |
| --- | ---: | --- |
| Finance / Banking | 8 | Many passive or prompted ratings |
| Finance / Trading | 120 | Lower rating propensity |
| Utilities | 180 | Very low rating rate |
| Social / Video | 35 | Medium rating rate |
| Games (Hyper-casual) | 40 | Prompt-heavy |
| Games (RPG/SLG) | 70 | Core players rate more |
| Travel / Food | 150 | Post-transaction ratings |
| Health & Fitness | 180 | Low rating rate |
| Games | 60 | Generic games bucket |
| Finance | 50 | Generic finance bucket |
| Default | 100 | Fallback |

## Maturity modifier (beta)

| Total ratings | beta |
| --- | ---: |
| < 1,000 | 1.5 |
| 1,000 – 9,999 | 1.0 |
| 10,000 – 99,999 | 0.5 |
| >= 100,000 | 0.1 |

## Regional factor

| Region | Factor |
| --- | ---: |
| TH, VN, ID, PH | 0.8 |
| JP, KR | 1.2 |
| BR, MX | 0.9 |
| US, GB, CA, DE | 1.0 |
| Other | 1.0 |

## Benchmark ceiling

When benchmark CSVs are available, the estimator compares the formula output against a category waterline derived from sorted benchmark downloads and the provided chart rank. If the raw estimate exceeds `1.5 × waterline`, the result is capped.

These coefficients are heuristic defaults. Use `calibrate_k.py` with your own licensed benchmark data to refine them.

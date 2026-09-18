# Market Morning Quality Gate Rules

## Completion gate

Schema Validation PASS alone is not a completion condition.

A daily update may be marked **完了（検証済み）** only after all of the following pass:

1. Schema Validation
2. Date integrity validation
3. Number and source audit
4. Cross-JSON consistency
5. Merge/publish to GitHub
6. GitHub Actions success
7. Vercel/Web production display validation

## Date integrity

Validate `data/report.json`, `data/market.json`, and `data/japan-stocks.json` together.

Required checks:
- `report_date`, `target_market_date`, and `updated_at` are internally consistent.
- Every required `market_date` is checked against the target market date appropriate to that asset/market.
- Partial refreshes must be detected. Example: US equities updated to the target date while Japan equities or FX remain stale.
- A stale value is FAIL by default.
- A stale value may be accepted only when there is a documented legitimate reason such as market holiday, unavailable data, or differing official publication schedule.
- If dates/bases differ, do not calculate or present a derived metric as if the inputs were synchronized. Mark it unavailable/pending instead.
- Do not infer or backfill missing numbers.

## Publication rule

Do not publish incomplete data to `main`. Use a quality-gate branch/PR first. If any gate fails, return to correction/research and re-run validation.

After merge, re-check production data and Web rendering. A pre-merge PASS does not replace the post-publish check.

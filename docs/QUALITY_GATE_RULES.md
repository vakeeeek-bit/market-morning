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

## Analysis discipline

### Unconfirmed-event interpretation
- Separate the fact that an event, meeting, negotiation, policy discussion, earnings release, or economic release has started/occurred from the confirmed outcome.
- Do not assign a positive or negative market direction merely because discussions started or an event occurred.
- When the outcome is not confirmed, keep the directional assessment neutral and express upside/downside implications as conditional scenarios.
- Preserve the sequence: confirmed fact -> confirmed outcome -> observed market reaction -> interpretation -> Japan-equity transmission.
- Final audit must explicitly ask: **Does any interpretation assign direction beyond the confirmed facts?** If yes, correct it before publication.

### Market-holiday and special-session handling
- Do not mechanically apply a normal trading-day template when Japanese cash equities are closed.
- Identify which relevant markets are actually open and performing price discovery, including OSE Nikkei 225/TOPIX futures, FX, commodities, or overseas markets as applicable.
- Never present the previous cash-session close as the current day's cash-market price.
- Clearly separate: previous-business-day observations, new information released during the closure, and reactions in markets that are actually tradable.
- On a Japanese cash-market holiday with OSE holiday trading, prioritize OSE futures as the initial domestic price-discovery signal while retaining appropriate caveats about cash-market confirmation.

## Final analytical audit

In addition to numerical, source, date, and cross-JSON checks, the pre-publication audit must verify:
1. Confirmed facts and interpretations are explicitly distinguishable.
2. No directional conclusion runs ahead of an unconfirmed event outcome.
3. Market reaction is described only where an actual traded-market reaction is observable.
4. The day's monitoring hierarchy reflects which markets are actually open.
5. Scenario-change conditions are tied to observable facts or prices rather than assumed outcomes.

Any failure in this analytical audit is a quality-gate FAIL and must be corrected before merge to `main`.

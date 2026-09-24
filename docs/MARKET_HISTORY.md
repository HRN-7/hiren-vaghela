# Observed market-price history

The existing historical reference and legacy `market_prices` table remain unchanged. Live AGMARKNET responses can now be saved in a new `observed_market_prices` table, keyed by state, district, market, crop, variety, grade, observation date and source.

## Enable

Configure `DATA_GOV_API_KEY` and PostgreSQL, then apply `backend/migrations/003_observed_market_prices.sql` to an existing database. `init_db.py` creates this new table if absent. No existing tables or historical observations are deleted or automatically reinterpreted.

Successful `/api/prices` responses save their actual observations when storage is configured. Failed storage does not hide the published prices. The command below can also be run by an operator or their existing daily scheduler:

```sh
.venv/bin/python backend/ingest_prices.py --crop Wheat --state Gujarat
```

Use `.venv\Scripts\python.exe` on Windows. Optional `--market "EXACT MARKET"` narrows collection. This command does not create a scheduler or paid hosting resource. Run one command per desired crop/state. The four supported crops remain Cotton, Wheat, Groundnut and Apple.

## Data rules

- Only records from the existing AGMARKNET adapter are collected. Supplied historical references, user quotes and unavailable feeds are never relabelled as live observations.
- Duplicated daily records update the same source row; they do not create extra history points. A corrected source quote updates its earlier observation.
- Invalid/non-finite prices, inconsistent min/modal/max ranges, future dates and records outside the requested state/crop/market are rejected.
- State and district remain part of the history scope, so similarly named markets are not combined. The market table retains published grades, including grades outside the app's self-declared A/B/C crop grading.
- `/api/prices/history` with state/district uses the new scoped table. Requests without a state retain the existing legacy-history behavior. There is no guessed state assignment for old records.
- The chart displays stored observations only and needs at least two observations. One fetched day cannot become a 30-day trend. Missing dates are not filled.
- The upstream adapter caps each response at 1,000 records. Its `truncated` flag is preserved; the collection command returns nonzero on truncation so an operator can narrow the market scope. This is not a historical backfill endpoint.

No live collection was performed here because the provider key and PostgreSQL are not configured. Tests use isolated synthetic observations and verify scope separation, corrections, invalid-row rejection, legacy compatibility and storage-outage behavior.

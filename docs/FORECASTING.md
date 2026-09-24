# Demand forecasting

The existing price model is unchanged. `backend/train_demand_model.py` adds a separate demand model, and the existing forecast API now includes `demand_details` plus its existing `demand` list. A price model and demand model can be available independently.

## Required real data

Supply a CSV for one exact crop, market, variety and grade with columns `date,demand_quintals`. Each row is the total **new buyer-requested quantity** recorded that day, in quintals, from a source with verified daily coverage. Deduplicate requests before aggregation and retain the same coverage definition across dates. Do not substitute arrivals, inventory, prices, repeated outstanding listings or completed sales. A current listing database is not automatically a historical demand dataset.

At least 120 consecutive observed days are required. An explicitly observed zero is valid; a missing day is unknown and is rejected. Duplicate dates, negative/non-finite quantities and future dates are rejected. The source argument records a public-safe source/coverage description, not credentials or individual buyer details.

From the project root after installing backend dependencies:

```sh
.venv/bin/python backend/train_demand_model.py --csv /path/to/verified-demand.csv --crop Apple --market "EXACT MARKET" --variety "EXACT VARIETY" --grade A --source "Verified provider; daily new requests; coverage description"
```

On Windows use `.venv\Scripts\python.exe` for the executable. Set `MODEL_DIRECTORY` on the training machine and backend consistently. No data or trained model is bundled; all synthetic observations used by tests stay in temporary test directories.

## Validation and serving

- XGBoost uses yesterday's observation, the observation seven days earlier, the previous seven-day mean, weekday and month.
- Validation uses the last 20% of dates, rounded to complete seven-day windows, with at least 28 held-out days. A model trained only on earlier data predicts each seven-day window recursively. Actual values within a window never become its prediction inputs. Completed earlier windows may seed the next window.
- The model must beat both a last-observation baseline and a weekly seasonal baseline by mean absolute error. A failed candidate exits with code 2 and does not overwrite an existing model.
- A passing candidate is refit on all observations and atomically written into `MODEL_DIRECTORY/demand/`. Serving verifies scope, validation metadata and recency. Artifacts older than two days, corrupt files or an unmatched scope yield an explicit unavailable response.
- The chart shows seven future dates after the current date in India. A one/two-day publication delay is bridged recursively, increasing the effective horizon and uncertainty beyond the seven-day validation horizon. Refresh source data daily. Validation error is historical error, not a confidence interval.
- Quantities describe new requests within the recorded source, not executed sales or all market demand. No forecast is a guarantee.

Joblib artifacts execute Python during loading: only use operator-created artifacts in the backend's trusted model directory. There is no user model-upload endpoint. Persist or securely restore that directory on backend deployment; an empty directory correctly disables forecasts.

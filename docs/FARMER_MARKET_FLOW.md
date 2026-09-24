# Farmer market recommendation flow

The saved crop drives Dashboard → Market prices → Market/transport/storage selections → AI Net Realization. Existing Buyer and FPO dashboards and account role checks are retained.

## Data requirements

- Backend `DATA_GOV_API_KEY` connects the Data.gov.in AGMARKNET resource. The key stays server-side. Missing, invalid or failed feeds produce an empty state, never an example market or PDF fallback.
- Location is resolved in India through `NOMINATIM_URL` (default OpenStreetMap Nominatim). Cached lookups are throttled to one per 1.1 seconds. Public service use must follow its usage policy; use an appropriate hosted geocoder for production volume.
- Nearby discovery uses the farmer's state and a 250 km straight-line bound, up to 12 candidate geocodes and 8 returned markets. Limited/truncated searches are labelled. It is not an exhaustive national optimum.
- Driving distances use `OSRM_URL`, not city-to-city straight-line multiplication. The mapped mandi/locality endpoint and vehicle route require confirmation. Failed routes remain unknown.
- Quotes and current storage compatibility require a connected provider at `PARTNER_DATA_URL` with server-only `PARTNER_API_KEY`. There is no universal tariff supplied by the AGMARKNET price feed. No unverified warehouse or old transport snapshot is passed into this recommendation engine.

## Prices and grades

The API adapter pages through at most 5,000 records; a larger response is marked truncated. It validates crop, state, positive finite prices, min/modal/max consistency and date. The recommendation engine selects the latest matching market/variety observation, excludes reports older than 7 days and future observations, and does not mix Rice with Paddy. A matching named variety is preferred; only generic/unreported varieties can be used as explicitly unconfirmed references when the named variety is absent. It never substitutes another named cultivar. Farmer A/B/C quality is self-declared and is not mapped to official AGMARK or FAQ grades.

Market prices are published modal prices, not guaranteed transaction prices. All resulting realization values are estimates. A stored-crop comparison holds that observed price constant; it is not a forecast of the future selling-date price.

## Service provider contract

`POST {PARTNER_DATA_URL}/recommendation-options` receives JSON:

- `crop`: name, variety, self-declared grade, quantity in quintals, location, selling date and quality parameters. Photos, notes, account IDs and contacts are excluded.
- `origin`: resolved coordinates and administrative location.
- `markets`: IDs, names, district/state, coordinates and price reporting date.
- `storage_days`: 0 for direct sale, otherwise 1–90 days.
- `request_fingerprint`: SHA-256 of the exact request context. The service must echo it to prevent using quotes from a different crop, load or route.

The response must echo `request_fingerprint` and contain arrays `transport`, `storage`, `charges`. Each record requires:

`id`, `name`, `market_id`, `source`, an HTTPS `source_url`, UTC/timezone-aware `updated_at`, `valid_until`, booleans `estimated` and `available`.

Quotes must be updated within 24 hours and unexpired. Missing fields, malformed prices, unavailable providers and a mismatched fingerprint are rejected.

Transport records additionally require:

- `vehicle`, `storage_id` (null for direct routes), `capacity_quintals`
- `rate_per_km`, `minimum_trip_cost`, `fixed_trip_cost`, `tolls_per_trip`
- `loading_per_quintal`, `unloading_per_quintal`
- `all_transport_costs_included`: true only when fuel, driver, tolls and all relevant transport expenses are accounted for.

The quoted kilometre rate must cover the provider's full billed journey for each estimated one-way route kilometre, including any return-leg billing; do not supply an incomplete outward-only tariff.

Storage records additionally require:

- `crops` (supported exact crop names), `compatible`, `capacity_quintals`, `lat`, `lon`
- `rate_per_quintal_day`, `handling_per_quintal`, `finance_per_quintal_day`, `loss_percent`, `minimum_days`
- `all_storage_costs_included`

Only available, crop-compatible facilities with enough capacity are suggested. Storage selection requires a transport quote for that facility's route. Road distances for farm → facility → market are added. Storage capacity and tariff are provider reports, not inferred from OpenStreetMap.

Charge records additionally require:

- `market_fee_percent`, `commission_per_quintal`, `other_per_quintal`, `other_description`
- `all_selling_costs_included`

Explicit verified zero is allowed; absent values are never replaced by zero. The provider must distinguish charges payable by the farmer from charges paid by other parties. Only supply a zero tariff when verified for this crop/market transaction.

See `backend/app/recommendations.py` Pydantic models for exact bounds and schema. Integration tests use isolated synthetic provider fixtures; these are not production fallback data.

## Calculation and ranking

Trips = ceil(quantity / vehicle capacity).

Transport / q = [trips × (max(minimum trip charge, fixed trip charge + distance × rate/km) + tolls/trip)] / quantity + loading/q + unloading/q.

Storage / q = max(requested days, minimum billed days) × (rent/q/day + finance/q/day) + handling/q + published price × expected loss%.

Market charges / q = published price × market fee% + commission/q.

Net Realization / q = market price − transport − storage − market charges − other costs.

Total expected realization = unrounded Net Realization × saved quantity. It is not profit after cultivation expenses.

The provider tariff's fixed and per-kilometre components must not duplicate one another. Costs and source metadata are displayed for each market. For complete quotes, the default selection considers eligible market + transport + storage combinations. The farmer may choose a different vehicle, facility or 2–3 markets. A winner is shown only if all selected options have complete costs. The complete subset can be ranked, but cannot establish the winner over unknown options.

Comparisons use short-lived server snapshots, owner and crop fingerprints, exact service/market IDs and provider expiry checks. No price or cost number supplied by the browser is trusted for ranking. Authenticated successful comparisons retain the existing saved-record behavior. Snapshots are process-local: a restart or a different worker returns a refresh message, never an invented result. Use a shared expiring cache before scaling to multiple workers if seamless snapshot continuity is needed.

## Crop photos

Desktop uploads accept validated JPEG, PNG or WebP files, at most 3, 5 MB each, and 20 megapixels. Mobile/tablet mode offers `getUserMedia` camera capture only, with no gallery/file input. HTTPS and camera permission are required. Vercel permits same-origin camera access; microphone remains disabled. Phone hardware capture still requires verification on an actual device.

Preview thumbnails include filenames, state and remove/replace/retake controls. Camera tracks stop on cancel, success and unmount. Saving persists owner-private photos in the backend. Upload retries are idempotent by crop/content hash. The backend verifies decoded image format and dimensions, rotates from EXIF before stripping metadata, and re-encodes JPEG. Photos are fetched with authorization, not public URLs. Preview-only photos are in memory and disappear on refresh.

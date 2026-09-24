# Verification record — 20 September 2026

This is a tested implementation and source handoff, not a claim that production authentication or deployment is complete.

## Completed checks

| Check | Result |
| --- | --- |
| Frontend TypeScript + Vite production build | Pass |
| Separate admin Vite production build | Pass |
| Backend tests | 29 passed; test database is isolated in-memory SQLite, not a production fallback |
| Frontend calculation/role/service-worker tests | 7 passed |
| Unauthenticated private crop/admin requests | Rejected |
| Cross-account crop read/edit/delete and owner injection | Rejected |
| Private crops absent from public discovery | Pass |
| Farmer prohibited from buyer dashboard API and buyer-only actions | Pass |
| Purchase visibility, seller-only acceptance and overbooking | Pass |
| FPO ownership/capacity checks | Pass |
| Farmer, Buyer and FPO menus | Separate routes, components and menu lists verified in browser |
| Unified Login/Register form | Role first; Email, Phone Number, Password together; Google option present; no Email/Phone tabs |
| Protected dashboard while signed out | Redirects to login |
| Four crop parameter forms | Cotton, Wheat, Groundnut and Apple fields observed in browser |
| Preview crop save | 50-qtl Cotton entry saved and appeared in buyer discovery count |
| Preview buyer demand | Form saved company/crop/quantity/price/date/contact and showed an unverified card |
| Preview FPO profile | 100-qtl capacity saved and appeared on its dashboard |
| Net calculator | Example: 2,250 − 80 − 25 − 75 = 2,070/qtl; total 103,500 for 50 qtl. Editing price to 2,300 updated net to 2,120 |
| Mobile login and dashboards | 390px iframe, 375px content viewport after scrollbar; no horizontal document overflow |
| Mobile sidebar | Open/close checked through visible navigation controls |
| Gujarati FPO view | Translated headings/forms/content observed; no horizontal overflow |
| Live Open-Meteo weather | Returned current data with source timestamp |
| FR8 transport adapter | Four current published reference rows returned; no vehicle availability implied |
| OSRM route adapter | Driving estimate returned |
| Storage adapter | Returned an explicit unavailable state when the provider could not refresh |

## Additional checks in this continuation

- Demand CSV rejects gaps, duplicate dates, negative/non-finite quantities and future dates; observed zeros are retained.
- Recursive validation does not use future actual values within a seven-day window. Exact scope, stale/corrupt artifacts and failed-candidate preservation are tested. Actual XGBoost fitting was exercised with test-only data; no test model was published.
- Queue tests cover atomic rollback, own opted-in device routing, retry timing, successful-send deduplication, expired-lease recovery, invalid-token removal, already-read cancellation and unsubscribe. Firebase sending was mocked.
- API checks reject another account's read/unsubscribe requests. Service-worker tests verify event tags and fixed profile navigation.
- Frontend production build passed after the changes. Forecast empty/unavailable states and Farmer navigation were observed in the browser. Mobile profile controls displayed the account requirement; 375px viewport/content widths matched with no horizontal overflow.
- All 72 files in the previous source archive still exist. Login/Register, separate role dashboard components and menus were not rewritten.
- Market-history tests verify duplicate/correction handling, invalid/out-of-scope rejection, state/district separation, legacy-history compatibility and continued published-price responses during a storage outage. Latest-published filters and unavailable states were checked in the browser.
- The configuration checker returned missing frontend API/Firebase and backend database/Firebase/CORS settings; it printed no credentials.

## Not completed / needs the operator's project access

- Real Firebase signup, email verification, email login, Google OAuth, phone OTP, phone linking, password reset and logout against the actual Firebase project. Code is wired, but the project configuration and test accounts were not supplied. Authentication buttons remain disabled when Firebase is unconfigured.
- A real PostgreSQL deployment and database migration. SQLAlchemy models and initial PostgreSQL DDL are supplied. A SQLite test does not verify production PostgreSQL concurrency; run the purchase/FPO concurrency checks on staging PostgreSQL before launch.
- Live buyer/FPO accounts, real transactions and administrator verification. All browser-created entries were clearly named QA preview data and stayed in memory.
- Current storage vacancy, tariffs and suitability: confirmed provider access is required. Public map listings alone are insufficient.
- eNAM authorized data access, AGMARKNET API key and a sufficiently long exact-scope price/arrival history.
- Validated models trained on genuine data. Both price and demand pipelines are supplied, but no real dataset/model is shipped. Demand forecasts remain unavailable until an exact-scope model passes validation and has recent observations.
- Live FCM delivery, real-device permission/unsubscribe/logout checks and PostgreSQL concurrent queue claims. Delivery is implemented, but Firebase and production PostgreSQL are not configured.
- WebMCP calculator action: registered conditionally in source, but this browser returned “modelContext is unavailable”; tool execution validation was not possible. UI calculation verification passed.
- Vercel frontend and separate admin deployment, Render backend and cloud PostgreSQL. The Vercel plugin is connected and returned empty teams/projects; its advertised deployment tool returned “Tool deploy_to_vercel not found”. The deployment CLI previously reported `login_required`. No public URL or domain ownership is claimed.

## Release checks after configuration

1. Use distinct Farmer, Buyer and FPO test accounts. Verify the selected role matches the account's stored role and each account is redirected to its own dashboard.
2. Attempt another role's direct URLs, crop IDs, purchase IDs and FPO request IDs. Confirm no private information is disclosed.
3. Finish Firebase verification/OTP/reset/Google tests on desktop and mobile, including invalid/expired OTP and cancelled popup states.
4. Check accepted purchase quantities and FPO capacity under concurrent requests against PostgreSQL.
5. Check feed timestamps, error handling and quoted units. Do not label unconfirmed values as live or show invented historical observations.
6. Verify domain DNS, TLS, backend CORS, health, public frontend access and independent admin authorization.
7. Verify real push delivery and token cleanup across sign-out, disabled permission and multiple accounts/devices. Verify concurrent queue workers against PostgreSQL.
8. Validate genuine demand-source coverage, baseline results and freshness before enabling forecast results.

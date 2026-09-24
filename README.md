# KrishiLink AI

Agricultural market intelligence for TechMates. React + Vite + Tailwind + Recharts, FastAPI, PostgreSQL and Firebase Authentication. The existing application has been continued without replacing its structure or green/white visual theme.

**Published frontend preview:** https://krishilink-ai-smoky.vercel.app/ — verified on 21 September 2026. Use **Explore preview** to open the dashboards. Real account login, persistent crop storage and live market recommendations still require Firebase, the hosted API/database and provider credentials. See `docs/PUBLISH_STATUS.md`.

## Latest changes — 21 September 2026

- Farmer crop entry now supports Cotton, Wheat, Groundnut and Rice with crop-specific varieties, quality fields and private photo attachments. Mobile capture uses the camera; desktop supports image upload.
- Farmer dashboard crop tabs and market views use the farmer's saved crops. Empty or unavailable feeds do not display invented crops, prices or markets.
- Recommendations now compare real AGMARKNET market observations with server-validated transport, storage and market-charge quotes. Farmers select actual markets and service options; unknown costs prevent a misleading winner. See `docs/FARMER_MARKET_FLOW.md` for provider setup and calculation rules.
- Production frontend build and all added recommendation, crop persistence and photo tests pass. Real provider credentials, real-account authentication and physical mobile camera capture still require production verification.

## Previous changes — 20 September 2026

- Added an independent demand-forecast training/serving pipeline with exact-scope, recency and seven-day holdout checks. The existing forecast card uses it when genuine validated data is available; no synthetic live forecasts are shipped.
- Added durable opt-in notification delivery, retry handling, FPO event notifications, device unsubscribe and owner-only **Mark as read** controls.
- Existing login, role dashboards, menus and business workflows are retained. All 72 files from the previous saved source remain present.
- Added state/district-aware recording of genuine market-price observations, correction-safe upserts and a daily collection command. See `docs/MARKET_HISTORY.md`.
- Added a read-only deployment configuration check plus forecasting/notification setup guides. **36 automated tests pass** (29 backend, 7 frontend).

- Role selection comes first: **Farmer, FPO, Buyer**. Email, Phone Number and Password appear together. There are no Email/Phone tabs. Google sign-in remains available.
- Three independent dashboards and navigation sets. Real accounts cannot enter another role's workspace by editing the URL.
- Email/password uses Firebase; phone sign-in uses OTP; registration can link an entered phone to the new email account. Email accounts must verify their email. Passwords are never stored by this backend.
- Farmer: crop entry, market analysis, buyers/FPO discovery, transport/storage, net calculator, recommendations, forecasts and sale requests.
- Buyer: own demands, available shared crops, purchase requests/history and profile.
- FPO: own profile, capacity/services and farmer requests. Accepting a request checks remaining capacity.
- Preview data is held in memory and is isolated from signed-in account data. Refresh clears it. The public preview is not an authentication bypass.
- Pages are loaded in separate bundles. English, Gujarati, Hindi and Marathi UI catalogs are included; provider names, measurements, user content and some technical source messages retain their original language.

## Run on Windows

Install Node.js 24 and Python 3.12 (the versions used for this build). Extract the project, then open this folder in VS Code.

Frontend, terminal 1:

```powershell
npm.cmd ci
Copy-Item .env.example .env
npm.cmd run dev
```

The preview runs at `http://localhost:4173`. With no Firebase configuration, sign-in is intentionally disabled; use **Explore preview**. Select another preview role in the top strip.

Backend, terminal 2:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.venv\Scripts\python.exe backend\init_db.py
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

`init_db.py` requires `DATABASE_URL` for a PostgreSQL database you control. Configure `.env` before running it. There is no production SQLite fallback. API documentation: `/api/docs` on the backend.

On macOS/Linux, use `python3 -m venv .venv`, `.venv/bin/python` and `npm`. `backend/requirements-linux.lock` records the verified Linux environment; use the portable requirements file on Windows.

## Route separation

| Account | Dashboard | Menu |
| --- | --- | --- |
| Farmer | `/app/farmer/dashboard` | Crops, markets, buyers, FPOs, transport, storage, calculator, recommendations, forecasts, sale requests, profile |
| Buyer | `/app/buyer/dashboard` | Post demand, available farmers, purchase history, profile |
| FPO | `/app/fpo/dashboard` | Manage storage/services, farmer requests, profile |

Replace `/app` with `/preview` for the nonpersistent demonstration. Previous `/app/dashboard` and other legacy routes redirect to the appropriate allowed role route.

The selected login role must match the account's stored role. A selector cannot grant a new role. Administrator access is never listed in public registration.

## Firebase configuration

1. Create/select the project's Firebase web app. Enable Email/Password, Google and Phone providers as required.
2. Add the final frontend and admin domains to Firebase Authentication's authorized domains. Configure SMS region settings/quotas and the Google provider's support email in Firebase.
3. Copy the public web-app configuration into the `VITE_FIREBASE_*` variables. Rebuild the Vercel app whenever build-time variables change.
4. Set `FIREBASE_PROJECT_ID` and the private service account JSON only on the backend. Do not commit service accounts, `.env` files or access tokens.
5. Set `VITE_FIREBASE_VAPID_KEY` and `VITE_FIREBASE_MESSAGING_SENDER_ID` for optional browser push. The backend now delivers queued account events while running. See `docs/NOTIFICATIONS.md` for migration, opt-in, retry and real-delivery verification.
6. Verify real signup, email verification, email login, linked phone OTP, Google OAuth, reset-password email and logout against your Firebase project before releasing real accounts.

Email/password sign-in uses email and password; **Send OTP** beside the phone field signs in with phone verification. Both sets of inputs remain visible. Google signs in through Firebase OAuth. A phone number entered at email registration is linked only after its OTP is verified. If linking fails, the email account still exists; verify the email and sign in rather than creating another account.

## Deploy to Vercel + Render

The Vercel project is **krishilink-ai**. Its verified public frontend URL is **https://krishilink-ai-smoky.vercel.app/**. The current release was deployed using Vercel's folder upload. No custom domain was configured.

1. Put this project in a Git repository under your control.
2. Provision PostgreSQL with SSL on your preferred cloud provider. Use least-privilege database credentials.
3. Connect the repository to Render. `render.yaml` describes the FastAPI service. Set the database, Firebase, CORS and provider secrets in Render. `init_db.py` creates the initial schema; review `backend/migrations/001_initial.sql` and the additive `002_push_deliveries.sql` / `003_observed_market_prices.sql` first. Back up existing databases before applying migrations.
4. Set `CORS_ORIGINS` to the exact frontend and separate admin HTTPS origins, comma-separated. Do not use a wildcard for authenticated production traffic.
5. In Vercel, import the root folder as project `krishilink-ai`, framework Vite. `vercel.json` supplies the build/output settings. Set `VITE_API_BASE_URL=https://YOUR_RENDER_SERVICE/api` plus the public Firebase variables.
6. Use `vercel login` on your own terminal if deploying through the CLI. Connecting the Vercel ChatGPT plugin does not sign in the deployment CLI. Then link the correct project and run `vercel --prod`. Never paste deployment tokens into a chat.
7. Deploy `admin/` as a **separate** Vercel project with its own Firebase/web API variables. If you own `krishilinkai.com`, attach `admin.krishilinkai.com` through its DNS controls. No domain was purchased or configured here.
8. Grant an administrator the Firebase custom claim `admin: true` through a trusted server-side operator process. The admin app and API both enforce it. Do not expose an endpoint for granting this claim.
9. Complete the real-account acceptance checks in `docs/ACCEPTANCE.md`, check provider errors and verify public access before announcing launch.

The frontend is published on the existing Vercel Hobby account. Firebase, Render, PostgreSQL and provider credentials are not configured, so this release is a public frontend preview. No paid service or custom domain was purchased. The admin app and FastAPI backend have not been deployed.

Run `.venv/bin/python backend/check_setup.py` (Windows: `.venv\Scripts\python.exe backend\check_setup.py`) to list missing configuration names without printing secrets. Use `--component frontend` or `--component backend` for a service-specific check. This is read-only and does not log in, create resources, send notifications or test actual credentials. Put private values directly into provider secret settings, never in chat or frontend build variables.

## Data and forecasting

Read `docs/DATA_SOURCES.md` for source URLs and freshness rules.

- Current weather: Open-Meteo. Maps: OpenStreetMap/OSRM, no Google Maps.
- AGMARKNET/data.gov adapter needs a server-side API key. New history automatically stores published observations for the exact state, district, crop, market, variety and grade when PostgreSQL is configured. The operator can also run `backend/ingest_prices.py`. There is no fabricated 30-day series.
- The supplied historical Apple report is not used by the Farmer Dashboard, Markets or recommendation flow. These pages require genuine API observations for the farmer's selected saved crop.
- FR8 publishes Surat–Mumbai full-truck rate references. These are shown with source/retrieval information, divided by the entered load only for a scenario estimate. They do not confirm current truck availability.
- Nearby storage uses map-directory data when available. Capacity, tariff and vacancy remain unknown without a confirmed provider feed. `PARTNER_DATA_URL` is a normalized adapter contract, not a claimed VRC/CWC API.
- Price model training uses XGBoost with a chronological holdout and naive baseline. Run `backend/train_model.py --help` with genuine daily data for one scope. No model is shipped as trained/validated. The independent demand pipeline is now implemented in `backend/train_demand_model.py`; it requires genuine daily buyer-request totals and publishes only a validated model. See `docs/FORECASTING.md`. Arrivals alone are not represented as demand.
- Market recommendations rank server-calculated net realization for 2–3 farmer-selected actual markets. Farmers do not enter market prices or selling costs. A winner is withheld when applicable costs are unknown, and a best selling date/buyer is not invented.
- Purchase requests are coordination records. Payments/delivery happen directly between the parties. A seller marks completion explicitly; the app does not process money.

## Check the build

```powershell
npm.cmd test
npm.cmd run build
.venv\Scripts\python.exe -m pytest backend\tests -q
npm.cmd --prefix admin ci
npm.cmd --prefix admin run build
```

The admin is a separate build, not a public role. Source + deployment configuration are provided; production authentication and hosted PostgreSQL still require your project setup. See `docs/ACCEPTANCE.md` for what was actually tested.

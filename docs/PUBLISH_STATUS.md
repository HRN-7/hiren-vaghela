# Published frontend — 21 September 2026

- Public website: https://krishilink-ai-smoky.vercel.app/
- Hosting: Vercel; project `krishilink-ai`, existing Hobby account.
- Deployment method: Vercel Drop to Deploy, using the verified production frontend build (29 files).
- Verified in a browser: public login page, role selectors, Explore preview navigation and Farmer dashboard. Published frontend assets loaded successfully.
- The preview starts with no saved crops and does not show invented crop prices or markets.
- Source is preserved in `KrishiLink-AI-source.zip`; the project structure and other role dashboards remain intact.

## Current scope

This is a **frontend preview**, not a completed real-account production launch. Preview changes are held in memory and clear on refresh.

Still required for real operations:

1. Firebase public frontend configuration and authorized domain, with the required authentication providers enabled.
2. Hosted FastAPI backend, PostgreSQL and server-side Firebase credentials; configure the frontend API URL and exact CORS origins.
3. Server-side Data.gov.in/AGMARKNET API key and current transport/storage/market-charge quote provider configuration. The UI does not invent missing market observations or costs.
4. Real-account and provider acceptance checks, plus physical mobile camera verification.

The backend, database and separate admin app were not deployed. No custom domain or paid service was purchased. Rebuild the frontend after adding build-time configuration; configuring Vercel variables alone does not modify this already compiled upload.

See `FARMER_MARKET_FLOW.md` for the data contract and recommendation calculations. See the root README for setup and deployment instructions.

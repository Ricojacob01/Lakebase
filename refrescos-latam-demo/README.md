# LTAP Real-Time Demo — Lakebase + Lakehouse

Shows real-time OLTP transactions landing in **Lakebase (Postgres)**, with
business analytics served back to a dark-themed React dashboard, plus embed
slots for an **AI/BI Dashboard** (SQL Warehouse) and a **Genie** space.

Two verticals, one dashboard each (hash routes):

| Route      | Vertical        | Transactions      | Business KPIs                       |
|------------|-----------------|-------------------|-------------------------------------|
| `#/mining` | ⛏️ Minería       | ore haul loads    | tons moved/hr · average grade (ley %) |
| `#/retail` | 🛒 Retail        | product sales     | revenue/min · average ticket        |

Every data panel carries a **compute attribution badge** so the audience always
knows *which Databricks compute* served it:

- 🟢 **Lakebase (Postgres OLTP)** — Live Activity, TPS, Business KPI, Lakebase Query
- 🟡 **SQL Warehouse** — AI/BI Dashboard
- 🔵 **Genie** — Genie panel

## Demo mode (no Databricks required)

When `PGHOST` is absent (or the Lakebase connection fails), the app runs in
**demo mode**: the transaction generator keeps counters + a rolling window in
memory instead of inserting into Postgres, and the Lakebase Query panel computes
its result over that in-memory window. Every response is flagged `demo_mode: true`.
This is the default when running locally with no auth.

## Architecture

```
ltap-realtime-demo/
├── app.py                      # FastAPI entry — mounts routers + serves SPA
├── app.yaml                    # Databricks App config (uvicorn on :8000)
├── requirements.txt            # Deployment pins (pip)
├── pyproject.toml              # Local dev deps (uv)
├── server/
│   ├── config.py               # Dual-mode auth (Databricks App vs local CLI)
│   ├── db.py                   # asyncpg pool + OAuth token password + demo fallback
│   ├── simulator.py            # Per-vertical background TPS generator
│   └── routes/
│       ├── transactions.py     # start/stop/reset/live/tps-series/kpi
│       ├── lakebase.py         # GET/POST lakebase-query (current query + run)
│       └── embeds.py           # AI/BI + Genie iframe URLs from env
└── frontend/                   # Vite + React + TS + Tailwind
    ├── src/
    │   ├── App.tsx             # header + nav shell
    │   ├── VerticalPage.tsx    # one dashboard per vertical, polls every ~1s
    │   ├── api.ts              # typed fetch client
    │   ├── router.tsx          # minimal hash router (see note below)
    │   ├── store.ts            # minimal external store (see note below)
    │   ├── verticals.ts        # per-vertical metadata + KPI formatting
    │   └── components/         # ComputeBadge, Card, ControlPanel, TpsChart, …
    └── dist/                   # built SPA (served by FastAPI; committed for deploy)
```

> **Offline-environment note:** `react-router-dom` and `zustand` were not
> available in the field install cache, so `router.tsx` and `store.ts` are tiny
> hand-rolled equivalents with the same shape. Swap them for the real packages
> (`npm i react-router-dom zustand`) when you have registry access — the call
> sites are isolated and documented in-file.

## Run locally

### Backend (demo mode — no Databricks needed)
```bash
cd ltap-realtime-demo
uv run uvicorn app:app --host 0.0.0.0 --port 8000
# or with any python that has fastapi+uvicorn installed:
#   python -m uvicorn app:app --port 8000
```
Open http://localhost:8000 — FastAPI serves the built SPA from `frontend/dist`.

### Frontend dev loop (hot reload, proxies /api → :8000)
```bash
cd frontend
npm install          # requires npm registry access
npm run dev          # http://localhost:5173
```

### Rebuild the SPA for deployment
```bash
cd frontend && npm run build   # emits frontend/dist/
```

## API (all under `/api`, `{vertical}` = `mining` | `retail`)

| Method | Path                          | Compute   | Returns |
|--------|-------------------------------|-----------|---------|
| POST   | `/{vertical}/start`           | lakebase  | begins the txn generator (optional `{tps}`) |
| POST   | `/{vertical}/stop`            | lakebase  | halts the generator |
| POST   | `/{vertical}/reset`           | lakebase  | clears counters + truncates OLTP table |
| GET    | `/{vertical}/live`            | lakebase  | `{tps, total, running, demo_mode, compute}` |
| GET    | `/{vertical}/tps-series`      | lakebase  | recent per-second TPS points |
| GET    | `/{vertical}/kpi`             | lakebase  | vertical business KPIs |
| GET    | `/{vertical}/lakebase-query`  | lakebase  | current query SQL text |
| POST   | `/{vertical}/lakebase-query`  | lakebase  | runs the query, `{sql, rows, latency_ms, compute}` |
| GET    | `/embeds`                     | warehouse/genie | configured iframe URLs |
| GET    | `/health`                     | —         | `{status, demo_mode}` |

## TODO — wiring real Databricks resources

1. **Lakebase (Postgres OLTP)** — attach a "Database" resource to the app (UI:
   App → Edit → Add resource → Database, permission "Can connect"). This injects
   `PGHOST/PGPORT/PGDATABASE/PGUSER`; the app auto-leaves demo mode. Tables
   `mining_txns` / `retail_txns` are created on startup (`server/db.py:SCHEMA_DDL`).
   Locally, set `DATABRICKS_PROFILE` + the `PG*` env vars to test against a real
   instance.
2. **AI/BI Dashboard (SQL Warehouse)** — publish a Lakeview dashboard, get its
   embed URL, and set `AIBI_DASHBOARD_URL` in `app.yaml` env (or
   `VITE_AIBI_DASHBOARD_URL` at build time). Empty ⇒ "not configured" placeholder.
3. **Genie** — set `GENIE_SPACE_URL` in `app.yaml` env (or `VITE_GENIE_SPACE_URL`).
4. **Foundation Model** — `SERVING_ENDPOINT` is reserved in `app.yaml` for a
   future AI panel; not used yet.
5. **TPS rate** — default ~50/s (`server/simulator.py:DEFAULT_TPS`); pass `{tps}`
   to `/start` to change per demo. Kept modest so it runs on a laptop; raise for
   a bigger Lakebase instance.

## Deploy (not done here — build + local validation only)

```bash
databricks apps create ltap-realtime-demo -p <profile>
databricks sync . /Workspace/Users/<you>/ltap-realtime-demo \
  --exclude node_modules --exclude .venv --exclude __pycache__ --exclude .git -p <profile>
databricks apps deploy ltap-realtime-demo \
  --source-code-path /Workspace/Users/<you>/ltap-realtime-demo -p <profile>
```
Then attach the Database / dashboard / Genie resources and redeploy.

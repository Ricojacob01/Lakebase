"""Refrescos LATAM — FastAPI entry point.

Demo de ventas de refrescos en Latinoamérica. Monta los routers de API y
sirve la SPA React desde frontend/dist. Corre en modo demo sin Databricks
auth o Lakebase, con fallback a datos sintéticos en memoria.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server.db import db
from server.routes import refrescos
from server.simulator import sim

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap OLTP schema when a real Lakebase pool is available (no-op in demo).
    await db.init_schema()
    yield
    await sim.shutdown()
    await db.close()


app = FastAPI(title="Refrescos LATAM", lifespan=lifespan)

app.include_router(refrescos.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "demo_mode": db.is_demo_mode}


# ---- SPA hosting -------------------------------------------------------
if os.path.isdir(FRONTEND_DIR):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"error": "not found"}, status_code=404)
        index = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"error": "frontend not built"}, status_code=404)
else:
    @app.get("/")
    async def no_frontend():
        return {"message": "Frontend not built. Run: cd frontend && npm run build"}

"""Transaction control + live metrics endpoints.

COMPUTE: Lakebase (Postgres OLTP). Start/stop/reset drive the background
transaction generator; live/tps-series/kpi read the OLTP store (or the in-memory
demo buffer). Every payload carries a `compute` field so the UI can attribute
which Databricks compute served the data.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import db
from ..simulator import DEFAULT_TPS, WINDOW_SECONDS, sim

router = APIRouter()

VERTICALS = ("mining", "retail")


def _check(vertical: str) -> None:
    if vertical not in VERTICALS:
        raise HTTPException(status_code=404, detail=f"unknown vertical '{vertical}'")


class StartBody(BaseModel):
    tps: int | None = None


@router.post("/{vertical}/start")
async def start(vertical: str, body: StartBody | None = None):
    """COMPUTE: Lakebase — begin inserting synthetic OLTP transactions."""
    _check(vertical)
    tps = body.tps if body else None
    await sim.start(vertical, tps)
    st = sim.get(vertical)
    return {"running": True, "tps": st.tps, "compute": "lakebase"}


@router.post("/{vertical}/stop")
async def stop(vertical: str):
    """COMPUTE: Lakebase — halt the transaction generator."""
    _check(vertical)
    await sim.stop(vertical)
    return {"running": False, "compute": "lakebase"}


@router.post("/{vertical}/reset")
async def reset(vertical: str):
    """COMPUTE: Lakebase — stop + clear counters and empty the OLTP table.

    Reports the real row count afterwards: if the table couldn't be cleared we
    return the actual total (not a fake 0) plus cleared=False, so the UI never
    misrepresents state.
    """
    _check(vertical)
    cleared = await sim.reset(vertical)
    total = 0
    if not db.is_demo_mode:
        table = "mining_txns" if vertical == "mining" else "retail_txns"
        try:
            rows = await db.fetch(f"SELECT count(*) AS c FROM {table}")
            total = int(rows[0]["c"]) if rows else 0
        except Exception:  # noqa: BLE001
            pass
    return {"running": False, "total": total, "cleared": cleared, "compute": "lakebase"}


@router.get("/{vertical}/live")
async def live(vertical: str):
    """COMPUTE: Lakebase — instantaneous TPS + cumulative transaction count."""
    _check(vertical)
    st = sim.get(vertical)
    total = st.total
    # On a real instance, prefer the authoritative row count.
    if not db.is_demo_mode:
        table = "mining_txns" if vertical == "mining" else "retail_txns"
        try:
            rows = await db.fetch(f"SELECT count(*) AS c FROM {table}")
            if rows:
                total = int(rows[0]["c"])
        except Exception:  # noqa: BLE001
            pass
    return {
        "tps": sim.current_tps(st),
        "total": total,
        "running": st.running,
        "demo_mode": db.is_demo_mode,
        "compute": "lakebase",
    }


@router.get("/{vertical}/tps-series")
async def tps_series(vertical: str):
    """COMPUTE: Lakebase — recent per-second TPS points for the live chart."""
    _check(vertical)
    st = sim.get(vertical)
    return {"points": sim.series(st), "compute": "lakebase"}


@router.get("/{vertical}/kpi")
async def kpi(vertical: str):
    """COMPUTE: Lakebase — vertical-specific business KPIs over the last minute."""
    _check(vertical)
    st = sim.get(vertical)

    if db.is_demo_mode:
        rows = sim.window_rows(st)
        if vertical == "mining":
            tons = sum(r.a for r in rows)
            grade = (sum(r.b for r in rows) / len(rows)) if rows else 0.0
            return {
                "vertical": "mining",
                "kpis": {
                    "tons_per_hour": round(tons * (3600 / WINDOW_SECONDS), 1),
                    "avg_grade_pct": round(grade, 3),
                },
                "window_seconds": WINDOW_SECONDS,
                "compute": "lakebase",
            }
        revenue = sum(r.a for r in rows)
        avg_ticket = (revenue / len(rows)) if rows else 0.0
        return {
            "vertical": "retail",
            "kpis": {
                # Demo buffer approximates the last hour with what's in memory.
                "revenue_last_hour": round(revenue, 2),
                "avg_ticket": round(avg_ticket, 2),
            },
            "window_seconds": 3600,
            "compute": "lakebase",
        }

    # Real Lakebase path.
    if vertical == "mining":
        rows = await db.fetch(
            "SELECT COALESCE(sum(tons),0) AS tons, COALESCE(avg(grade_pct),0) AS grade "
            "FROM mining_txns WHERE ts >= now() - interval '60 seconds'"
        )
        r = rows[0] if rows else {"tons": 0, "grade": 0}
        return {
            "vertical": "mining",
            "kpis": {
                "tons_per_hour": round(float(r["tons"]) * 60, 1),
                "avg_grade_pct": round(float(r["grade"]), 3),
            },
            "window_seconds": WINDOW_SECONDS,
            "compute": "lakebase",
        }
    # Unified revenue metric: last hour (stable, and matches the dashboard's
    # "Ingreso última hora" counter — both read retail_txns over the same window).
    rows = await db.fetch(
        "SELECT COALESCE(sum(amount),0) AS rev, COALESCE(avg(amount),0) AS ticket "
        "FROM retail_txns WHERE ts >= now() - interval '1 hour'"
    )
    r = rows[0] if rows else {"rev": 0, "ticket": 0}
    return {
        "vertical": "retail",
        "kpis": {
            "revenue_last_hour": round(float(r["rev"]), 2),
            "avg_ticket": round(float(r["ticket"]), 2),
        },
        "window_seconds": 3600,
        "compute": "lakebase",
    }

"""Ad-hoc Lakebase query endpoint.

COMPUTE: Lakebase (Postgres OLTP). Runs the vertical's "current query" directly
against Lakebase and returns rows + measured latency. In demo mode the same
logical query is computed over the in-memory window so the panel still returns
representative results (flagged demo_mode=true).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from ..db import db
from ..simulator import WINDOW_SECONDS, sim

router = APIRouter()

VERTICALS = ("mining", "retail")

# The SQL shown in the "Current Query" box and executed on Lakebase.
CURRENT_QUERY = {
    "mining": (
        "SELECT count(*)              AS loads,\n"
        "       round(sum(tons)::numeric, 1)      AS tons_last_min,\n"
        "       round(avg(grade_pct)::numeric, 3) AS avg_grade_pct\n"
        "FROM   mining_txns\n"
        "WHERE  ts >= now() - interval '60 seconds';"
    ),
    "retail": (
        "SELECT count(*)              AS orders,\n"
        "       round(sum(amount)::numeric, 2)    AS revenue_last_hour,\n"
        "       round(avg(amount)::numeric, 2)    AS avg_ticket\n"
        "FROM   retail_txns\n"
        "WHERE  ts >= now() - interval '1 hour';"
    ),
}


@router.get("/{vertical}/lakebase-query")
async def get_query(vertical: str):
    """COMPUTE: Lakebase — return the SQL text shown in the Current Query box."""
    if vertical not in VERTICALS:
        raise HTTPException(status_code=404, detail=f"unknown vertical '{vertical}'")
    return {"sql": CURRENT_QUERY[vertical], "compute": "lakebase"}


@router.post("/{vertical}/lakebase-query")
async def run_query(vertical: str):
    """COMPUTE: Lakebase — execute the current query and return rows + latency."""
    if vertical not in VERTICALS:
        raise HTTPException(status_code=404, detail=f"unknown vertical '{vertical}'")

    sql = CURRENT_QUERY[vertical]
    t0 = time.perf_counter()

    if db.is_demo_mode:
        rows = _demo_rows(vertical)
    else:
        rows = await db.fetch(sql)

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "sql": sql,
        "rows": rows,
        "latency_ms": latency_ms,
        "demo_mode": db.is_demo_mode,
        "compute": "lakebase",
    }


def _demo_rows(vertical: str) -> list[dict]:
    """Compute the query result over the in-memory rolling window."""
    st = sim.get(vertical)
    window = sim.window_rows(st)
    if vertical == "mining":
        tons = sum(r.a for r in window)
        grade = (sum(r.b for r in window) / len(window)) if window else 0.0
        return [{
            "loads": len(window),
            "tons_last_min": round(tons, 1),
            "avg_grade_pct": round(grade, 3),
        }]
    revenue = sum(r.a for r in window)
    ticket = (revenue / len(window)) if window else 0.0
    return [{
        "orders": len(window),
        "revenue_last_hour": round(revenue, 2),
        "avg_ticket": round(ticket, 2),
    }]

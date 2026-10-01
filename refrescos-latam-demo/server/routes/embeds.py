"""Embed config for the AI/BI Dashboard + Genie panels, per vertical.

COMPUTE: SQL Warehouse (AI/BI dashboard) and Genie. This endpoint just exposes
the configured iframe URLs (from env) so the frontend can render them; empty
URLs render a "not configured yet" placeholder.

Each vertical has its own AI/BI dashboard AND its own focused Genie space. The
UI keeps a single Genie panel; switching verticals swaps the embedded space
behind the scenes (same as the dashboard), so mining talks only mining and
retail only retail.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

router = APIRouter()

# Per-vertical AI/BI dashboard URLs (SQL Warehouse compute).
_DASHBOARD_ENV = {
    "mining": "AIBI_DASHBOARD_URL_MINING",
    "retail": "AIBI_DASHBOARD_URL_RETAIL",
}
# Per-vertical Genie space URLs.
_GENIE_ENV = {
    "mining": "GENIE_SPACE_URL_MINING",
    "retail": "GENIE_SPACE_URL_RETAIL",
}


@router.get("/{vertical}/embeds")
async def embeds(vertical: str):
    """COMPUTE: SQL Warehouse + Genie — return configured iframe URLs for a vertical."""
    if vertical not in _DASHBOARD_ENV:
        raise HTTPException(status_code=404, detail=f"unknown vertical: {vertical}")
    # Fall back to the generic env var if a per-vertical one is unset.
    dash = os.environ.get(_DASHBOARD_ENV[vertical]) or os.environ.get("AIBI_DASHBOARD_URL", "")
    genie = os.environ.get(_GENIE_ENV[vertical]) or os.environ.get("GENIE_SPACE_URL", "")
    return {
        "dashboard": {"url": dash, "compute": "warehouse"},
        "genie": {"url": genie, "compute": "genie"},
    }

"""Dual-mode Databricks auth + environment detection.

Two runtime modes:
  * Databricks App  -> service principal creds are auto-injected.
  * Local dev       -> uses a Databricks CLI profile (if configured).

None of this is *required* for the demo to run: when no Lakebase env vars and
no Databricks auth are present, the app falls back to demo mode (synthetic
in-memory data) and these helpers are simply never exercised.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

# Databricks Apps set DATABRICKS_APP_NAME on the runtime.
IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))


def get_workspace_client():
    """Return an authenticated WorkspaceClient (import lazily so the SDK is
    only needed when real auth is used)."""
    from databricks.sdk import WorkspaceClient

    if IS_DATABRICKS_APP:
        # Service principal credentials are injected into the environment.
        return WorkspaceClient()
    profile = os.environ.get("DATABRICKS_PROFILE")
    return WorkspaceClient(profile=profile) if profile else WorkspaceClient()


def get_oauth_token() -> Optional[str]:
    """OAuth token used as the Lakebase Postgres password.

    Returns None if auth cannot be resolved (caller should degrade to demo
    mode). Note: w.config.token is None for OAuth/U2M — use authenticate().
    """
    try:
        w = get_workspace_client()
        if w.config.token:
            return w.config.token
        auth_headers = w.config.authenticate()
        if auth_headers and "Authorization" in auth_headers:
            return auth_headers["Authorization"].replace("Bearer ", "")
    except Exception as e:  # noqa: BLE001 — demo must never crash on auth
        print(f"[config] OAuth token unavailable: {e}")
    return None


@lru_cache(maxsize=1)
def get_workspace_host() -> str:
    """Workspace host URL with https:// prefix (empty string if unknown)."""
    if IS_DATABRICKS_APP:
        # In Databricks Apps DATABRICKS_HOST is just the hostname, no scheme.
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host
    try:
        return get_workspace_client().config.host or ""
    except Exception:  # noqa: BLE001
        return ""

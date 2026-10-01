"""Lakebase (Postgres) async connection pool with OAuth token password.

Demo-mode contract: if PGHOST is absent (local dev, no Lakebase attached) OR
the connection fails, `is_demo_mode` flips to True and callers synthesize data
instead of touching Postgres. The rest of the app is written to never assume a
live pool exists.
"""
from __future__ import annotations

import os
from typing import Optional

from .config import get_oauth_token

# Schema already provisioned via infra/schema.sql in Lakebase.
# This app just connects and uses the existing tables: productos, tiendas, ventas, agent_memory.
SCHEMA_DDL = {}


class DatabasePool:
    """Lazy asyncpg pool. Safe to import and call in demo mode."""

    def __init__(self) -> None:
        self._pool = None  # type: ignore[var-annotated]
        self._demo_mode: Optional[bool] = None

    async def get_pool(self):
        # Decide demo-mode once we've actually tried.
        if not os.environ.get("PGHOST"):
            self._demo_mode = True
            return None

        if self._pool is None:
            try:
                import asyncpg  # imported lazily so demo mode has no hard dep

                # Prefer the PGPASSWORD auto-injected by the attached Lakebase
                # resource (scoped to the app SP's Postgres role); fall back to a
                # workspace OAuth token for local dev.
                token = os.environ.get("PGPASSWORD") or get_oauth_token()
                if not token:
                    raise RuntimeError("no OAuth token for Lakebase")
                self._pool = await asyncpg.create_pool(
                    host=os.environ["PGHOST"],
                    port=int(os.environ.get("PGPORT", "5432")),
                    database=os.environ["PGDATABASE"],
                    user=os.environ["PGUSER"],
                    password=token,
                    ssl="require",
                    min_size=2,
                    max_size=10,
                )
                self._demo_mode = False
            except Exception as e:  # noqa: BLE001
                print(f"[db] Lakebase connection failed, using demo mode: {e}")
                self._demo_mode = True
                self._pool = None
                return None
        return self._pool

    async def init_schema(self) -> None:
        """Create OLTP tables when a real pool is available (no-op in demo).

        Idempotent and tolerant: if the tables already exist but are owned by a
        different role (e.g. provisioned out-of-band), the CREATE INDEX IF NOT
        EXISTS can raise InsufficientPrivilege ("must be owner of table"). That
        is not fatal — the tables are already there — so we swallow it and let
        the app start. Any other error is re-raised.
        """
        pool = await self.get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            for ddl in SCHEMA_DDL.values():
                try:
                    await conn.execute(ddl)
                except Exception as e:  # noqa: BLE001
                    msg = str(e).lower()
                    if "must be owner" in msg or "already exists" in msg or "permission denied" in msg:
                        print(f"[db] init_schema: skipping (tables pre-exist): {e}")
                        continue
                    raise

    async def refresh_token(self) -> None:
        """Recreate the pool with a fresh OAuth token (call ~every 45 min)."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        await self.get_pool()

    @staticmethod
    def _is_auth_error(e: Exception) -> bool:
        """Lakebase OAuth tokens expire (~1h). When they do, acquiring a
        connection fails with an invalid-password/auth error — recoverable by
        recreating the pool with a fresh token."""
        name = type(e).__name__
        msg = str(e).lower()
        return (
            "InvalidPassword" in name
            or "InvalidAuthorizationSpecification" in name
            or "password authentication failed" in msg
            or "token" in msg and "expired" in msg
        )

    async def fetch(self, sql: str, *args):
        pool = await self.get_pool()
        if pool is None:
            return []
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *args)
                return [dict(r) for r in rows]
        except Exception as e:  # noqa: BLE001
            if not self._is_auth_error(e):
                raise
            # Token expired — refresh the pool with a new token and retry once.
            print("[db] auth error on fetch; refreshing Lakebase token")
            await self.refresh_token()
            pool = await self.get_pool()
            if pool is None:
                return []
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *args)
                return [dict(r) for r in rows]

    async def execute(self, sql: str, *args):
        pool = await self.get_pool()
        if pool is None:
            return None
        try:
            async with pool.acquire() as conn:
                return await conn.execute(sql, *args)
        except Exception as e:  # noqa: BLE001
            if not self._is_auth_error(e):
                raise
            print("[db] auth error on execute; refreshing Lakebase token")
            await self.refresh_token()
            pool = await self.get_pool()
            if pool is None:
                return None
            async with pool.acquire() as conn:
                return await conn.execute(sql, *args)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def is_demo_mode(self) -> bool:
        # If we haven't tried yet, infer from env (PGHOST presence).
        if self._demo_mode is None:
            return not bool(os.environ.get("PGHOST"))
        return self._demo_mode


db = DatabasePool()

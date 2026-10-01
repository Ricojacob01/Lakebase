"""Retail narrative endpoints — how an OLTP transaction is born.

Three origins share one table (retail_txns.source):
  * manual     — a clerk captures the sale in a classic app form.
  * agent      — a Foundation Model agent parses NL and calls register_sale.
  * simulation — the mass transaction generator (see simulator.py).

COMPUTE: Lakebase for the inserts + source-mix; the agentic parse itself runs on
a Foundation Model (model serving). Demo mode keeps everything in memory so the
screens work offline.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Deque, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import db
from ..llm import agentic_parse
from ..simulator import sim

router = APIRouter()

# In-memory fallback for agent conversation memory when Lakebase is absent
# (demo mode) — mirrors what the agent_memory Postgres table holds.
_demo_memory: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=200))


class ManualInsertBody(BaseModel):
    store_id: int
    product_id: int
    qty: int
    amount: float


class AgentInsertBody(BaseModel):
    message: str
    thread_id: str | None = None


async def _save_turn(thread_id: str, turn_idx: int, role: str,
                     content: str, tool_call: dict | None) -> None:
    """Persist one conversation turn as agent memory (Lakebase, keyed by
    thread_id). This is the agent's short-term memory: the app can rehydrate a
    thread with prior messages, reasoning and tool calls intact."""
    if db.is_demo_mode:
        _demo_memory[thread_id].append({
            "thread_id": thread_id, "turn_idx": turn_idx, "role": role,
            "content": content, "tool_call": tool_call,
        })
        return
    await db.execute(
        "INSERT INTO agent_memory (thread_id, turn_idx, role, content, tool_call) "
        "VALUES ($1, $2, $3, $4, $5)",
        thread_id, turn_idx, role, content,
        json.dumps(tool_call) if tool_call else None,
    )


async def _load_memory(thread_id: str) -> List[dict]:
    """Read back the conversation memory for a thread from Lakebase."""
    if db.is_demo_mode:
        return list(_demo_memory.get(thread_id, []))
    rows = await db.fetch(
        "SELECT turn_idx, role, content, tool_call, ts FROM agent_memory "
        "WHERE thread_id = $1 ORDER BY turn_idx",
        thread_id,
    )
    for r in rows:
        if isinstance(r.get("tool_call"), str):
            try:
                r["tool_call"] = json.loads(r["tool_call"])
            except (TypeError, ValueError):
                r["tool_call"] = None
        if r.get("ts") is not None and hasattr(r["ts"], "isoformat"):
            r["ts"] = r["ts"].isoformat()
    return rows


async def _insert_retail(store_id: int, product_id: int, qty: int, amount: float, source: str) -> dict:
    """Insert one retail txn with its origin. Returns the resulting row.

    Real mode: INSERT ... RETURNING against Lakebase. Demo mode: push to the
    in-memory buffer (so live panels + source-mix still move) and synthesize the
    row shape the UI expects.
    """
    if db.is_demo_mode:
        sim.record_external("retail", amount, qty, source)
        st = sim.get("retail")
        return {
            "txn_id": st.total,  # monotonic-ish demo id
            "store_id": store_id,
            "product_id": product_id,
            "qty": qty,
            "amount": round(float(amount), 2),
            "source": source,
        }
    rows = await db.fetch(
        "INSERT INTO retail_txns (store_id, product_id, qty, amount, source) "
        "VALUES ($1, $2, $3, $4, $5) "
        "RETURNING txn_id, ts, store_id, product_id, qty, amount, source",
        store_id,
        product_id,
        qty,
        round(float(amount), 2),
        source,
    )
    row = rows[0] if rows else {}
    # asyncpg returns Decimal/datetime — coerce to JSON-friendly primitives.
    if "amount" in row and row["amount"] is not None:
        row["amount"] = float(row["amount"])
    if "ts" in row and row["ts"] is not None:
        row["ts"] = row["ts"].isoformat()
    return row


@router.post("/retail/manual-insert")
async def manual_insert(body: ManualInsertBody):
    """COMPUTE: Lakebase — a clerk captures one sale (source='traditional')."""
    row = await _insert_retail(
        body.store_id, body.product_id, body.qty, body.amount, "traditional"
    )
    return {
        "row": row,
        "compute": "lakebase",
        "source": "traditional",
        "demo_mode": db.is_demo_mode,
    }


@router.post("/retail/agent-insert")
async def agent_insert(body: AgentInsertBody):
    """COMPUTE: Foundation Model (parse) + Lakebase (insert).

    NL message -> agent -> register_sale tool call -> INSERT with source='agent'.
    Returns the agent's reasoning + the executed tool call + the inserted row so
    the UI can tell the whole story.
    """
    thread_id = body.thread_id or "default"

    # Load prior conversation from Lakebase (the agent's memory) and feed it as
    # context so the agent keeps track across turns — e.g. "agrega todo" or
    # "1 de cada 1" resolve against products discussed earlier.
    existing = await _load_memory(thread_id)
    history = [
        {"role": t["role"], "content": t.get("content") or ""}
        for t in existing
    ]
    parsed = await agentic_parse(body.message, history)
    # The agent may register several products in one turn (one tool call each).
    tool_calls = parsed.get("tool_calls") or (
        [parsed["tool_call"]] if parsed.get("tool_call") else []
    )
    registered = bool(parsed.get("registered") and tool_calls)

    rows = []
    if registered:
        for tc in tool_calls:
            a = tc["arguments"]
            rows.append(await _insert_retail(
                a["store_id"], a["product_id"], a["qty"], a["amount"], "agent"
            ))

    # Persist both turns as agent memory in Lakebase (keyed by thread_id).
    base = (existing[-1]["turn_idx"] + 1) if existing else 0
    await _save_turn(thread_id, base, "user", body.message, None)
    await _save_turn(thread_id, base + 1, "assistant",
                     parsed["reasoning"], parsed.get("tool_call"))

    return {
        "reasoning": parsed["reasoning"],
        "tool_call": parsed.get("tool_call"),
        "tool_calls": tool_calls,
        "inserted_row": rows[0] if rows else None,
        "inserted_rows": rows,
        "registered": registered,
        "thread_id": thread_id,
        "compute": "lakebase",
        "source": "agent",
        "agent_demo": parsed.get("demo", False),
        "demo_mode": db.is_demo_mode,
    }


@router.get("/retail/agent-memory")
async def agent_memory(thread_id: str = "default"):
    """COMPUTE: Lakebase — read back the agent's conversation memory for a
    thread. Demonstrates Lakebase as the agent state/memory store (checkpointing
    by thread_id): prior messages, reasoning and tool calls persisted."""
    turns = await _load_memory(thread_id)
    return {
        "thread_id": thread_id,
        "turns": turns,
        "count": len(turns),
        "compute": "lakebase",
        "demo_mode": db.is_demo_mode,
    }


@router.delete("/retail/agent-memory")
async def clear_agent_memory(thread_id: str = "default"):
    """COMPUTE: Lakebase — wipe the agent's conversation memory for a thread.
    Lets the demo start a fresh conversation without lingering context."""
    if db.is_demo_mode:
        _demo_memory.pop(thread_id, None)
    else:
        await db.execute("DELETE FROM agent_memory WHERE thread_id = $1", thread_id)
    return {"thread_id": thread_id, "cleared": True, "compute": "lakebase"}


@router.get("/retail/source-mix")
async def source_mix():
    """COMPUTE: Lakebase — transaction-origin mix (traditional vs agent)."""
    counts = {"traditional": 0, "agent": 0}
    if db.is_demo_mode:
        st = sim.get("retail")
        for k, v in st.source_counts.items():
            counts[k] = counts.get(k, 0) + v
    else:
        rows = await db.fetch(
            "SELECT source, count(*) AS c FROM retail_txns GROUP BY source"
        )
        for r in rows:
            # Fold any legacy values into the two canonical origins.
            key = "agent" if r["source"] == "agent" else "traditional"
            counts[key] = counts.get(key, 0) + int(r["c"])
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "compute": "lakebase",
        "demo_mode": db.is_demo_mode,
    }

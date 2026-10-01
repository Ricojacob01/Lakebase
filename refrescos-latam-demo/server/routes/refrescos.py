"""Refrescos LATAM — endpoints for all three narrative screens.

Tab 1 (Ventas): manual-insert, productos, tiendas, recent, source-mix
Tab 2 (Agente): agent-insert, agent-memory management
Tab 3 (Dashboard): embeds, latest-order
Tab 4 (Autoescalado): analytics/postgres, analytics/lakehouse, events, clean

COMPUTE: Lakebase (Postgres OLTP) for Tabs 1, 2, and SQL Warehouse (Lakehouse) for Tab 3.
Demo mode keeps everything in memory.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import get_oauth_token
from ..db import db
from ..llm import agentic_parse
from ..simulator import sim

router = APIRouter()

# In-memory fallback for agent conversation memory when Lakebase is absent
# (demo mode) — mirrors what the agent_memory Postgres table holds.
_demo_memory: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=200))


class ManualInsertBody(BaseModel):
    tienda_id: int
    producto_id: int
    cantidad: int


class AgentInsertBody(BaseModel):
    message: str
    thread_id: Optional[str] = None


class StartBody(BaseModel):
    tps: Optional[int] = None


# ============================================================================
# TAB 1: VENTAS (Sales / OLTP transactions)
# ============================================================================

@router.get("/refrescos/productos")
async def get_productos():
    """Retorna el catálogo de productos (refrescos)."""
    if db.is_demo_mode:
        # Demo-mode catalog (from infra/seed_data.sql)
        return [
            {"producto_id": 1, "nombre": "Inca Kola 500ml", "marca": "Inca Kola", "pais": "Perú", "categoria": "Cola dorada", "presentacion": "500 ml", "precio": 0.90},
            {"producto_id": 2, "nombre": "Guaraná Antarctica 350ml", "marca": "Guaraná Antarctica", "pais": "Brasil", "categoria": "Guaraná", "presentacion": "350 ml lata", "precio": 0.75},
            {"producto_id": 3, "nombre": "Postobón Manzana 400ml", "marca": "Postobón", "pais": "Colombia", "categoria": "Manzana", "presentacion": "400 ml", "precio": 0.70},
            {"producto_id": 4, "nombre": "Colombiana 350ml", "marca": "Postobón", "pais": "Colombia", "categoria": "Kola champaña", "presentacion": "350 ml", "precio": 0.70},
            {"producto_id": 5, "nombre": "Jarritos Tamarindo 370ml", "marca": "Jarritos", "pais": "México", "categoria": "Tamarindo", "presentacion": "370 ml", "precio": 0.85},
            {"producto_id": 6, "nombre": "Jarritos Mandarina 370ml", "marca": "Jarritos", "pais": "México", "categoria": "Mandarina", "presentacion": "370 ml", "precio": 0.85},
            {"producto_id": 7, "nombre": "Bilz 350ml", "marca": "Bilz y Pap", "pais": "Chile", "categoria": "Fantasía", "presentacion": "350 ml", "precio": 0.80},
            {"producto_id": 8, "nombre": "Pap 350ml", "marca": "Bilz y Pap", "pais": "Chile", "categoria": "Fantasía", "presentacion": "350 ml", "precio": 0.80},
            {"producto_id": 9, "nombre": "Big Cola 3L", "marca": "Kola Real (AJE)", "pais": "Perú", "categoria": "Cola", "presentacion": "3 L", "precio": 1.60},
            {"producto_id": 10, "nombre": "Manzanita Sol 600ml", "marca": "Manzanita Sol", "pais": "México", "categoria": "Manzana", "presentacion": "600 ml", "precio": 0.95},
            {"producto_id": 11, "nombre": "Pomar Uva 350ml", "marca": "Pomar", "pais": "Argentina", "categoria": "Uva", "presentacion": "350 ml", "precio": 0.78},
            {"producto_id": 12, "nombre": "Pony Malta 330ml", "marca": "Pony Malta", "pais": "Colombia", "categoria": "Malta", "presentacion": "330 ml", "precio": 0.72},
        ]
    rows = await db.fetch("SELECT * FROM productos ORDER BY producto_id")
    for r in rows:
        if "precio" in r and r["precio"] is not None:
            r["precio"] = float(r["precio"])
    return rows


@router.get("/refrescos/tiendas")
async def get_tiendas():
    """Retorna el listado de tiendas (puntos de venta)."""
    if db.is_demo_mode:
        return [
            {"tienda_id": 1, "nombre": "Abarrotes Reforma", "ciudad": "Ciudad de México", "pais": "México", "region": "MX-Centro", "tipo": "tienda"},
            {"tienda_id": 2, "nombre": "Mayorista Guadalajara", "ciudad": "Guadalajara", "pais": "México", "region": "MX-Occidente", "tipo": "mayorista"},
            {"tienda_id": 3, "nombre": "Super Andino", "ciudad": "Bogotá", "pais": "Colombia", "region": "CO-Andina", "tipo": "supermercado"},
            {"tienda_id": 4, "nombre": "Tienda Paisa", "ciudad": "Medellín", "pais": "Colombia", "region": "CO-Antioquia", "tipo": "tienda"},
            {"tienda_id": 5, "nombre": "Bodega Miraflores", "ciudad": "Lima", "pais": "Perú", "region": "PE-Costa", "tipo": "tienda"},
            {"tienda_id": 6, "nombre": "Distribuidora Lima", "ciudad": "Lima", "pais": "Perú", "region": "PE-Costa", "tipo": "mayorista"},
            {"tienda_id": 7, "nombre": "Super Santiago", "ciudad": "Santiago", "pais": "Chile", "region": "CL-RM", "tipo": "supermercado"},
            {"tienda_id": 8, "nombre": "Mercado Paulista", "ciudad": "São Paulo", "pais": "Brasil", "region": "BR-Sudeste", "tipo": "mayorista"},
            {"tienda_id": 9, "nombre": "Almacén Porteño", "ciudad": "Buenos Aires", "pais": "Argentina", "region": "AR-Pampeana", "tipo": "tienda"},
            {"tienda_id": 10, "nombre": "Super Palermo", "ciudad": "Buenos Aires", "pais": "Argentina", "region": "AR-Pampeana", "tipo": "supermercado"},
        ]
    rows = await db.fetch("SELECT * FROM tiendas ORDER BY tienda_id")
    return rows


@router.get("/refrescos/recent")
async def get_recent(limit: int = 20):
    """Retorna ventas recientes, con join a productos y tiendas."""
    if limit > 1000:
        limit = 1000
    if db.is_demo_mode:
        # Demo: synthesize from in-memory buffer
        st = sim.estado
        rows = list(st.recientes)[-limit:]
        rows.reverse()
        # Return a simplified schema (demo data only has monto, cantidad, origen)
        return [
            {
                "venta_id": i,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r.ts)),
                "tienda": "Demo Tienda",
                "ciudad": "Demo",
                "pais": "Demo",
                "producto": "Demo Producto",
                "marca": "Demo",
                "cantidad": r.cantidad,
                "monto": r.monto,
                "origen": r.origen,
            }
            for i, r in enumerate(rows)
        ]
    sql = """
        SELECT v.venta_id, v.ts, t.nombre AS tienda, t.ciudad, t.pais,
               p.nombre AS producto, p.marca, v.cantidad, v.monto, v.origen
        FROM ventas v
        JOIN tiendas t ON v.tienda_id = t.tienda_id
        JOIN productos p ON v.producto_id = p.producto_id
        ORDER BY v.ts DESC
        LIMIT $1
    """
    rows = await db.fetch(sql, limit)
    for r in rows:
        if "monto" in r and r["monto"] is not None:
            r["monto"] = float(r["monto"])
        if "ts" in r and r["ts"] is not None and hasattr(r["ts"], "isoformat"):
            r["ts"] = r["ts"].isoformat()
    return rows


@router.post("/refrescos/manual-insert")
async def manual_insert(body: ManualInsertBody):
    """Registra una venta manual (origen='manual')."""
    if db.is_demo_mode:
        # Demo: lookup precio and synthesize the row
        from ..simulator import PRECIO_MAP
        precio = PRECIO_MAP.get(body.producto_id, 0.75)
        monto = round(body.cantidad * precio, 2)
        sim.record_external(body.cantidad, monto, "manual")
        return {
            "ok": True,
            "venta": {
                "tienda_id": body.tienda_id,
                "producto_id": body.producto_id,
                "cantidad": body.cantidad,
                "monto": monto,
                "origen": "manual",
            },
            "compute": "lakebase",
        }
    # Real DB: lookup precio from productos table, insert, return result
    rows = await db.fetch(
        "SELECT precio FROM productos WHERE producto_id = $1",
        body.producto_id,
    )
    if not rows:
        raise HTTPException(status_code=400, detail="Producto no existe")
    precio = float(rows[0]["precio"])
    monto = round(body.cantidad * precio, 2)
    
    venta_rows = await db.fetch(
        "INSERT INTO ventas (tienda_id, producto_id, cantidad, monto, origen) "
        "VALUES ($1, $2, $3, $4, $5) "
        "RETURNING venta_id, ts, tienda_id, producto_id, cantidad, monto, origen",
        body.tienda_id, body.producto_id, body.cantidad, monto, "manual"
    )
    venta = venta_rows[0] if venta_rows else {}
    if "monto" in venta:
        venta["monto"] = float(venta["monto"])
    if "ts" in venta and hasattr(venta["ts"], "isoformat"):
        venta["ts"] = venta["ts"].isoformat()
    
    sim.record_external(body.cantidad, monto, "manual")
    return {"ok": True, "venta": venta, "compute": "lakebase"}


@router.get("/refrescos/source-mix")
async def source_mix():
    """Retorna la mezcla de orígenes de ventas (manual, agente, simulacion, historico)."""
    counts = {"manual": 0, "agente": 0, "simulacion": 0, "historico": 0}
    if db.is_demo_mode:
        st = sim.estado
        for k, v in st.origen_counts.items():
            counts[k] = counts.get(k, 0) + v
    else:
        rows = await db.fetch(
            "SELECT origen, count(*) AS c FROM ventas GROUP BY origen"
        )
        for r in rows:
            origen = r["origen"]
            counts[origen] = counts.get(origen, 0) + int(r["c"])
    return {"counts": counts, "total": sum(counts.values())}


# ============================================================================
# TAB 2: AGENTE (Agentic NL capture + agent memory)
# ============================================================================

async def _save_turn(thread_id: str, turn_idx: int, role: str,
                     content: str, tool_call: Optional[dict]) -> None:
    """Persiste un turno de conversación como agent memory en Lakebase."""
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
    """Carga el historial de conversación de un thread desde Lakebase."""
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


async def _insert_venta_agente(tienda_id: int, producto_id: int, cantidad: int) -> dict:
    """Inserta una venta con origen='agente'. Retorna la fila creada."""
    if db.is_demo_mode:
        from ..simulator import PRECIO_MAP
        precio = PRECIO_MAP.get(producto_id, 0.75)
        monto = round(cantidad * precio, 2)
        sim.record_external(cantidad, monto, "agente")
        return {
            "tienda_id": tienda_id,
            "producto_id": producto_id,
            "cantidad": cantidad,
            "monto": monto,
            "origen": "agente",
        }
    # Real DB: lookup precio
    rows = await db.fetch(
        "SELECT precio FROM productos WHERE producto_id = $1",
        producto_id,
    )
    if not rows:
        raise HTTPException(status_code=400, detail="Producto no existe")
    precio = float(rows[0]["precio"])
    monto = round(cantidad * precio, 2)
    
    venta_rows = await db.fetch(
        "INSERT INTO ventas (tienda_id, producto_id, cantidad, monto, origen) "
        "VALUES ($1, $2, $3, $4, $5) "
        "RETURNING venta_id, ts, tienda_id, producto_id, cantidad, monto, origen",
        tienda_id, producto_id, cantidad, monto, "agente"
    )
    venta = venta_rows[0] if venta_rows else {}
    if "monto" in venta:
        venta["monto"] = float(venta["monto"])
    if "ts" in venta and hasattr(venta["ts"], "isoformat"):
        venta["ts"] = venta["ts"].isoformat()
    
    sim.record_external(cantidad, monto, "agente")
    return venta


@router.post("/refrescos/agent-insert")
async def agent_insert(body: AgentInsertBody):
    """Procesa un mensaje de NL, ejecuta registrar_venta si es apropiado."""
    thread_id = body.thread_id or "default"
    
    # Carga el historial para dar contexto al agente
    existing = await _load_memory(thread_id)
    history = [
        {"role": t["role"], "content": t.get("content") or ""}
        for t in existing
    ]
    
    parsed = await agentic_parse(body.message, history)
    tool_calls = parsed.get("tool_calls") or (
        [parsed["tool_call"]] if parsed.get("tool_call") else []
    )
    registered = bool(parsed.get("registered") and tool_calls)
    
    ventas = []
    if registered:
        for tc in tool_calls:
            a = tc["arguments"]
            venta = await _insert_venta_agente(a["tienda_id"], a["producto_id"], a["cantidad"])
            ventas.append(venta)
    
    # Persiste los turnos en agent_memory
    base = (existing[-1]["turn_idx"] + 1) if existing else 0
    await _save_turn(thread_id, base, "user", body.message, None)
    await _save_turn(thread_id, base + 1, "assistant",
                     parsed["reasoning"], parsed.get("tool_call"))
    
    return {
        "reasoning": parsed["reasoning"],
        "tool_call": parsed.get("tool_call"),
        "tool_calls": tool_calls,
        "ventas": ventas,
        "registered": registered,
        "thread_id": thread_id,
        "compute": "lakebase",
    }


@router.get("/refrescos/agent-memory")
async def agent_memory(thread_id: str = "default"):
    """Retorna el historial de conversación de un agente para un thread."""
    turns = await _load_memory(thread_id)
    return {
        "thread_id": thread_id,
        "turns": turns,
        "compute": "lakebase",
    }


@router.delete("/refrescos/agent-memory")
async def clear_agent_memory(thread_id: str = "default"):
    """Borra el historial de conversación de un thread."""
    if db.is_demo_mode:
        _demo_memory.pop(thread_id, None)
    else:
        await db.execute("DELETE FROM agent_memory WHERE thread_id = $1", thread_id)
    return {"ok": True, "thread_id": thread_id, "compute": "lakebase"}


# ============================================================================
# TAB 3: DASHBOARD (AI/BI + Genie embeds)
# ============================================================================

@router.get("/refrescos/embeds")
async def embeds():
    """Retorna URLs configuradas para dashboard e imputs de Genie."""
    import os
    dash = os.environ.get("AIBI_DASHBOARD_URL", "")
    genie = os.environ.get("GENIE_SPACE_URL", "")
    return {
        "dashboard": {"url": dash, "compute": "warehouse"},
        "genie": {"url": genie, "compute": "genie"},
    }


@router.get("/refrescos/latest-order")
async def latest_order():
    """Retorna la venta más reciente (desde Lakehouse si está disponible, sino Postgres)."""
    if db.is_demo_mode:
        # Demo: return a synthetic recent row
        return {
            "venta": {
                "venta_id": 999,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
                "tienda": "Demo Tienda",
                "producto": "Demo Refresco",
                "marca": "Demo",
                "cantidad": 10,
                "monto": 7.50,
            },
            "compute": "warehouse",
            "source": "demo",
        }
    
    # Try warehouse first (Lakehouse)
    uc_table = os.environ.get("UC_VENTAS_TABLE", "main.refrescos_latam.ventas")
    token = get_oauth_token()
    if token:
        try:
            from databricks import sql
            import os as os_module
            
            host = os_module.environ.get("DATABRICKS_HOST", "").replace("https://", "")
            if not host:
                raise RuntimeError("DATABRICKS_HOST not set")
            
            # Warehouse connection with short timeout
            conn = sql.connect(
                server_hostname=host,
                http_path="/sql/1.0/warehouses/" + os_module.environ.get("DATABRICKS_WAREHOUSE_ID", ""),
                access_token=token,
            )
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT v.venta_id, v.ts, t.nombre AS tienda, p.nombre AS producto, 
                       p.marca, v.cantidad, v.monto
                FROM {uc_table} v
                JOIN {uc_table.rsplit('.', 1)[0]}.tiendas t ON v.tienda_id = t.tienda_id
                JOIN {uc_table.rsplit('.', 1)[0]}.productos p ON v.producto_id = p.producto_id
                ORDER BY v.ts DESC LIMIT 1
            """)
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                return {
                    "venta": {
                        "venta_id": row[0],
                        "ts": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1]),
                        "tienda": row[2],
                        "producto": row[3],
                        "marca": row[4],
                        "cantidad": row[5],
                        "monto": float(row[6]),
                    },
                    "compute": "warehouse",
                    "source": uc_table,
                }
        except Exception as e:
            print(f"[latest_order] Warehouse query failed: {e}")
    
    # Fall back to Lakebase (Postgres)
    rows = await db.fetch("""
        SELECT v.venta_id, v.ts, t.nombre AS tienda_nombre, p.nombre AS producto_nombre,
               p.marca, v.cantidad, v.monto
        FROM ventas v
        JOIN tiendas t ON v.tienda_id = t.tienda_id
        JOIN productos p ON v.producto_id = p.producto_id
        ORDER BY v.ts DESC LIMIT 1
    """)
    if not rows:
        return {"venta": None, "compute": "lakebase", "source": "ventas"}
    r = rows[0]
    return {
        "venta": {
            "venta_id": int(r["venta_id"]),
            "ts": r["ts"].isoformat() if hasattr(r["ts"], "isoformat") else str(r["ts"]),
            "tienda": r["tienda_nombre"],
            "producto": r["producto_nombre"],
            "marca": r["marca"],
            "cantidad": int(r["cantidad"]),
            "monto": float(r["monto"]),
        },
        "compute": "lakebase",
        "source": "ventas",
    }


# ============================================================================
# TAB 4: AUTOESCALADO (Analytics — Postgres vs Lakehouse)
# ============================================================================

@router.post("/refrescos/analytics/postgres")
async def analytics_postgres():
    """Ejecuta la query pesada directamente en Lakebase (Postgres primary)."""
    sql = """
        SELECT t.pais, p.marca, date_trunc('day', v.ts) AS dia,
               COUNT(*) AS pedidos, SUM(v.cantidad * p.precio) AS ventas
        FROM ventas v 
        JOIN productos p ON v.producto_id=p.producto_id
        JOIN tiendas  t ON v.tienda_id=t.tienda_id
        GROUP BY 1,2,3 ORDER BY ventas DESC
    """
    
    if db.is_demo_mode:
        # Demo: fake latency + return a few rows
        await asyncio.sleep(0.1)
        sim.record_event("postgres", "Analítica en Postgres")
        return {
            "sql": sql,
            "row_count": 0,
            "latency_ms": 100,
            "compute": "lakebase",
            "top": [],
        }
    
    t0 = time.perf_counter()
    try:
        rows = await db.fetch(sql)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        
        sim.record_event("postgres", "Analítica en Postgres")
        
        # Convert Decimal/datetime to JSON-friendly types
        for r in rows:
            if "ventas" in r and r["ventas"] is not None:
                r["ventas"] = float(r["ventas"])
            if "dia" in r and r["dia"] is not None and hasattr(r["dia"], "isoformat"):
                r["dia"] = r["dia"].isoformat()
        
        return {
            "sql": sql,
            "row_count": len(rows),
            "latency_ms": latency_ms,
            "compute": "lakebase",
            "top": rows[:5],
        }
    except Exception as e:
        print(f"[analytics/postgres] Query failed: {e}")
        return {
            "sql": sql,
            "row_count": 0,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "compute": "lakebase",
            "top": [],
            "error": str(e),
        }


@router.post("/refrescos/analytics/lakehouse")
async def analytics_lakehouse():
    """Ejecuta la query pesada en el SQL warehouse (Lakehouse)."""
    uc_table = os.environ.get("UC_VENTAS_TABLE", "main.refrescos_latam.ventas")
    schema = uc_table.rsplit(".", 1)[0]  # e.g. "main.refrescos_latam"
    
    sql = f"""
        SELECT t.pais, p.marca, date_trunc('day', v.ts) AS dia,
               COUNT(*) AS pedidos, SUM(v.cantidad * p.precio) AS ventas
        FROM {uc_table} v
        JOIN {schema}.productos p ON v.producto_id=p.producto_id
        JOIN {schema}.tiendas  t ON v.tienda_id=t.tienda_id
        GROUP BY 1,2,3 ORDER BY ventas DESC
    """
    
    if db.is_demo_mode:
        await asyncio.sleep(0.15)
        sim.record_event("lakehouse", "Analítica en Lakehouse")
        return {
            "sql": sql,
            "row_count": 0,
            "latency_ms": 150,
            "compute": "warehouse",
            "top": [],
        }
    
    token = get_oauth_token()
    if not token:
        return {
            "sql": sql,
            "row_count": 0,
            "latency_ms": 0,
            "compute": "warehouse",
            "top": [],
            "error": "No OAuth token",
        }
    
    t0 = time.perf_counter()
    try:
        # NOTE: import as dbsql — `from databricks import sql` would shadow the
        # local `sql` query-string variable (breaking cursor.execute + the response).
        from databricks import sql as dbsql

        host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "")
        warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
        if not host or not warehouse_id:
            raise RuntimeError("DATABRICKS_HOST or DATABRICKS_WAREHOUSE_ID not set")

        conn = dbsql.connect(
            server_hostname=host,
            http_path=f"/sql/1.0/warehouses/{warehouse_id}",
            access_token=token,
        )
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        sim.record_event("lakehouse", "Analítica en Lakehouse")
        
        # Convert to dicts
        result_rows = []
        for row in rows[:5]:  # Top 5
            result_rows.append({
                "pais": str(row[0]) if row[0] is not None else None,
                "marca": str(row[1]) if row[1] is not None else None,
                "dia": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                "pedidos": int(row[3]) if row[3] is not None else 0,
                "ventas": float(row[4]) if row[4] is not None else 0,
            })
        
        return {
            "sql": sql,
            "row_count": len(rows),
            "latency_ms": latency_ms,
            "compute": "warehouse",
            "top": result_rows,
        }
    except Exception as e:
        print(f"[analytics/lakehouse] Query failed: {e}")
        return {
            "sql": sql,
            "row_count": 0,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "compute": "warehouse",
            "top": [],
            "error": str(e),
        }


@router.get("/refrescos/events")
async def get_events():
    """Retorna marcadores de eventos (anotaciones en el gráfico TPS)."""
    return {"events": sim.get_eventos()}


@router.post("/refrescos/clean")
async def clean_simulation():
    """Borra todas las ventas con origen='simulacion'."""
    if db.is_demo_mode:
        st = sim.estado
        # Filter out simulation rows from recientes
        st.recientes = deque(
            (r for r in st.recientes if r.origen != "simulacion"),
            maxlen=st.recientes.maxlen
        )
        st.origen_counts["simulacion"] = 0
        return {"deleted": 0, "compute": "lakebase"}
    
    try:
        # asyncpg execute() returns a status string like "DELETE 76".
        status = await db.execute("DELETE FROM ventas WHERE origen = $1", "simulacion")
        try:
            deleted = int(str(status).split()[-1])
        except (ValueError, IndexError, AttributeError):
            deleted = 0
        return {"deleted": deleted, "compute": "lakebase"}
    except Exception as e:
        print(f"[clean] DELETE failed: {e}")
        return {"deleted": 0, "error": str(e), "compute": "lakebase"}


# ============================================================================
# Transaction Control (Metrics + Simulation)
# ============================================================================

@router.post("/refrescos/start")
async def start_simulator(body: Optional[StartBody] = None):
    """Comienza la generación de ventas sintéticas."""
    tps = body.tps if body else None
    await sim.start(tps)
    st = sim.estado
    return {"running": True, "tps": st.tps, "compute": "lakebase"}


@router.post("/refrescos/stop")
async def stop_simulator():
    """Detiene la generación de ventas sintéticas."""
    await sim.stop()
    return {"running": False, "compute": "lakebase"}


@router.post("/refrescos/reset")
async def reset_simulator():
    """Detiene + borra contadores + vacía la tabla de simulación."""
    cleared = await sim.reset()
    total = 0
    if not db.is_demo_mode:
        try:
            rows = await db.fetch(f"SELECT count(*) AS c FROM ventas")
            total = int(rows[0]["c"]) if rows else 0
        except Exception:
            pass
    return {"running": False, "total": total, "cleared": cleared, "compute": "lakebase"}


@router.get("/refrescos/live")
async def live_metrics():
    """Retorna métricas en vivo: TPS, total de ventas, estado."""
    st = sim.estado
    total = st.total
    if not db.is_demo_mode:
        try:
            rows = await db.fetch(f"SELECT count(*) AS c FROM ventas")
            if rows:
                total = int(rows[0]["c"])
        except Exception:
            pass
    return {
        "tps": sim.current_tps(),
        "total": total,
        "running": st.corriendo,
        "demo_mode": db.is_demo_mode,
        "compute": "lakebase",
    }


@router.get("/refrescos/tps-series")
async def tps_series():
    """Retorna puntos de TPS para el gráfico de serie temporal (~120 puntos)."""
    return {"points": sim.series(), "compute": "lakebase"}


@router.get("/refrescos/kpi")
async def kpi():
    """Retorna KPIs de ventas en la última hora."""
    st = sim.estado
    if db.is_demo_mode:
        rows = sim.window_rows()
        ventas_total = sum(r.monto for r in rows)
        pedidos = len(rows)
        ticket_medio = (ventas_total / pedidos) if pedidos > 0 else 0.0
        return {
            "kpis": {
                "ventas_total": round(ventas_total, 2),
                "pedidos": pedidos,
                "ticket_medio": round(ticket_medio, 2),
            },
            "compute": "lakebase",
        }
    
    # Real DB
    rows = await db.fetch(
        "SELECT COUNT(*) AS pedidos, COALESCE(SUM(monto), 0) AS ventas_total, "
        "COALESCE(AVG(monto), 0) AS ticket_medio "
        "FROM ventas WHERE ts >= now() - interval '1 hour'"
    )
    r = rows[0] if rows else {"pedidos": 0, "ventas_total": 0, "ticket_medio": 0}
    return {
        "kpis": {
            "ventas_total": round(float(r["ventas_total"]), 2),
            "pedidos": int(r["pedidos"]),
            "ticket_medio": round(float(r["ticket_medio"]), 2),
        },
        "compute": "lakebase",
    }

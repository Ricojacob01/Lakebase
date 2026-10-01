"""Transaction generator for Refrescos LATAM.

A background asyncio task inserts synthetic OLTP transactions (ventas) at a configurable
rate (TPS). On a real Lakebase instance rows land in Postgres; in demo mode we
keep counters + recent-window buffers in memory so every panel still animates.

Specialization: single vertical "refrescos" (sodas across Latin America).
"""
from __future__ import annotations

import asyncio
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple

from .db import db

# Default demo rate. The template quotes 30k/s; we keep it modest so it truly
# runs on a laptop and (in real mode) doesn't hammer Lakebase.
DEFAULT_TPS = 50
TICK_SECONDS = 0.1  # generator wakes 10x/sec and inserts a proportional batch
SERIES_MAXLEN = 120  # ~2 minutes of 1s TPS points for the chart
WINDOW_SECONDS = 60  # KPI/query rolling window

# Real tienda/producto ids (from infra/seed_data.sql).
# Tiendas: 1..10 (cities across LATAM)
# Productos: 1..12 (emblemáticas de Latinoamérica, con precios en USD)
TIENDA_IDS = list(range(1, 11))  # 1..10
PRODUCTO_IDS = list(range(1, 13))  # 1..12

# Precio map: {producto_id: precio} — cached at startup.
# From infra/seed_data.sql
PRECIO_MAP = {
    1: 0.90, 2: 0.75, 3: 0.70, 4: 0.70, 5: 0.85,
    6: 0.85, 7: 0.80, 8: 0.80, 9: 1.60, 10: 0.95,
    11: 0.78, 12: 0.72,
}

# Origins
ORIGEN_SIMULACION = "simulacion"


@dataclass
class _Venta:
    """A synthetic venta (sale) kept in memory for demo-mode analytics."""

    ts: float
    monto: float  # total sale amount
    cantidad: int  # quantity sold
    origen: str = ORIGEN_SIMULACION  # manual | agente | simulacion


@dataclass
class EstadoSimulador:
    """State of the refrescos simulator."""

    nombre: str
    tps: int = DEFAULT_TPS
    corriendo: bool = False
    total: int = 0
    # (epoch_second, count) samples for computing instantaneous TPS.
    _sec_bucket_ts: int = 0
    _sec_bucket_count: int = 0
    tps_series: Deque[Tuple[float, int]] = field(
        default_factory=lambda: deque(maxlen=SERIES_MAXLEN)
    )
    # Rolling window of recent txns (demo-mode analytics only).
    recientes: Deque[_Venta] = field(default_factory=lambda: deque(maxlen=20000))
    # Cumulative transaction-origin mix (demo-mode; real mode reads Lakebase).
    origen_counts: Dict[str, int] = field(
        default_factory=lambda: {"manual": 0, "agente": 0, "simulacion": 0, "historico": 0}
    )
    # Event markers for analytics phases (postgres vs lakehouse)
    eventos: Deque[dict] = field(default_factory=lambda: deque(maxlen=20))
    _task: asyncio.Task | None = None

    def reset(self) -> None:
        self.total = 0
        self._sec_bucket_ts = 0
        self._sec_bucket_count = 0
        self.tps_series.clear()
        self.recientes.clear()
        self.origen_counts = {"manual": 0, "agente": 0, "simulacion": 0, "historico": 0}


class Simulador:
    """Simulador para Refrescos LATAM — inserta ventas sintéticas a una tasa de TPS configurable."""

    def __init__(self) -> None:
        self.estado: EstadoSimulador = EstadoSimulador("refrescos")

    # ---- lifecycle -----------------------------------------------------
    async def start(self, tps: int | None = None) -> None:
        """Comienza la generación de ventas sintéticas."""
        st = self.estado
        if tps is not None:
            st.tps = max(1, min(int(tps), 2000))
        if st.corriendo:
            return
        st.corriendo = True
        st._task = asyncio.create_task(self._run(st))

    async def stop(self) -> None:
        """Detiene la generación de ventas sintéticas."""
        st = self.estado
        st.corriendo = False
        if st._task is not None:
            st._task.cancel()
            try:
                await st._task
            except asyncio.CancelledError:
                pass
            st._task = None

    async def reset(self) -> bool:
        """Detiene el generador, borra contadores en memoria, y vacía la tabla OLTP.

        Retorna True si la tabla fue limpiada (o estamos en modo demo),
        False si la limpieza en BD falló.
        """
        await self.stop()
        st = self.estado
        st.reset()
        if db.is_demo_mode:
            return True
        try:
            await db.execute("DELETE FROM ventas WHERE origen = $1", ORIGEN_SIMULACION)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[sim] reset DELETE failed: {e}")
            return False

    async def shutdown(self) -> None:
        """Apaga el simulador antes de cerrar la app."""
        await self.stop()

    # ---- generation ----------------------------------------------------
    async def _run(self, st: EstadoSimulador) -> None:
        """Inserta `tps` filas/seg, distribuidas en 10 ticks/seg."""
        carry = 0.0
        try:
            while st.corriendo:
                carry += st.tps * TICK_SECONDS
                n = int(carry)
                carry -= n
                if n > 0:
                    await self._emit_batch(st, n)
                await asyncio.sleep(TICK_SECONDS)
        except asyncio.CancelledError:
            raise

    async def _emit_batch(self, st: EstadoSimulador, n: int) -> None:
        """Emite un lote de n ventas sintéticas."""
        now = time.time()
        rows = [self._synth(now) for _ in range(n)]

        # Actualiza contadores + TPS bucket.
        st.total += n
        sec = int(now)
        if sec != st._sec_bucket_ts:
            if st._sec_bucket_ts:
                st.tps_series.append((float(st._sec_bucket_ts), st._sec_bucket_count))
            st._sec_bucket_ts = sec
            st._sec_bucket_count = 0
        st._sec_bucket_count += n

        if db.is_demo_mode:
            for r in rows:
                tienda_id, producto_id, cantidad, monto = r
                venta = _Venta(now, float(monto), int(cantidad), ORIGEN_SIMULACION)
                st.recientes.append(venta)
                st.origen_counts[ORIGEN_SIMULACION] = st.origen_counts.get(ORIGEN_SIMULACION, 0) + 1
        else:
            await self._insert(rows)

    def record_external(self, cantidad: int, monto: float, origen: str) -> None:
        """Registra una venta manual/agente en los buffers demo para que los
        paneles en vivo, KPIs y mezcla de origen sigan animándose offline.
        No-op-safe."""
        st = self.estado
        now = time.time()
        venta = _Venta(now, float(monto), int(cantidad), origen)
        st.recientes.append(venta)
        st.total += 1
        st.origen_counts[origen] = st.origen_counts.get(origen, 0) + 1
        sec = int(now)
        if sec != st._sec_bucket_ts:
            if st._sec_bucket_ts:
                st.tps_series.append((float(st._sec_bucket_ts), st._sec_bucket_count))
            st._sec_bucket_ts = sec
            st._sec_bucket_count = 0
        st._sec_bucket_count += 1

    def record_event(self, phase: str, label: str) -> None:
        """Registra un evento para anotar el gráfico TPS (e.g. 'postgres', 'lakehouse')."""
        st = self.estado
        st.eventos.append({"t": int(time.time()), "phase": phase, "label": label})

    @staticmethod
    def _synth(now: float):
        """Sintetiza una venta: (tienda_id, producto_id, cantidad, monto)."""
        tienda_id = random.choice(TIENDA_IDS)
        producto_id = random.choice(PRODUCTO_IDS)
        cantidad = random.randint(1, 40)
        precio_unitario = PRECIO_MAP.get(producto_id, 0.75)
        monto = round(cantidad * precio_unitario, 2)
        return tienda_id, producto_id, cantidad, monto

    async def _insert(self, rows: list) -> None:
        """Inserta un lote de ventas sintéticas en la BD."""
        pool = await db.get_pool()
        if pool is None:
            return
        try:
            async with pool.acquire() as conn:
                await conn.executemany(
                    "INSERT INTO ventas (tienda_id, producto_id, cantidad, monto, origen) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    [
                        (tienda_id, producto_id, cantidad, monto, ORIGEN_SIMULACION)
                        for (tienda_id, producto_id, cantidad, monto) in rows
                    ],
                )
        except Exception as e:  # noqa: BLE001
            print(f"[sim] insert failed: {e}")

    # ---- read models (demo-mode) --------------------------------------
    def current_tps(self) -> int:
        """TPS instantáneo = count en el segundo completado más reciente."""
        st = self.estado
        if st.tps_series:
            return st.tps_series[-1][1]
        return st._sec_bucket_count if st.corriendo else 0

    def series(self) -> List[dict]:
        """Retorna puntos de TPS para el gráfico de la serie de tiempo."""
        st = self.estado
        pts = list(st.tps_series)
        # Incluye el segundo en progreso para que el gráfico se mueva en vivo.
        if st._sec_bucket_ts:
            pts = pts + [(float(st._sec_bucket_ts), st._sec_bucket_count)]
        return [{"t": int(t), "tps": c} for (t, c) in pts]

    def window_rows(self) -> List[_Venta]:
        """Retorna las ventas en la ventana de tiempo reciente (últimos WINDOW_SECONDS)."""
        st = self.estado
        cutoff = time.time() - WINDOW_SECONDS
        return [r for r in st.recientes if r.ts >= cutoff]

    def get_eventos(self) -> List[dict]:
        """Retorna marcadores de eventos (fases de analítica)."""
        return list(self.estado.eventos)


sim = Simulador()

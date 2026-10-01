import { useState, useEffect } from "react";
import { CheckCircle2, Droplet } from "lucide-react";
import { api, type Venta, type Tienda, type Producto } from "../api";
import { Card } from "../components/Card";
import { ComputeBadge } from "../components/ComputeBadge";
import { SourceTag } from "../components/SourceTag";

const POLL_INTERVAL_MS = 5000; // 5 seconds for recent sales refresh

// Tab 1 — Ventas. Sales form + recent sales table.
export function VentasPage() {
  const [tiendas, setTiendas] = useState<Tienda[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [tiendaId, setTiendaId] = useState<number | null>(null);
  const [productoId, setProductoId] = useState<number | null>(null);
  const [cantidad, setCantidad] = useState<string>("1");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<Venta[]>([]);
  const [flash, setFlash] = useState(false);

  // Load catalog on mount
  useEffect(() => {
    Promise.all([api.tiendas(), api.productos()])
      .then(([t, p]) => {
        setTiendas(t);
        setProductos(p);
        if (t.length > 0) setTiendaId(t[0].tienda_id);
        if (p.length > 0) setProductoId(p[0].producto_id);
      })
      .catch(() => {});
  }, []);

  // Poll recent sales
  useEffect(() => {
    const load = () => api.recent(20).then(setRecent).catch(() => {});
    load();
    const id = window.setInterval(load, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, []);

  const currentProduct = productos.find((p) => p.producto_id === productoId);
  const monto = currentProduct ? parseFloat(cantidad || "0") * currentProduct.precio : 0;

  const handleSubmit = async () => {
    setError(null);
    if (!tiendaId || !productoId || !cantidad) {
      setError("Por favor completa todos los campos.");
      return;
    }
    const qty = parseInt(cantidad, 10);
    if (qty <= 0) {
      setError("La cantidad debe ser mayor a 0.");
      return;
    }
    setBusy(true);
    try {
      await api.manualInsert({ tienda_id: tiendaId, producto_id: productoId, cantidad: qty });
      setRecent((prev) => {
        const updated = [...prev];
        return updated.slice(0, 19);
      });
      setCantidad("1");
      setFlash(true);
      window.setTimeout(() => setFlash(false), 1600);
      // Refresh recent sales
      api.recent(20).then(setRecent).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al registrar la venta");
    } finally {
      setBusy(false);
    }
  };

  const selectCls =
    "rounded-lg border border-ink-border bg-ink-900 px-3 py-2 text-sm text-gray-100 outline-none transition focus:border-accent-cyan";
  const inputCls =
    "tnum rounded-lg border border-ink-border bg-ink-900 px-3 py-2 text-sm text-gray-100 outline-none transition focus:border-accent-cyan";

  const formatter = new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "USD",
  });

  return (
    <div className="mx-auto grid max-w-[1100px] grid-cols-1 gap-3 p-3 lg:grid-cols-2">
      <Card title="Registrar venta" badge={<ComputeBadge kind="lakebase" short />}>
        <div className="mb-4 flex items-center gap-2 text-gray-400">
          <Droplet size={14} />
          <span className="text-xs">Formulario de venta · Refrescos LATAM</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {/* Tienda */}
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-gray-400">Tienda</span>
            <select
              value={tiendaId ?? ""}
              onChange={(e) => setTiendaId(Number(e.target.value))}
              className={selectCls}
            >
              {tiendas.map((t) => (
                <option key={t.tienda_id} value={t.tienda_id}>
                  {t.nombre} · {t.ciudad}
                </option>
              ))}
            </select>
          </label>

          {/* Producto */}
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-gray-400">Producto</span>
            <select
              value={productoId ?? ""}
              onChange={(e) => setProductoId(Number(e.target.value))}
              className={selectCls}
            >
              {productos.map((p) => (
                <option key={p.producto_id} value={p.producto_id}>
                  {p.nombre} · {p.marca}
                </option>
              ))}
            </select>
          </label>

          {/* Cantidad */}
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-gray-400">Cantidad</span>
            <input
              type="number"
              inputMode="numeric"
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
              className={inputCls}
            />
          </label>

          {/* Monto (computed) */}
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-gray-400">Monto</span>
            <div className={inputCls + " flex items-center justify-between pointer-events-none"}>
              <span className="text-gray-100">{formatter.format(monto)}</span>
            </div>
          </label>
        </div>

        {error && (
          <div className="mt-3 rounded-lg border border-accent-red/40 bg-accent-red/10 px-3 py-2 text-xs text-accent-red">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={busy}
          className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-accent-green px-3 py-2.5 text-sm font-semibold text-black transition hover:brightness-110 disabled:opacity-40"
        >
          <CheckCircle2 size={16} /> {busy ? "Registrando…" : "Registrar venta"}
        </button>

        {flash && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-accent-green/40 bg-accent-green/10 px-3 py-2 text-xs text-accent-green">
            <CheckCircle2 size={14} /> Venta registrada en Lakebase.
          </div>
        )}
      </Card>

      <Card title="Ventas recientes" badge={<ComputeBadge kind="lakebase" short />}>
        {recent.length === 0 ? (
          <div className="rounded-lg border border-dashed border-ink-border bg-ink-900/60 px-3 py-8 text-center text-xs text-gray-500">
            Registra una venta para verla aquí.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-ink-border">
            <table className="w-full text-left text-sm">
              <thead className="bg-ink-800 text-gray-400">
                <tr>
                  <th className="px-3 py-2 font-medium">Producto</th>
                  <th className="px-3 py-2 font-medium">Marca</th>
                  <th className="px-3 py-2 font-medium">Tienda</th>
                  <th className="px-3 py-2 font-medium">Ciudad</th>
                  <th className="px-3 py-2 font-medium">Cant.</th>
                  <th className="px-3 py-2 font-medium">Monto</th>
                  <th className="px-3 py-2 font-medium">Origen</th>
                  <th className="px-3 py-2 font-medium">Hora</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((row, i) => (
                  <tr key={i} className="border-t border-ink-border">
                    <td className="px-3 py-2 text-gray-200">{row.producto || "—"}</td>
                    <td className="px-3 py-2 text-gray-200">{row.marca || "—"}</td>
                    <td className="px-3 py-2 text-gray-200">{row.tienda || "—"}</td>
                    <td className="px-3 py-2 text-gray-200">{row.ciudad || "—"}</td>
                    <td className="tnum px-3 py-2 text-gray-200">{row.cantidad}</td>
                    <td className="tnum px-3 py-2 text-gray-200">
                      {formatter.format(row.monto)}
                    </td>
                    <td className="px-3 py-2">
                      <SourceTag source={row.origen || "manual"} />
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-400">
                      {row.ts
                        ? new Date(row.ts).toLocaleTimeString("es-MX", {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

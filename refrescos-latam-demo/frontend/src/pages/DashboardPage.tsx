import { useEffect, useState } from "react";
import { LayoutDashboard, Package } from "lucide-react";
import { api, type EmbedsResp, type LatestOrderResp } from "../api";
import { config } from "../config";
import { Card, Stat } from "../components/Card";
import { ComputeBadge } from "../components/ComputeBadge";
import { EmbedPanel } from "../components/EmbedPanel";

const POLL_MS = 3000; // Poll latest order every 3 seconds

// Tab 3 — Dashboard. AI/BI dashboard + latest order card.
export function DashboardPage() {
  const [embeds, setEmbeds] = useState<EmbedsResp | null>(null);
  const [latestOrder, setLatestOrder] = useState<LatestOrderResp | null>(null);

  useEffect(() => {
    api.embeds().then(setEmbeds).catch(() => setEmbeds(null));
  }, []);

  // Poll latest order
  useEffect(() => {
    const load = () => api.latestOrder().then(setLatestOrder).catch(() => {});
    load();
    const id = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(id);
  }, []);

  const formatter = new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "USD",
  });

  return (
    <div className="grid h-[calc(100vh-7rem)] grid-cols-1 gap-3 p-3 lg:grid-cols-3">
      {/* Main dashboard */}
      <div className="lg:col-span-2 min-h-0">
        <EmbedPanel
          title="Tablero AI/BI · Refrescos LATAM"
          kind="warehouse"
          url={embeds?.dashboard?.url || config.aibiDashboardUrl}
          icon={<LayoutDashboard size={28} />}
          hint="Define VITE_AIBI_DASHBOARD_URL para embeber un tablero AI/BI del SQL Warehouse."
        />
      </div>

      {/* Latest order card */}
      <div className="min-h-0 flex flex-col">
        <Card title="Último pedido" badge={<ComputeBadge kind="warehouse" short />}>
          {latestOrder ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 text-gray-400 mb-2">
                <Package size={14} />
                <span className="text-xs">Leído del lakehouse en tiempo real</span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-gray-500">ID Venta</div>
                  <div className="text-sm font-mono text-gray-200">
                    {latestOrder.venta.venta_id ?? "—"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wide text-gray-500">Hora</div>
                  <div className="text-sm text-gray-200">
                    {latestOrder.venta.ts
                      ? new Date(latestOrder.venta.ts).toLocaleTimeString("es-MX", {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })
                      : "—"}
                  </div>
                </div>
              </div>

              <div className="border-t border-ink-border pt-2">
                <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">
                  Producto
                </div>
                <div className="text-sm text-gray-200">{latestOrder.venta.producto || "—"}</div>
                <div className="text-xs text-gray-400">
                  {latestOrder.venta.marca || "—"}
                </div>
              </div>

              <div className="border-t border-ink-border pt-2">
                <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">
                  Tienda
                </div>
                <div className="text-sm text-gray-200">{latestOrder.venta.tienda || "—"}</div>
                <div className="text-xs text-gray-400">
                  {latestOrder.venta.ciudad || "—"} · {latestOrder.venta.pais || "—"}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 border-t border-ink-border pt-2">
                <Stat
                  label="Cantidad"
                  value={latestOrder.venta.cantidad}
                  accent="text-accent-cyan"
                />
                <Stat
                  label="Monto"
                  value={formatter.format(latestOrder.venta.monto)}
                  accent="text-accent-amber"
                />
              </div>

              <div className="text-[10px] text-gray-500 mt-2 p-2 rounded-lg bg-ink-800/30">
                Fuente: main.refrescos_latam.ventas
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-ink-border bg-ink-900/60 px-3 py-8 text-center text-xs text-gray-500">
              Esperando el primer pedido del lakehouse…
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

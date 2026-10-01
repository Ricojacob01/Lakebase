import { useEffect, useState } from "react";
import { GitMerge } from "lucide-react";
import { api, type SourceMixResp } from "../api";
import { Card } from "./Card";
import { ComputeBadge } from "./ComputeBadge";

// "Origen de ventas" — shows the mix of different sources (manual, agente, simulacion, historico)
// landing in the same OLTP table.
const ROWS: { key: keyof SourceMixResp["counts"]; label: string; bar: string; dot: string }[] = [
  { key: "manual", label: "Manual", bar: "bg-accent-green", dot: "bg-accent-green" },
  { key: "agente", label: "Agente IA", bar: "bg-accent-purple", dot: "bg-accent-purple" },
  { key: "simulacion", label: "Simulación", bar: "bg-accent-cyan", dot: "bg-accent-cyan" },
  { key: "historico", label: "Histórico", bar: "bg-gray-500", dot: "bg-gray-500" },
];

export function SourceMixWidget() {
  const [mix, setMix] = useState<SourceMixResp | null>(null);

  useEffect(() => {
    const load = () => api.sourceMix().then(setMix).catch(() => {});
    load();
    const id = window.setInterval(load, 2000);
    return () => window.clearInterval(id);
  }, []);

  const total = mix?.total ?? 0;
  const counts = mix?.counts ?? { manual: 0, agente: 0, simulacion: 0, historico: 0 };

  return (
    <Card title="Origen de ventas" badge={<ComputeBadge kind="lakebase" short />}>
      <div className="mb-3 flex items-center gap-2 text-gray-400">
        <GitMerge size={14} />
        <span className="text-xs">
          {total.toLocaleString()} ventas · tabla <code className="text-accent-cyan">refrescos_latam.ventas</code>
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {ROWS.map((r) => {
          const c = counts[r.key] ?? 0;
          const pct = total > 0 ? Math.round((c / total) * 100) : 0;
          return (
            <div key={r.key}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-gray-300">
                  <span className={`h-2 w-2 rounded-full ${r.dot}`} />
                  {r.label}
                </span>
                <span className="tnum text-gray-400">
                  {c.toLocaleString()} · {pct}%
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-ink-900">
                <div
                  className={`h-full rounded-full ${r.bar} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

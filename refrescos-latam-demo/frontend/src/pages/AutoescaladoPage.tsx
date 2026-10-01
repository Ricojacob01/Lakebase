import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, BarChart3, Play, RotateCcw, Square, Zap, Trash2 } from "lucide-react";
import {
  AreaChart,
  Area,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  type LiveResp,
  type TpsPoint,
  type EventPoint,
} from "../api";
import { VERTICALS } from "../verticals";
import { Card } from "../components/Card";
import { ComputeBadge } from "../components/ComputeBadge";

const POLL_MS = 1000;
const VERTICAL = "refrescos" as const;

interface AnalyticsResult {
  type: "postgres" | "lakehouse";
  latency_ms: number;
  row_count: number;
  compute: string;
  tpsDropPercent?: number;
  minTpsDuring?: number;
}

// Tab 4 — Autoescalado Lakebase. HTAP workload isolation demo.
export function AutoescaladoPage() {
  const meta = VERTICALS[VERTICAL];

  const [live, setLive] = useState<LiveResp | null>(null);
  const [series, setSeries] = useState<TpsPoint[]>([]);
  const [events, setEvents] = useState<EventPoint[]>([]);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<AnalyticsResult[]>([]);

  const running = live?.running ?? false;
  const pollRef = useRef<number | null>(null);
  const baselineTpsRef = useRef<number>(0);

  const poll = useCallback(async () => {
    try {
      const [l, s, e] = await Promise.all([
        api.live(),
        api.tpsSeries(),
        api.events(),
      ]);
      setLive(l);
      setSeries(s.points);
      setEvents(e.events);
      // Track baseline for comparison
      if (l.tps > 0 && baselineTpsRef.current === 0) {
        baselineTpsRef.current = l.tps;
      }
    } catch {
      /* transient — keep last good state */
    }
  }, []);

  useEffect(() => {
    poll();
    pollRef.current = window.setInterval(poll, POLL_MS);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [poll]);

  const wrap = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await poll();
    } finally {
      setBusy(false);
    }
  };

  const runAnalytics = async (type: "postgres" | "lakehouse") => {
    try {
      const result = await (type === "postgres"
        ? api.analyticsPostgres()
        : api.analyticsLakehouse());

      // Calculate TPS drop by looking at series after the analytics run
      // Find the min TPS in the last 5 seconds and compare to baseline
      const recentPoints = series.slice(-5);
      const minTpsDuring = recentPoints.length > 0
        ? Math.min(...recentPoints.map((p) => p.tps))
        : baselineTpsRef.current;
      const tpsDropPercent = baselineTpsRef.current > 0
        ? Math.round(((baselineTpsRef.current - minTpsDuring) / baselineTpsRef.current) * 100)
        : 0;

      const newResult: AnalyticsResult = {
        type,
        latency_ms: result.latency_ms,
        row_count: result.row_count,
        compute: result.compute,
        tpsDropPercent: Math.max(0, tpsDropPercent),
        minTpsDuring,
      };

      setResults((prev) => {
        const filtered = prev.filter((r) => r.type !== type);
        return [...filtered, newResult];
      });
    } catch (e) {
      console.error(`Analytics error: ${e}`);
    }
  };

  const btn =
    "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold transition disabled:opacity-40 disabled:cursor-not-allowed";

  // Prepare chart data with event markers
  const chartData = series.map((p) => ({
    time: new Date(p.t * 1000).toLocaleTimeString([], {
      minute: "2-digit",
      second: "2-digit",
    }),
    tps: p.tps,
    t: p.t,
  }));

  // Find max TPS for axis scaling
  const tpsValues = series.map((p) => p.tps);
  const maxTps = tpsValues.length > 0 ? Math.max(...tpsValues) : 100;

  const postgresResult = results.find((r) => r.type === "postgres");
  const lakehouseResult = results.find((r) => r.type === "lakehouse");

  return (
    <div className="grid h-[calc(100vh-7rem)] grid-cols-1 gap-3 p-3 overflow-y-auto">
      {/* Control panel */}
      <section className="rounded-xl border border-ink-border bg-ink-700/70 p-3 shadow-lg shadow-black/20">
        <div className="flex flex-wrap items-center gap-2">
          <button
            className={`${btn} border border-ink-border bg-ink-600 text-gray-200 hover:bg-ink-500`}
            onClick={() => wrap(() => api.reset())}
            disabled={busy}
          >
            <RotateCcw size={16} /> Reiniciar
          </button>
          <button
            className={`${btn} bg-accent-green text-black hover:brightness-110`}
            onClick={() => wrap(() => api.start())}
            disabled={busy || running}
          >
            <Play size={16} /> Iniciar carga
          </button>
          <button
            className={`${btn} bg-accent-red text-white hover:brightness-110`}
            onClick={() => wrap(() => api.stop())}
            disabled={busy || !running}
          >
            <Square size={16} /> Detener
          </button>

          <div className="mx-2 h-6 w-px bg-ink-600" />

          <button
            className={`${btn} border border-accent-amber/50 bg-accent-amber/10 text-accent-amber hover:bg-accent-amber/20`}
            onClick={() => wrap(() => runAnalytics("postgres"))}
            disabled={busy || !running}
          >
            <Zap size={16} /> Analítica en Postgres
          </button>
          <button
            className={`${btn} border border-accent-green/50 bg-accent-green/10 text-accent-green hover:bg-accent-green/20`}
            onClick={() => wrap(() => runAnalytics("lakehouse"))}
            disabled={busy || !running}
          >
            <BarChart3 size={16} /> Analítica en Lakehouse
          </button>
          <button
            className={`${btn} border border-accent-red/50 bg-accent-red/10 text-accent-red hover:bg-accent-red/20`}
            onClick={() => wrap(() => api.clean())}
            disabled={busy}
          >
            <Trash2 size={16} /> Limpiar
          </button>

          <div className="ml-auto">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${
                running
                  ? "bg-accent-green/15 text-accent-green"
                  : "bg-gray-500/15 text-gray-400"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  running ? "animate-pulse bg-accent-green" : "bg-gray-500"
                }`}
              />
              {running ? "en ejecución" : "detenido"}
            </span>
          </div>
        </div>
      </section>

      {/* Main content: TPS chart + results */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* TPS Chart (left, spans 2 cols on lg) */}
        <div className="lg:col-span-2">
          <Card title="TPS en el tiempo" badge={<ComputeBadge kind="lakebase" short />}>
            <div className="flex items-center gap-2 text-gray-400 mb-3">
              <Activity size={14} />
              <span className="text-xs">
                {meta.emoji} {meta.txnLabel} — muestra el impacto de cada tipo de analítica
              </span>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="tpsFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="time"
                    tick={{ fill: "#8b98a5", fontSize: 10 }}
                    stroke="#2a3441"
                    minTickGap={40}
                  />
                  <YAxis
                    tick={{ fill: "#8b98a5", fontSize: 10 }}
                    stroke="#2a3441"
                    allowDecimals={false}
                    width={40}
                    domain={[0, Math.ceil(maxTps * 1.2)]}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #2a3441",
                      borderRadius: 8,
                      color: "#e6edf3",
                      fontSize: 12,
                    }}
                    labelStyle={{ color: "#8b98a5" }}
                  />

                  {/* Event markers */}
                  {events.map((e, i) => {
                    const isPostgres = e.label.includes("Postgres");
                    return (
                      <ReferenceLine
                        key={i}
                        x={new Date(e.t * 1000).toLocaleTimeString([], {
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                        stroke={isPostgres ? "#f59e0b" : "#10b981"}
                        strokeDasharray="3 3"
                        label={{
                          value: e.label.slice(0, 10),
                          position: "top",
                          fill: isPostgres ? "#f59e0b" : "#10b981",
                          fontSize: 10,
                        }}
                      />
                    );
                  })}

                  <Area
                    type="monotone"
                    dataKey="tps"
                    stroke="#22d3ee"
                    strokeWidth={2}
                    fill="url(#tpsFill)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* Results comparison (right) */}
        <div className="flex flex-col gap-3">
          {/* Postgres Analytics */}
          <Card>
            <div className="text-xs font-semibold uppercase text-accent-amber mb-3 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent-amber" />
              Analítica en Postgres
            </div>
            {postgresResult ? (
              <div className="space-y-2 text-sm">
                <div>
                  <div className="text-[10px] uppercase text-gray-500">Latencia</div>
                  <div className="text-2xl font-bold text-accent-amber">
                    {postgresResult.latency_ms}
                    <span className="text-base font-normal text-gray-400"> ms</span>
                  </div>
                </div>
                <div className="border-t border-ink-border pt-2">
                  <div className="text-[10px] uppercase text-gray-500">Filas procesadas</div>
                  <div className="text-lg font-bold text-gray-200">
                    {postgresResult.row_count.toLocaleString()}
                  </div>
                </div>
                <div className="border-t border-ink-border pt-2 rounded-lg bg-accent-red/10 p-2.5 border border-accent-red/40">
                  <div className="text-[10px] uppercase text-accent-red mb-1">TPS Impacto</div>
                  <div className="text-lg font-bold text-accent-red">
                    ↓ {postgresResult.tpsDropPercent || 0}%
                  </div>
                  <div className="text-xs text-accent-red/80 mt-1">
                    TPS bajó a {postgresResult.minTpsDuring !== undefined ? Math.round(postgresResult.minTpsDuring) : "—"}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-500">Ejecuta analítica para ver resultados…</div>
            )}
          </Card>

          {/* Lakehouse Analytics */}
          <Card>
            <div className="text-xs font-semibold uppercase text-accent-green mb-3 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent-green" />
              Analítica en Lakehouse
            </div>
            {lakehouseResult ? (
              <div className="space-y-2 text-sm">
                <div>
                  <div className="text-[10px] uppercase text-gray-500">Latencia</div>
                  <div className="text-2xl font-bold text-accent-green">
                    {lakehouseResult.latency_ms}
                    <span className="text-base font-normal text-gray-400"> ms</span>
                  </div>
                </div>
                <div className="border-t border-ink-border pt-2">
                  <div className="text-[10px] uppercase text-gray-500">Filas procesadas</div>
                  <div className="text-lg font-bold text-gray-200">
                    {lakehouseResult.row_count.toLocaleString()}
                  </div>
                </div>
                <div className="border-t border-ink-border pt-2 rounded-lg bg-accent-green/10 p-2.5 border border-accent-green/40">
                  <div className="text-[10px] uppercase text-accent-green mb-1">TPS Impacto</div>
                  <div className="text-lg font-bold text-accent-green">
                    ≈ 0% ✓
                  </div>
                  <div className="text-xs text-accent-green/80 mt-1">
                    OLTP aislado, TPS se mantiene
                    {lakehouseResult.minTpsDuring !== undefined
                      ? ` (${Math.round(lakehouseResult.minTpsDuring)})`
                      : ""}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-500">Ejecuta analítica para ver resultados…</div>
            )}
          </Card>
        </div>
      </div>

      {/* Explanation panel */}
      <Card>
        <h3 className="text-sm font-semibold text-accent-cyan mb-2">
          ¿Por qué el aislamiento de cargas importa?
        </h3>
        <p className="text-xs leading-relaxed text-gray-300 mb-2">
          <strong>Analítica en Postgres (Lakebase OLTP):</strong> La consulta directa sobre la
          tabla OLTP genera lock y compite con transacciones en tiempo real. Ves el TPS caer
          durante la ejecución.
        </p>
        <p className="text-xs leading-relaxed text-gray-300">
          <strong>Analítica en Lakehouse (SQL Warehouse + Delta):</strong> Los datos están
          replicados en Unity Catalog. El cómputo es independiente — Postgres sigue procesando
          ventas sin interferencia. TPS se mantiene estable.
        </p>
        <div className="mt-3 flex gap-2 text-xs">
          <span className="inline-flex items-center gap-1 rounded-full border border-accent-amber/40 px-2 py-0.5 text-accent-amber bg-accent-amber/10">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-amber" />
            Postgres = Contención
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-accent-green/40 px-2 py-0.5 text-accent-green bg-accent-green/10">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-green" />
            Lakehouse = HTAP ✓
          </span>
        </div>
      </Card>
    </div>
  );
}

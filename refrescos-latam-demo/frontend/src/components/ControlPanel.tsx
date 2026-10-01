import { Database, Play, RotateCcw, Square, Terminal } from "lucide-react";
import type { Vertical } from "../api";

// Control panel: reset / start / stop / run-query + running status badge.
// Titleless + compact so the whole page fits without scrolling.
export function ControlPanel({
  running,
  demoMode,
  busy,
  onReset,
  onStart,
  onStop,
  onRunQuery,
}: {
  running: boolean;
  demoMode: boolean;
  busy: boolean;
  vertical: Vertical;
  onReset: () => void;
  onStart: () => void;
  onStop: () => void;
  onRunQuery: () => void;
}) {
  const btn =
    "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold transition disabled:opacity-40 disabled:cursor-not-allowed";
  return (
    <section className="rounded-xl border border-ink-border bg-ink-700/70 p-3 shadow-lg shadow-black/20">
      <div className="flex flex-wrap items-center gap-2">
        <button
          className={`${btn} border border-ink-border bg-ink-600 text-gray-200 hover:bg-ink-500`}
          onClick={onReset}
          disabled={busy}
        >
          <RotateCcw size={16} /> Reiniciar datos
        </button>
        <button
          className={`${btn} bg-accent-green text-black hover:brightness-110`}
          onClick={onStart}
          disabled={busy || running}
        >
          <Play size={16} /> Iniciar
        </button>
        <button
          className={`${btn} bg-accent-red text-white hover:brightness-110`}
          onClick={onStop}
          disabled={busy || !running}
        >
          <Square size={16} /> Detener
        </button>
        <button
          className={`${btn} bg-accent-cyan text-black hover:brightness-110`}
          onClick={onRunQuery}
          disabled={busy}
        >
          <Terminal size={16} /> Consultar
        </button>

        <div className="ml-auto flex items-center gap-3">
          {demoMode && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-amber/40 bg-ink-800/60 px-2.5 py-1 text-[11px] font-medium text-accent-amber">
              <Database size={12} /> Modo demo (sin Lakebase)
            </span>
          )}
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
  );
}

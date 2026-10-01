// Compute attribution badge — names which Databricks compute serves a panel.
import type { ComputeKind } from "../api";

const MAP: Record<ComputeKind, { label: string; dot: string; ring: string }> = {
  lakebase: {
    label: "🟢 Lakebase (Postgres OLTP)",
    dot: "bg-accent-green",
    ring: "border-accent-green/40 text-accent-green",
  },
  // Genie is NOT its own compute — it runs its NL→SQL on the SQL Warehouse.
  // The badge reflects the real compute so the demo stays honest.
  genie: {
    label: "🟡 SQL Warehouse",
    dot: "bg-accent-amber",
    ring: "border-accent-amber/40 text-accent-amber",
  },
  warehouse: {
    label: "🟡 SQL Warehouse",
    dot: "bg-accent-amber",
    ring: "border-accent-amber/40 text-accent-amber",
  },
  // The agent runs on a Foundation Model / model serving endpoint, not on
  // Lakebase or a SQL Warehouse — its own compute in the narrative.
  agent: {
    label: "🟣 Foundation Model (agente)",
    dot: "bg-accent-purple",
    ring: "border-accent-purple/40 text-accent-purple",
  },
};

// `short` renders the compact "🟢 Lakebase" for the live/kpi panels.
export function ComputeBadge({
  kind,
  short = false,
}: {
  kind: ComputeKind;
  short?: boolean;
}) {
  const m = MAP[kind];
  const shortLabels: Partial<Record<ComputeKind, string>> = {
    lakebase: "🟢 Lakebase",
    agent: "🟣 Foundation Model",
  };
  const label = (short && shortLabels[kind]) || m.label;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${m.ring} bg-ink-800/60`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      {label}
    </span>
  );
}

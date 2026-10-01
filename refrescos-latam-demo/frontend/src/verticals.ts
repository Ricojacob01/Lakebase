import type { Vertical } from "./api";

// Per-vertical presentation metadata + KPI formatting.
export interface KpiSpec {
  key: string;
  label: string;
  accent: string;
  suffix?: string;
  format: (v: number) => string;
}

export interface VerticalMeta {
  id: Vertical;
  label: string;
  emoji: string;
  txnLabel: string; // what a "transaction" is in this vertical
  kpis: KpiSpec[];
}

const int = (v: number) => Math.round(v).toLocaleString();
const usd = (v: number) => "$" + v.toLocaleString(undefined, { maximumFractionDigits: 2 });

export const VERTICALS: Record<Vertical, VerticalMeta> = {
  refrescos: {
    id: "refrescos",
    label: "Refrescos LATAM",
    emoji: "🥤",
    txnLabel: "sales de refrescos",
    kpis: [
      {
        key: "ventas_total",
        label: "Ventas totales",
        accent: "text-accent-cyan",
        format: usd,
      },
      {
        key: "pedidos",
        label: "Pedidos",
        accent: "text-accent-green",
        format: int,
      },
      {
        key: "ticket_medio",
        label: "Ticket medio",
        accent: "text-accent-amber",
        format: usd,
      },
    ],
  },
};

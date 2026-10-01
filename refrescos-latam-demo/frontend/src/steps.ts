import type { Route } from "./router";

// Refrescos LATAM: four steps showing sales capture → AI agent → analytics → HTAP workload isolation.
export interface StepMeta {
  id: Route;
  n: number;
  label: string; // nav label, e.g. "1 · Ventas"
  title: string; // screen heading
  caption: string; // one-line story caption under the heading
}

export const STEPS: StepMeta[] = [
  {
    id: "ventas",
    n: 1,
    label: "1 · Ventas",
    title: "Ventas",
    caption: "Captura de ventas en tiempo real — Refrescos LATAM",
  },
  {
    id: "chat",
    n: 2,
    label: "2 · Chat con agente",
    title: "Chat con agente",
    caption: "Registra ventas usando lenguaje natural con IA.",
  },
  {
    id: "dashboard",
    n: 3,
    label: "3 · Dashboard",
    title: "Dashboard",
    caption: "Tablero AI/BI y últimos pedidos del lakehouse.",
  },
  {
    id: "autoescalado",
    n: 4,
    label: "4 · Autoescalado Lakebase",
    title: "Autoescalado Lakebase",
    caption:
      "HTAP: compare analítica en Postgres vs lakehouse — aislamiento de cargas.",
  },
];

export const STEP_BY_ID: Record<Route, StepMeta> = STEPS.reduce(
  (acc, s) => ({ ...acc, [s.id]: s }),
  {} as Record<Route, StepMeta>,
);

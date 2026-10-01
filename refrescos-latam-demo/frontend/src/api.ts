// Thin fetch wrapper for the backend API. All payloads carry a `compute` field.

export type Vertical = "refrescos";
// `agent` = Foundation Model / model serving (the agentic-capture screen).
export type ComputeKind = "lakebase" | "genie" | "warehouse" | "agent";

export interface LiveResp {
  tps: number;
  total: number;
  running: boolean;
  demo_mode: boolean;
  compute: ComputeKind;
}

export interface TpsPoint {
  t: number;
  tps: number;
}

export interface EventPoint {
  t: number;
  phase: string;
  label: string;
}

export interface KpiResp {
  kpis: Record<string, number>;
  compute: ComputeKind;
}

export interface QueryResp {
  sql: string;
  row_count: number;
  latency_ms: number;
  compute: ComputeKind;
  top?: Record<string, unknown>[];
}

export interface EmbedsResp {
  dashboard?: { url: string; compute: ComputeKind };
  genie?: { url: string; compute: ComputeKind };
}

// ---- Refrescos Vertical Types -----------------------------------------------
export interface Venta {
  venta_id?: number | string;
  ts?: string;
  tienda_id: number;
  producto_id: number;
  cantidad: number;
  monto: number;
  origen?: string;
  tienda?: string;
  ciudad?: string;
  pais?: string;
  producto?: string;
  marca?: string;
}

export interface Producto {
  producto_id: number;
  nombre: string;
  marca: string;
  pais: string;
  categoria: string;
  presentacion: string;
  precio: number;
}

export interface Tienda {
  tienda_id: number;
  nombre: string;
  ciudad: string;
  pais: string;
  region: string;
  tipo: string;
}

export interface ManualInsertResp {
  ok: boolean;
  venta: Venta;
  compute: ComputeKind;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface AgentInsertResp {
  reasoning: string;
  tool_call?: ToolCall | null;
  registered: boolean;
  compute: ComputeKind;
  thread_id: string;
}

// Agent conversation memory persisted in Lakebase (keyed by thread_id).
export interface MemoryTurn {
  turn_idx: number;
  role: "user" | "assistant";
  content: string;
  tool_call?: ToolCall | null;
  ts?: string;
}

export interface AgentMemoryResp {
  turns: MemoryTurn[];
  compute: ComputeKind;
}

export interface SourceMixResp {
  counts: { manual: number; agente: number; simulacion: number; historico: number };
  total: number;
  compute: ComputeKind;
}

export interface LatestOrderResp {
  venta: Venta;
  compute: ComputeKind;
  source: string;
}

export interface EventsResp {
  events: EventPoint[];
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  // Control endpoints
  start: (tps?: number) =>
    req(`/refrescos/start`, { method: "POST", body: JSON.stringify({ tps }) }),
  stop: () => req(`/refrescos/stop`, { method: "POST" }),
  reset: () => req(`/refrescos/reset`, { method: "POST" }),

  // Live data
  live: () => req<LiveResp>(`/refrescos/live`),
  tpsSeries: () => req<{ points: TpsPoint[] }>(`/refrescos/tps-series`),
  kpi: () => req<KpiResp>(`/refrescos/kpi`),

  // Catalog
  productos: () => req<Producto[]>(`/refrescos/productos`),
  tiendas: () => req<Tienda[]>(`/refrescos/tiendas`),

  // Sales
  manualInsert: (body: { tienda_id: number; producto_id: number; cantidad: number }) =>
    req<ManualInsertResp>(`/refrescos/manual-insert`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  recent: (limit?: number) =>
    req<Venta[]>(`/refrescos/recent${limit ? `?limit=${limit}` : ""}`),

  // Source mix
  sourceMix: () => req<SourceMixResp>(`/refrescos/source-mix`),

  // Agent
  agentInsert: (message: string, thread_id?: string) =>
    req<AgentInsertResp>(`/refrescos/agent-insert`, {
      method: "POST",
      body: JSON.stringify({ message, thread_id }),
    }),
  agentMemory: (thread_id: string) =>
    req<AgentMemoryResp>(`/refrescos/agent-memory?thread_id=${encodeURIComponent(thread_id)}`),
  clearAgentMemory: (thread_id: string) =>
    req(`/refrescos/agent-memory?thread_id=${encodeURIComponent(thread_id)}`, {
      method: "DELETE",
    }),

  // Embeds
  embeds: () => req<EmbedsResp>(`/refrescos/embeds`),

  // Latest order
  latestOrder: () => req<LatestOrderResp>(`/refrescos/latest-order`),

  // Analytics
  analyticsPostgres: () =>
    req<QueryResp>(`/refrescos/analytics/postgres`, { method: "POST" }),
  analyticsLakehouse: () =>
    req<QueryResp>(`/refrescos/analytics/lakehouse`, { method: "POST" }),

  // Events
  events: () => req<EventsResp>(`/refrescos/events`),

  // Clean
  clean: () => req(`/refrescos/clean`, { method: "POST" }),
};

// Small pill showing a transaction's origin.
const MAP: Record<string, { label: string; cls: string }> = {
  manual: { label: "manual", cls: "border-accent-green/40 text-accent-green" },
  agente: { label: "agente IA", cls: "border-accent-purple/40 text-accent-purple" },
  simulacion: { label: "simulación", cls: "border-accent-cyan/40 text-accent-cyan" },
  historico: { label: "histórico", cls: "border-gray-400/40 text-gray-400" },
  // Legacy sources (for compatibility)
  traditional: { label: "manual", cls: "border-accent-green/40 text-accent-green" },
  agent: { label: "agente IA", cls: "border-accent-purple/40 text-accent-purple" },
};

export function SourceTag({ source }: { source: string }) {
  const m = MAP[source] ?? { label: source, cls: "border-ink-border text-gray-400" };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${m.cls} bg-ink-800/60`}
    >
      {m.label}
    </span>
  );
}

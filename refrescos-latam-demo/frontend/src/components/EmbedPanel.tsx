import type { ReactNode } from "react";
import { ExternalLink } from "lucide-react";
import type { ComputeKind } from "../api";
import { ComputeBadge } from "./ComputeBadge";

// Accent per compute kind — a subtle top border + icon tint that ties the
// embedded (light) Databricks surface back into the app's dark theme.
const ACCENT: Record<ComputeKind, { bar: string; icon: string; glow: string }> = {
  lakebase: { bar: "from-accent-green/70", icon: "text-accent-green", glow: "shadow-accent-green/10" },
  genie: { bar: "from-accent-cyan/70", icon: "text-accent-cyan", glow: "shadow-accent-cyan/10" },
  warehouse: { bar: "from-accent-amber/70", icon: "text-accent-amber", glow: "shadow-accent-amber/10" },
  agent: { bar: "from-accent-purple/70", icon: "text-accent-purple", glow: "shadow-accent-purple/10" },
};

// Renders an iframe embed (AI/BI dashboard or Genie) or a "not configured yet"
// placeholder when the URL is empty. Databricks embeds render light; we frame
// them on a soft white canvas inside the dark card so the transition reads as
// intentional design instead of a hard black/white clash.
export function EmbedPanel({
  title,
  url,
  kind,
  hint,
  icon,
}: {
  title: string;
  url: string;
  kind: ComputeKind;
  hint: string;
  icon?: ReactNode;
}) {
  const a = ACCENT[kind];
  return (
    <section
      className={`flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-ink-border bg-ink-700/70 shadow-lg ${a.glow}`}
    >
      {/* Accent bar ties the panel to its compute color. */}
      <div className={`h-1 w-full bg-gradient-to-r ${a.bar} to-transparent`} />

      <header className="flex items-center justify-between gap-2 px-4 py-3">
        <div className="flex items-center gap-2">
          {icon && <span className={a.icon}>{icon}</span>}
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-100">
            {title}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-ink-border bg-ink-800/60 p-1.5 text-gray-400 transition hover:text-accent-cyan"
              title="Abrir en pestaña nueva"
            >
              <ExternalLink size={13} />
            </a>
          )}
          <ComputeBadge kind={kind} />
        </div>
      </header>

      {url ? (
        // Soft white canvas with padding so the light embed feels framed, not pasted.
        <div className="min-h-0 flex-1 rounded-t-xl bg-white/95 p-1.5">
          <iframe
            src={url}
            title={title}
            className="h-full w-full rounded-lg border-0"
            allow="clipboard-write"
          />
        </div>
      ) : (
        <div className="m-3 flex min-h-0 flex-1 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-ink-border bg-ink-900/60 text-center">
          <div className={a.icon}>{icon}</div>
          <div className="text-sm font-medium text-gray-300">
            Aún no configurado
          </div>
          <p className="max-w-md px-6 text-xs leading-relaxed text-gray-500">
            {hint}
          </p>
        </div>
      )}
    </section>
  );
}

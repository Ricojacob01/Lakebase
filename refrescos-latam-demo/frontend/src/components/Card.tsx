import type { ReactNode } from "react";

// Base surface card matching the dark template.
export function Card({
  title,
  badge,
  children,
  className = "",
}: {
  title?: string;
  badge?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-xl border border-ink-border bg-ink-700/70 p-4 shadow-lg shadow-black/20 ${className}`}
    >
      {(title || badge) && (
        <header className="mb-3 flex items-center justify-between gap-2">
          {title && (
            <h2 className="text-sm font-semibold uppercase tracking-wide text-accent-cyan">
              {title}
            </h2>
          )}
          {badge}
        </header>
      )}
      {children}
    </section>
  );
}

// Big-number stat used across the KPI / live panels.
export function Stat({
  label,
  value,
  accent = "text-accent-cyan",
  suffix,
}: {
  label: string;
  value: string | number;
  accent?: string;
  suffix?: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-gray-400">
        {label}
      </div>
      <div className={`tnum text-3xl font-bold ${accent}`}>
        {value}
        {suffix && <span className="ml-1 text-base font-medium text-gray-400">{suffix}</span>}
      </div>
    </div>
  );
}

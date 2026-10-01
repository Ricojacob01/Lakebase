import { Card } from "./Card";
import { ComputeBadge } from "./ComputeBadge";
import type { QueryResp } from "../api";

// Shows the "Current Query" SQL and the most recent result + latency.
export function LakebaseQueryPanel({
  sql,
  result,
}: {
  sql: string;
  result: QueryResp | null;
}) {
  return (
    <Card title="Consulta Lakebase" badge={<ComputeBadge kind="lakebase" />}>
      <div className="mb-2 text-[11px] uppercase tracking-wide text-gray-400">
        Consulta actual
      </div>
      <pre className="overflow-x-auto rounded-lg border border-ink-border bg-ink-900 p-2.5 text-xs leading-relaxed text-accent-cyan">
        <code>{sql || "—"}</code>
      </pre>

      <div className="mb-2 mt-3 flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wide text-gray-400">
          Resultado
        </span>
        {result && (
          <span className="tnum text-[11px] text-gray-400">
            {result.latency_ms} ms
          </span>
        )}
      </div>

      {result && result.top && result.top.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-ink-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-800 text-gray-400">
              <tr>
                {Object.keys(result.top[0]).map((c: string) => (
                  <th key={c} className="px-3 py-2 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.top.map((row: Record<string, unknown>, i: number) => (
                <tr key={i} className="border-t border-ink-border">
                  {Object.values(row).map((v: unknown, j: number) => (
                    <td key={j} className="tnum px-3 py-2 text-gray-200">
                      {String(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-ink-border bg-ink-900/60 px-3 py-4 text-center text-xs text-gray-500">
          Presiona "Consultar" para ejecutar contra Lakebase.
        </div>
      )}
    </Card>
  );
}

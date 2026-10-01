import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TpsPoint } from "../api";

// Live area chart of transactions-per-second.
export function TpsChart({ points }: { points: TpsPoint[] }) {
  const data = points.map((p) => ({
    time: new Date(p.t * 1000).toLocaleTimeString([], {
      minute: "2-digit",
      second: "2-digit",
    }),
    tps: p.tps,
  }));

  return (
    <div className="h-32 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
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
  );
}

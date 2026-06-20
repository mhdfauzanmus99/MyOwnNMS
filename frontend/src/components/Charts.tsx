import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from "recharts";
import type { Metric } from "../api";
import { fmtBps, fmtPct } from "../api";

/* ------------------------------------------------------------------ */
/* Utilisation area chart (bps + % on two Y axes)                       */
/* ------------------------------------------------------------------ */
export function UtilChart({ data, height = 300 }: { data: Metric[]; height?: number }) {
  const chartData = data.map((m) => ({
    ts: new Date(m.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    "In": m.in_bps ?? 0,
    "Out": m.out_bps ?? 0,
    "In %": m.in_pct ?? 0,
    "Out %": m.out_pct ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="gradIn" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#34d399" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="gradOut" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#60a5fa" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="ts" tick={{ fontSize: 11 }} stroke="#64748b" />
        <YAxis
          yAxisId="bps"
          tickFormatter={(v) => (v >= 1e9 ? `${(v / 1e9).toFixed(1)}G` : v >= 1e6 ? `${(v / 1e6).toFixed(0)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : v)}
          tick={{ fontSize: 11 }}
          stroke="#64748b"
        />
        <YAxis
          yAxisId="pct"
          orientation="right"
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11 }}
          stroke="#64748b"
        />
        <Tooltip
          contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#e2e8f0" }}
          formatter={(value: number, name: string) => {
            if (name.includes("%")) return [fmtPct(value), name];
            return [fmtBps(value), name];
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
        <Area yAxisId="bps" type="monotone" dataKey="In" stroke="#34d399" fill="url(#gradIn)" strokeWidth={2} />
        <Area yAxisId="bps" type="monotone" dataKey="Out" stroke="#60a5fa" fill="url(#gradOut)" strokeWidth={2} />
        <Area yAxisId="pct" type="monotone" dataKey="In %" stroke="#34d399" fill="none" strokeWidth={1} strokeDasharray="4 2" />
        <Area yAxisId="pct" type="monotone" dataKey="Out %" stroke="#60a5fa" fill="none" strokeWidth={1} strokeDasharray="4 2" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/* Mini sparkline for dashboard cards                                    */
/* ------------------------------------------------------------------ */
export function MiniUtilChart({ data, color, height = 60 }: {
  data: Metric[];
  color: string;
  height?: number;
}) {
  const chartData = data.map((m) => ({
    ts: new Date(m.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    pct: Math.max(m.in_pct ?? 0, m.out_pct ?? 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 2, right: 2, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id={`mini-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="pct" stroke={color} fill={`url(#mini-${color})`} strokeWidth={1.5} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

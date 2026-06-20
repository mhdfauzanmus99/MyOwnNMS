import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import * as api from "../api";
import type { Interface, Metric } from "../api";
import { UtilChart } from "../components/Charts";
import { StatusDot } from "../components/UI";
import { fmtBps, fmtPct, fmtSpeed } from "../api";
import { ArrowLeft } from "lucide-react";

const RANGES = ["1h", "6h", "24h"] as const;

export function InterfaceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [iface, setIface] = useState<Interface | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [range, setRange] = useState<string>("1h");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [i, m] = await Promise.all([api.getInterface(+id), api.interfaceMetrics(+id, range)]);
      setIface(i);
      setMetrics(m);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [id, range]);

  useEffect(() => { load(); }, [load]);

  if (loading || !iface) return <div className="flex h-64 items-center justify-center text-slate-400">Loading…</div>;

  const peak = Math.max(iface.in_pct ?? 0, iface.out_pct ?? 0);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to={`/devices/${iface.device_id}`} className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-surface-hover transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">{iface.name || iface.descr || `Interface ${iface.id}`}</h1>
            <div className="flex items-center gap-1.5">
              <StatusDot status={iface.oper_status} />
              <span className={`text-sm font-medium ${iface.oper_status === "up" ? "text-emerald-400" : "text-red-400"}`}>
                {iface.oper_status}
              </span>
            </div>
          </div>
          <p className="text-sm text-slate-400 mt-0.5">
            {iface.device_name} · {iface.alias || iface.descr || "—"} · {fmtSpeed(iface.speed)}
          </p>
        </div>
      </div>

      {/* Current stats */}
      <div className="card grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-slate-400 block">In Traffic</span>
          <span className="text-white font-medium font-mono">{fmtBps(iface.in_bps)}</span>
          <span className="text-slate-500 ml-1">({fmtPct(iface.in_pct)})</span>
        </div>
        <div>
          <span className="text-slate-400 block">Out Traffic</span>
          <span className="text-white font-medium font-mono">{fmtBps(iface.out_bps)}</span>
          <span className="text-slate-500 ml-1">({fmtPct(iface.out_pct)})</span>
        </div>
        <div>
          <span className="text-slate-400 block">Peak Utilisation</span>
          <span className={`font-medium ${peak > 80 ? "text-amber-400" : "text-emerald-400"}`}>{fmtPct(peak)}</span>
        </div>
        <div>
          <span className="text-slate-400 block">Speed</span>
          <span className="text-white font-medium">{fmtSpeed(iface.speed)}</span>
        </div>
      </div>

      {/* Utilisation graph */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Utilisation</h2>
          <div className="flex items-center gap-1 bg-surface rounded-lg p-1">
            {RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  range === r ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        {metrics.length < 2 ? (
          <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
            Not enough data points yet. Wait for a few polling cycles.
          </div>
        ) : (
          <UtilChart data={metrics} height={350} />
        )}
      </div>

      {/* Errors / discards */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Errors & Discards</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div><span className="text-slate-400 block">In Errors</span><span className="text-white font-mono">{metrics[metrics.length - 1]?.in_errors ?? 0}</span></div>
          <div><span className="text-slate-400 block">Out Errors</span><span className="text-white font-mono">{metrics[metrics.length - 1]?.out_errors ?? 0}</span></div>
          <div><span className="text-slate-400 block">In Discards</span><span className="text-white font-mono">{metrics[metrics.length - 1]?.in_discards ?? 0}</span></div>
          <div><span className="text-slate-400 block">Out Discards</span><span className="text-white font-mono">{metrics[metrics.length - 1]?.out_discards ?? 0}</span></div>
        </div>
      </div>
    </div>
  );
}

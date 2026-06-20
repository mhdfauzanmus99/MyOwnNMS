import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import * as api from "../api";
import { useSSE, type SSEAlert } from "../hooks";
import { StatCard, SeverityBadge, StatusDot, ToastContainer } from "../components/UI";
import { Server, Wifi, WifiOff, AlertTriangle, RefreshCw } from "lucide-react";

export function DashboardPage() {
  const [data, setData] = useState<api.DashboardData | null>(null);
  const [toasts, setToasts] = useState<{ id: number; severity: string; message: string }[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const d = await api.dashboard();
      setData(d);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onAlert = useCallback((a: SSEAlert) => {
    setToasts((prev) => [...prev.slice(-4), { id: a.id, severity: a.severity, message: a.message }]);
    setTimeout(() => load(), 1000); // refresh dashboard after alert
  }, [load]);

  useSSE(onAlert);

  const dismiss = (id: number) => setToasts((p) => p.filter((t) => t.id !== id));

  if (loading || !data) {
    return <div className="flex h-64 items-center justify-center text-slate-400">Loading dashboard…</div>;
  }

  const d = data.devices;
  const i = data.interfaces;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <button onClick={load} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white bg-surface-card border border-surface-border rounded-lg px-3 py-2 transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Devices Up" value={d.up} icon={<Server className="w-6 h-6 text-emerald-400" />} color="bg-emerald-500/15" />
        <StatCard label="Devices Down" value={d.down} icon={<WifiOff className="w-6 h-6 text-red-400" />} color="bg-red-500/15" />
        <StatCard label="Interfaces Up" value={i.up} icon={<Wifi className="w-6 h-6 text-blue-400" />} color="bg-blue-500/15" />
        <StatCard label="Open Alerts" value={data.open_alerts} icon={<AlertTriangle className="w-6 h-6 text-amber-400" />} color="bg-amber-500/15" />
      </div>

      {/* Top interfaces + recent alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top utilised */}
        <div className="lg:col-span-2 card">
          <h2 className="text-lg font-semibold text-white mb-4">Top Utilised Interfaces</h2>
          {data.top_interfaces.length === 0 ? (
            <p className="text-slate-500 text-sm">No data yet — polling has not completed a second pass.</p>
          ) : (
            <div className="space-y-3">
              {data.top_interfaces.map((ti) => (
                <Link
                  key={ti.interface_id}
                  to={`/interfaces/${ti.interface_id}`}
                  className="flex items-center gap-4 p-3 rounded-lg bg-surface hover:bg-surface-hover transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white truncate">{ti.interface_name}</span>
                      <span className="text-xs text-slate-500">{ti.device_name}</span>
                    </div>
                    <div className="flex items-center gap-3 mt-1.5">
                      <div className="flex-1">
                        <div className="flex justify-between text-xs text-slate-400 mb-0.5">
                          <span>In</span>
                          <span>{api.fmtBps(ti.in_bps)} ({api.fmtPct(ti.in_pct)})</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-surface-hover overflow-hidden">
                          <div
                            className="h-full rounded-full bg-emerald-500 transition-all"
                            style={{ width: `${Math.min(ti.in_pct ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between text-xs text-slate-400 mb-0.5">
                          <span>Out</span>
                          <span>{api.fmtBps(ti.out_bps)} ({api.fmtPct(ti.out_pct)})</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-surface-hover overflow-hidden">
                          <div
                            className="h-full rounded-full bg-blue-500 transition-all"
                            style={{ width: `${Math.min(ti.out_pct ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  <StatusDot status="up" />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent alerts */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Alerts</h2>
            <Link to="/alerts" className="text-xs text-emerald-400 hover:text-emerald-300">View all →</Link>
          </div>
          {data.recent_alerts.length === 0 ? (
            <p className="text-slate-500 text-sm">No alerts yet.</p>
          ) : (
            <div className="space-y-2">
              {data.recent_alerts.map((a) => (
                <div key={a.id} className="flex items-start gap-2 p-2 rounded-lg bg-surface">
                  <SeverityBadge severity={a.severity} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 break-words">{a.message}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {new Date(a.ts).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

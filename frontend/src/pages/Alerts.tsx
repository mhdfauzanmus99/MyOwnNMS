import { useEffect, useState, useCallback } from "react";
import * as api from "../api";
import type { Alert } from "../api";
import { SeverityBadge, EmptyState } from "../components/UI";
import { Check, RefreshCw, XCircle } from "lucide-react";

export function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showResolved, setShowResolved] = useState(false);

  const load = useCallback(async () => {
    try { setAlerts(await api.listAlerts(showResolved ? true : false, 200)); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }, [showResolved]);

  useEffect(() => { load(); }, [load]);

  const handleAck = async (id: number) => {
    try { await api.ackAlert(id); load(); }
    catch { /* ignore */ }
  };

  const handleResolve = async (id: number) => {
    try { await api.resolveAlert(id); load(); }
    catch { /* ignore */ }
  };

  if (loading) return <div className="flex h-64 items-center justify-center text-slate-400">Loading…</div>;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Alerts</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowResolved(!showResolved)}
            className={`text-sm rounded-lg px-3 py-2 transition-colors border ${
              showResolved
                ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                : "bg-surface-card border-surface-border text-slate-400 hover:text-white"
            }`}
          >
            {showResolved ? "Showing resolved" : "Show resolved"}
          </button>
          <button onClick={load} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white bg-surface-card border border-surface-border rounded-lg px-3 py-2 transition-colors">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {alerts.length === 0 ? (
        <EmptyState message={showResolved ? "No resolved alerts." : "No open alerts. All clear!"} />
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={`card flex items-start gap-4 ${
                a.resolved_at ? "opacity-50" : ""
              }`}
            >
              <SeverityBadge severity={a.severity} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-200 break-words">{a.message}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                  <span className="badge badge-info">{a.type.replace("_", " ")}</span>
                  {a.device_name && <span>Device: {a.device_name}</span>}
                  {a.interface_name && <span>Interface: {a.interface_name}</span>}
                  <span>{new Date(a.ts).toLocaleString()}</span>
                  {a.resolved_at && <span className="text-emerald-500">Resolved: {new Date(a.resolved_at).toLocaleString()}</span>}
                  {a.acknowledged ? <span className="text-amber-400">Acknowledged</span> : null}
                </div>
              </div>
              {!a.resolved_at && (
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button onClick={() => handleAck(a.id)} className="p-1.5 rounded-md text-slate-400 hover:text-emerald-400 hover:bg-surface-hover transition-colors" title="Acknowledge">
                    <Check className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleResolve(a.id)} className="p-1.5 rounded-md text-slate-400 hover:text-red-400 hover:bg-surface-hover transition-colors" title="Resolve">
                    <XCircle className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

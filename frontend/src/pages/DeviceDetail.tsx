import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import * as api from "../api";
import type { Device, Interface } from "../api";
import { StatusDot } from "../components/UI";
import { fmtBps, fmtPct } from "../api";
import { ArrowLeft, RefreshCw } from "lucide-react";

export function DeviceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [device, setDevice] = useState<Device | null>(null);
  const [interfaces, setInterfaces] = useState<Interface[]>([]);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [d, ifs] = await Promise.all([api.getDevice(+id), api.deviceInterfaces(+id)]);
      setDevice(d);
      setInterfaces(ifs);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handlePoll = async () => {
    if (!id) return;
    setPolling(true);
    try { await api.pollDevice(+id); load(); }
    catch (err: any) { alert(err.message); }
    finally { setPolling(false); }
  };

  if (loading || !device) return <div className="flex h-64 items-center justify-center text-slate-400">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/devices" className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-surface-hover transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">{device.name}</h1>
            <div className="flex items-center gap-1.5">
              <StatusDot status={device.status} />
              <span className={`text-sm font-medium ${device.status === "up" ? "text-emerald-400" : device.status === "down" ? "text-red-400" : "text-slate-400"}`}>
                {device.status}
              </span>
            </div>
          </div>
          <p className="text-sm text-slate-400 mt-0.5">
            {device.hostname}:{device.port} · {device.vendor || "Unknown"} · {device.sysname || device.name}
          </p>
        </div>
        <button
          onClick={handlePoll}
          disabled={polling}
          className="flex items-center gap-2 text-sm text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg px-4 py-2 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${polling ? "animate-spin" : ""}`} />
          {polling ? "Polling…" : "Poll Now"}
        </button>
      </div>

      {/* System info */}
      <div className="card grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div><span className="text-slate-400 block">Vendor</span><span className="text-white font-medium">{device.vendor || "—"}</span></div>
        <div><span className="text-slate-400 block">SNMP Version</span><span className="text-white font-medium">{device.snmp_version}</span></div>
        <div><span className="text-slate-400 block">Interfaces</span><span className="text-white font-medium">{interfaces.length}</span></div>
        <div><span className="text-slate-400 block">Last Polled</span><span className="text-white font-medium">{device.last_polled ? new Date(device.last_polled).toLocaleTimeString() : "—"}</span></div>
      </div>

      {/* Interfaces table */}
      <div className="card overflow-x-auto p-0">
        <div className="px-5 py-3 border-b border-surface-border">
          <h2 className="text-lg font-semibold text-white">Interfaces</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-border text-left text-slate-400">
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Name</th>
              <th className="px-5 py-3 font-medium">Description</th>
              <th className="px-5 py-3 font-medium">Speed</th>
              <th className="px-5 py-3 font-medium">In</th>
              <th className="px-5 py-3 font-medium">Out</th>
              <th className="px-5 py-3 font-medium">Utilisation</th>
            </tr>
          </thead>
          <tbody>
            {interfaces.map((iface) => (
              <tr key={iface.id} className="border-b border-surface-border last:border-0 hover:bg-surface-hover transition-colors">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <StatusDot status={iface.oper_status} />
                    <span className="text-xs text-slate-400">{iface.oper_status}</span>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <Link to={`/interfaces/${iface.id}`} className="text-emerald-400 hover:text-emerald-300 font-medium">
                    {iface.name || iface.descr || `if${iface.ifindex}`}
                  </Link>
                </td>
                <td className="px-5 py-3 text-slate-400">{iface.alias || iface.descr || "—"}</td>
                <td className="px-5 py-3 text-slate-400 font-mono text-xs">{api.fmtSpeed(iface.speed)}</td>
                <td className="px-5 py-3 text-slate-300 font-mono text-xs">{fmtBps(iface.in_bps)}</td>
                <td className="px-5 py-3 text-slate-300 font-mono text-xs">{fmtBps(iface.out_bps)}</td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 max-w-[120px] h-2 rounded-full bg-surface-hover overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${Math.max(iface.in_pct ?? 0, iface.out_pct ?? 0) > 80 ? "bg-amber-500" : "bg-emerald-500"}`}
                        style={{ width: `${Math.min(Math.max(iface.in_pct ?? 0, iface.out_pct ?? 0), 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 w-12 text-right">{fmtPct(Math.max(iface.in_pct ?? 0, iface.out_pct ?? 0))}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

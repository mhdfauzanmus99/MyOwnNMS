import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import * as api from "../api";
import type { Device } from "../api";
import { StatusDot, StatusBadge, EmptyState } from "../components/UI";
import { Plus, Trash2, RefreshCw, X } from "lucide-react";

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", hostname: "", port: 161, community: "public", snmp_version: "2c" });
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    try { setDevices(await api.listDevices()); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    setAdding(true);
    try {
      await api.createDevice(form);
      setShowAdd(false);
      setForm({ name: "", hostname: "", port: 161, community: "public", snmp_version: "2c" });
      load();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete device "${name}"?`)) return;
    try { await api.deleteDevice(id); load(); }
    catch (err: any) { alert(err.message); }
  };

  if (loading) return <div className="flex h-64 items-center justify-center text-slate-400">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Devices</h1>
        <div className="flex items-center gap-2">
          <button onClick={load} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white bg-surface-card border border-surface-border rounded-lg px-3 py-2 transition-colors">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 text-sm text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg px-3 py-2 transition-colors">
            <Plus className="w-4 h-4" /> Add Device
          </button>
        </div>
      </div>

      {devices.length === 0 ? (
        <EmptyState message="No devices. Add one to start monitoring." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-left text-slate-400">
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Host</th>
                <th className="px-5 py-3 font-medium">Vendor</th>
                <th className="px-5 py-3 font-medium">Interfaces</th>
                <th className="px-5 py-3 font-medium">Alerts</th>
                <th className="px-5 py-3 font-medium">Last Polled</th>
                <th className="px-5 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.id} className="border-b border-surface-border last:border-0 hover:bg-surface-hover transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <StatusDot status={d.status} />
                      <StatusBadge status={d.status} />
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <Link to={`/devices/${d.id}`} className="text-emerald-400 hover:text-emerald-300 font-medium">
                      {d.name}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-slate-400">{d.hostname}:{d.port}</td>
                  <td className="px-5 py-3 text-slate-400">{d.vendor || "—"}</td>
                  <td className="px-5 py-3 text-slate-400">{d.interface_count}</td>
                  <td className="px-5 py-3">
                    {d.open_alerts > 0 ? (
                      <span className="badge badge-critical">{d.open_alerts}</span>
                    ) : (
                      <span className="text-slate-500">0</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-slate-500 text-xs">
                    {d.last_polled ? new Date(d.last_polled).toLocaleTimeString() : "—"}
                  </td>
                  <td className="px-5 py-3">
                    <button onClick={() => handleDelete(d.id, d.name)} className="p-1 text-slate-500 hover:text-red-400 transition-colors" title="Delete">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add device modal */}
      {showAdd && (
        <div className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center px-4">
          <div className="bg-surface-card border border-surface-border rounded-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Add Device</h2>
              <button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
              <input placeholder="Hostname / IP" value={form.hostname} onChange={(e) => setForm({ ...form, hostname: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
              <div className="grid grid-cols-2 gap-3">
                <input type="number" placeholder="Port" value={form.port} onChange={(e) => setForm({ ...form, port: +e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
                <input placeholder="Community" value={form.community} onChange={(e) => setForm({ ...form, community: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
              </div>
              <select value={form.snmp_version} onChange={(e) => setForm({ ...form, snmp_version: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50">
                <option value="2c">SNMPv2c</option>
                <option value="1">SNMPv1</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white rounded-lg transition-colors">Cancel</button>
              <button onClick={handleAdd} disabled={adding || !form.name || !form.hostname} className="px-4 py-2 text-sm text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg transition-colors">
                {adding ? "Adding…" : "Add Device"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

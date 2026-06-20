import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import * as api from "../api";
import type { Device } from "../api";
import { StatusDot, StatusBadge, EmptyState } from "../components/UI";
import { Plus, Trash2, RefreshCw, X } from "lucide-react";

const emptyDeviceForm = {
  name: "",
  hostname: "",
  port: 161,
  community: "public",
  snmp_version: "2c",
  snmpv3_username: "",
  snmpv3_security_level: "noAuthNoPriv",
  snmpv3_auth_protocol: "sha",
  snmpv3_auth_password: "",
  snmpv3_priv_protocol: "aes128",
  snmpv3_priv_password: "",
  snmpv3_context_name: "",
};

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(emptyDeviceForm);
  const [adding, setAdding] = useState(false);
  const isV3 = form.snmp_version === "3";
  const needsAuth = isV3 && form.snmpv3_security_level !== "noAuthNoPriv";
  const needsPriv = isV3 && form.snmpv3_security_level === "authPriv";

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
      setForm(emptyDeviceForm);
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
              <select value={form.snmp_version} onChange={(e) => setForm({ ...form, snmp_version: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50">
                <option value="2c">SNMPv2c</option>
                <option value="1">SNMPv1</option>
                <option value="3">SNMPv3</option>
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input type="number" placeholder="Port" value={form.port} onChange={(e) => setForm({ ...form, port: +e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
                {!isV3 && (
                  <input placeholder="Community" value={form.community} onChange={(e) => setForm({ ...form, community: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
                )}
                {isV3 && (
                  <input placeholder="Context name" value={form.snmpv3_context_name} onChange={(e) => setForm({ ...form, snmpv3_context_name: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
                )}
              </div>
              {isV3 && (
                <div className="space-y-3 border-t border-surface-border pt-3">
                  <input placeholder="SNMPv3 username" value={form.snmpv3_username} onChange={(e) => setForm({ ...form, snmpv3_username: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
                  <select value={form.snmpv3_security_level} onChange={(e) => setForm({ ...form, snmpv3_security_level: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50">
                    <option value="noAuthNoPriv">No auth, no privacy</option>
                    <option value="authNoPriv">Auth, no privacy</option>
                    <option value="authPriv">Auth and privacy</option>
                  </select>
                  {needsAuth && (
                    <div className="grid grid-cols-2 gap-3">
                      <select value={form.snmpv3_auth_protocol} onChange={(e) => setForm({ ...form, snmpv3_auth_protocol: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50">
                        <option value="sha">SHA</option>
                        <option value="sha224">SHA-224</option>
                        <option value="sha256">SHA-256</option>
                        <option value="sha384">SHA-384</option>
                        <option value="sha512">SHA-512</option>
                        <option value="md5">MD5</option>
                      </select>
                      <input type="password" placeholder="Auth password" value={form.snmpv3_auth_password} onChange={(e) => setForm({ ...form, snmpv3_auth_password: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
                    </div>
                  )}
                  {needsPriv && (
                    <div className="grid grid-cols-2 gap-3">
                      <select value={form.snmpv3_priv_protocol} onChange={(e) => setForm({ ...form, snmpv3_priv_protocol: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50">
                        <option value="aes128">AES-128</option>
                        <option value="aes192">AES-192</option>
                        <option value="aes256">AES-256</option>
                        <option value="des">DES</option>
                      </select>
                      <input type="password" placeholder="Privacy password" value={form.snmpv3_priv_password} onChange={(e) => setForm({ ...form, snmpv3_priv_password: e.target.value })} className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50" />
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white rounded-lg transition-colors">Cancel</button>
              <button onClick={handleAdd} disabled={adding || !form.name || !form.hostname || (isV3 && !form.snmpv3_username) || (needsAuth && !form.snmpv3_auth_password) || (needsPriv && !form.snmpv3_priv_password)} className="px-4 py-2 text-sm text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg transition-colors">
                {adding ? "Adding…" : "Add Device"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

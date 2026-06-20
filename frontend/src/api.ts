/**
 * API client — thin fetch wrapper with credential forwarding.
 * All calls are relative (the Vite dev proxy forwards /api/* to the backend).
 */
const BASE = "";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new ApiError(401, "Not authenticated");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  return res.json();
}

// --- Auth ---
export const login = (username: string, password: string) =>
  request<{ id: number; username: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
export const logout = () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
export const me = () => request<{ id: number; username: string }>("/api/auth/me");

// --- Devices ---
export interface Device {
  id: number;
  name: string;
  hostname: string;
  port: number;
  community: string;
  snmp_version: string;
  enabled: number;
  status: string;
  sysname: string | null;
  vendor: string | null;
  interface_count: number;
  open_alerts: number;
  last_polled: string | null;
  reason: string | null;
}
export const listDevices = () => request<Device[]>("/api/devices");
export const getDevice = (id: number) => request<Device>(`/api/devices/${id}`);
export const createDevice = (d: Partial<Device>) =>
  request<{ id: number; ok: boolean }>("/api/devices", { method: "POST", body: JSON.stringify(d) });
export const deleteDevice = (id: number) =>
  request<{ ok: boolean }>(`/api/devices/${id}`, { method: "DELETE" });
export const pollDevice = (id: number) =>
  request<{ ok: boolean }>(`/api/devices/${id}/poll`, { method: "POST" });

// --- Interfaces ---
export interface Interface {
  id: number;
  device_id: number;
  ifindex: number;
  name: string;
  alias: string;
  descr: string;
  speed: number;
  admin_status: string;
  oper_status: string;
  in_pct: number | null;
  out_pct: number | null;
  in_bps: number | null;
  out_bps: number | null;
  // Joined in from devices table by getInterface().
  device_name?: string;
}
export const deviceInterfaces = (deviceId: number) =>
  request<Interface[]>(`/api/devices/${deviceId}/interfaces`);
export const getInterface = (id: number) =>
  request<Interface & { device_name: string }>(`/api/interfaces/${id}`);

// --- Metrics ---
export interface Metric {
  ts: string;
  in_octets: number | null;
  out_octets: number | null;
  in_errors: number | null;
  out_errors: number | null;
  in_discards: number | null;
  out_discards: number | null;
  in_bps: number | null;
  out_bps: number | null;
  in_pct: number | null;
  out_pct: number | null;
}
export const interfaceMetrics = (id: number, range = "1h") =>
  request<Metric[]>(`/api/interfaces/${id}/metrics?range=${range}`);

// --- Alerts ---
export interface Alert {
  id: number;
  device_id: number;
  interface_id: number;
  ts: string;
  type: string;
  severity: string;
  message: string;
  resolved_at: string | null;
  acknowledged: number;
  device_name: string | null;
  interface_name: string | null;
}
export const listAlerts = (resolved?: boolean, limit = 100) => {
  const q = new URLSearchParams({ limit: String(limit) });
  if (resolved !== undefined) q.set("resolved", String(resolved));
  return request<Alert[]>(`/api/alerts?${q}`);
};
export const ackAlert = (id: number) =>
  request<{ ok: boolean }>(`/api/alerts/${id}/ack`, { method: "POST", body: JSON.stringify({ acknowledged: true }) });
export const resolveAlert = (id: number) =>
  request<{ ok: boolean }>(`/api/alerts/${id}`, { method: "DELETE" });

// --- Dashboard ---
export interface DashboardData {
  devices: { up: number; down: number; unknown: number; total: number };
  interfaces: { up: number; down: number; total: number };
  open_alerts: number;
  top_interfaces: Array<{
    interface_id: number; interface_name: string;
    device_id: number; device_name: string;
    in_pct: number | null; out_pct: number | null;
    in_bps: number | null; out_bps: number | null;
    speed: number; ts: string;
  }>;
  recent_alerts: Alert[];
}
export const dashboard = () => request<DashboardData>("/api/dashboard");

// --- Helpers ---
export function fmtBps(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)} Gbps`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} Mbps`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)} Kbps`;
  return `${n.toFixed(0)} bps`;
}

export function fmtPct(n: number | null): string {
  if (n == null) return "—";
  return `${n.toFixed(1)}%`;
}

export function fmtSpeed(n: number): string {
  if (n >= 1_000_000_000) return `${n / 1_000_000_000}G`;
  if (n >= 1_000_000) return `${n / 1_000_000}M`;
  if (n >= 1_000) return `${n / 1_000}K`;
  return `${n}`;
}

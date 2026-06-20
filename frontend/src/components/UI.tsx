import clsx from "clsx";

/* ------------------------------------------------------------------ */
/* Status dot / badge                                                  */
/* ------------------------------------------------------------------ */
export function StatusDot({ status }: { status: string }) {
  const color =
    status === "up" ? "bg-emerald-400" :
    status === "down" ? "bg-red-400" :
    "bg-slate-500";
  return (
    <span className={clsx("inline-block w-2.5 h-2.5 rounded-full", color)} />
  );
}

export function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "up" ? "badge badge-up" :
    status === "down" ? "badge badge-down" :
    "badge badge-info";
  return <span className={cls}>{status}</span>;
}

export function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "critical" ? "badge badge-critical" :
    severity === "warning" ? "badge badge-warning" :
    "badge badge-info";
  return <span className={cls}>{severity}</span>;
}

/* ------------------------------------------------------------------ */
/* Stat card                                                            */
/* ------------------------------------------------------------------ */
export function StatCard({ label, value, icon, color }: {
  label: string; value: string | number;
  icon: React.ReactNode; color: string;
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className={clsx("w-12 h-12 rounded-xl flex items-center justify-center", color)}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-sm text-slate-400">{label}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Toast notification (for SSE alerts)                                   */
/* ------------------------------------------------------------------ */
import { X } from "lucide-react";

export interface Toast {
  id: number;
  severity: string;
  message: string;
}

export function ToastContainer({ toasts, onDismiss }: {
  toasts: Toast[];
  onDismiss: (id: number) => void;
}) {
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={clsx(
            "rounded-lg border px-4 py-3 shadow-lg flex items-start gap-3 animate-slide-in",
            t.severity === "critical" ? "bg-red-500/15 border-red-500/30 text-red-300" :
            t.severity === "warning" ? "bg-amber-500/15 border-amber-500/30 text-amber-300" :
            "bg-blue-500/15 border-blue-500/30 text-blue-300"
          )}
        >
          <p className="flex-1 text-sm">{t.message}</p>
          <button onClick={() => onDismiss(t.id)} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Loading skeleton                                                      */
/* ------------------------------------------------------------------ */
export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded bg-surface-hover", className)} />;
}

/* ------------------------------------------------------------------ */
/* Empty state                                                          */
/* ------------------------------------------------------------------ */
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-500">
      <p className="text-lg">{message}</p>
    </div>
  );
}

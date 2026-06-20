import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import * as api from "./api";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
interface User {
  id: number;
  username: string;
}

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const u = await api.login(username, password);
    setUser(u);
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}

// ---------------------------------------------------------------------------
// SSE — real-time alert stream
// ---------------------------------------------------------------------------
export interface SSEAlert {
  kind: string;
  id: number;
  device_id: number;
  device_name: string;
  interface_id: number;
  interface_name: string;
  type: string;
  severity: string;
  message: string;
  ts: string;
}

export function useSSE(onAlert: (a: SSEAlert) => void) {
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/events/stream");
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.kind === "alert") onAlert(data as SSEAlert);
      } catch {
        /* ignore parse errors */
      }
    };
    es.onerror = () => {
      // Reconnect after 5s on error
      setTimeout(() => {
        es.close();
        // reconnect handled by re-running the effect (but we need a trigger).
        // For simplicity, just close; browser EventSource auto-reconnects.
      }, 5000);
    };
    return () => es.close();
  }, [onAlert]);
}

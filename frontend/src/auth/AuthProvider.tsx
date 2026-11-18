import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";

type Role = "admin" | "dosen" | "mahasiswa";
type AppUser = { auth: User; role: Role; nama: string };
type AuthContextValue = {
  user: AppUser | null;
  session: Session | null;
  loading: boolean;
  error: string;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  user: null,
  session: null,
  loading: true,
  error: "",
  signOut: async () => undefined,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestId = useRef(0);

  const loadUser = useCallback(async (currentSession: Session | null) => {
    const id = ++requestId.current;
    setError("");
    if (!currentSession?.user) {
      setSession(null);
      setUser(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const { data, error: profileError } = await supabase
        .from("profiles")
        .select("role,nama")
        .eq("id", currentSession.user.id)
        .maybeSingle();
      if (profileError) throw profileError;
      if (id !== requestId.current) return;
      if (!data || !["admin", "dosen", "mahasiswa"].includes(data.role)) {
        await supabase.auth.signOut();
        setSession(null);
        setUser(null);
      } else {
        setSession(currentSession);
        setUser({ auth: currentSession.user, role: data.role as Role, nama: data.nama });
      }
    } catch {
      if (id === requestId.current) {
        setSession(currentSession);
        setUser(null);
        setError("Akun belum dapat diverifikasi. Periksa koneksi lalu muat ulang.");
      }
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void supabase.auth.getSession().then(({ data, error: sessionError }) => {
      if (!active) return;
      if (sessionError) {
        setError("Sesi belum dapat diperiksa. Muat ulang halaman untuk mencoba kembali.");
        setLoading(false);
        return;
      }
      void loadUser(data.session);
    });
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      queueMicrotask(() => {
        if (active) void loadUser(currentSession);
      });
    });
    return () => {
      active = false;
      subscription.subscription.unsubscribe();
    };
  }, [loadUser]);

  async function signOut() {
    const { error: signOutError } = await supabase.auth.signOut();
    if (signOutError) throw signOutError;
    setUser(null);
    setSession(null);
    setError("");
  }

  return (
    <AuthContext.Provider value={{ user, session, loading, error, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

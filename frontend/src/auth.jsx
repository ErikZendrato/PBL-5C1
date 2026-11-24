import { createContext, useContext, useEffect, useState } from "react";
import { api, supabase } from "./api.js";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) { setMe(null); setLoading(false); return; }
    try { setMe(await api("/me")); } catch { setMe(null); }
    setLoading(false);
  };

  useEffect(() => {
    load();
    const { data } = supabase.auth.onAuthStateChange(() => { load(); });
    return () => data.subscription.unsubscribe();
  }, []);

  const login = async (email, password) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };
  const logout = () => supabase.auth.signOut();

  return <Ctx.Provider value={{ me, loading, login, logout }}>{children}</Ctx.Provider>;
}

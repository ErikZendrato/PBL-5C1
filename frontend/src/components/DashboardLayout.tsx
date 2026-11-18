import { useEffect, useMemo, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3, BookOpen, Database, GraduationCap, LayoutDashboard, LogOut,
  Search, UserRound, Users,
} from "lucide-react";
import { useAuth } from "../auth/AuthProvider";
import { ThemeToggle } from "../pages/RolePage";
import { Toast } from "./SharedUI";

type MenuItem = { to: string; label: string; icon: typeof LayoutDashboard };
const MENUS: Record<"admin" | "dosen" | "mahasiswa", MenuItem[]> = {
  admin: [
    { to: "/admin", label: "Ringkasan", icon: LayoutDashboard },
    { to: "/admin/mahasiswa", label: "Mahasiswa", icon: Users },
    { to: "/admin/akun", label: "Akun pengguna", icon: UserRound },
    { to: "/admin/lainnya", label: "Data & model", icon: Database },
  ],
  dosen: [
    { to: "/dosen", label: "Ringkasan", icon: LayoutDashboard },
    { to: "/dosen/mahasiswa", label: "Mahasiswa bimbingan", icon: Users },
    { to: "/dosen/prediksi", label: "Prediksi manual", icon: BarChart3 },
  ],
  mahasiswa: [
    { to: "/mahasiswa", label: "Performa saya", icon: BookOpen },
  ],
};

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const role = user?.role ?? "mahasiswa";
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const labels = { admin: "Admin", dosen: "Dosen wali", mahasiswa: "Mahasiswa" };
  const pageTitle = useMemo(() => MENUS[role].find((item) => location.pathname === item.to || (item.to !== `/${role}` && location.pathname.startsWith(item.to)))?.label ?? labels[role], [labels, location.pathname, role]);

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") === "dark" ? "dark" : "light";
    setTheme(savedTheme);
    document.documentElement.dataset.theme = savedTheme;
  }, []);

  function searchPage(value: string) {
    setSearch(value);
    window.dispatchEvent(new CustomEvent("app-search", { detail: value }));
  }

  async function logOut() {
    try {
      await signOut();
      navigate("/login", { replace: true });
    } catch {
      setToast("Belum berhasil keluar. Coba lagi.");
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to={`/${role}`} aria-label="Performa Akademik — beranda">
          <span className="brand-icon"><GraduationCap aria-hidden="true" /></span>
          <span className="brand-copy"><strong>Performa Akademik</strong><small>{labels[role]}</small></span>
        </NavLink>
        <nav className="sidebar-nav" aria-label="Navigasi utama">
          {MENUS[role].map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === `/${role}`} className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
              <Icon size={20} aria-hidden="true" /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-profile">
          <span className="avatar">{(user?.nama ?? "U").slice(0, 1).toLocaleUpperCase("id-ID")}</span>
          <span className="profile-copy"><strong>{user?.nama ?? "Pengguna"}</strong><small>{labels[role]}</small></span>
          <button type="button" className="icon-button logout-icon" aria-label="Keluar" onClick={() => void logOut()}><LogOut size={18} /></button>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-title"><p className="eyebrow">{labels[role]}</p><h1>{pageTitle}</h1></div>
          <label className="global-search"><Search size={18} aria-hidden="true" /><input value={search} onChange={(event) => searchPage(event.target.value)} placeholder="Cari di halaman ini" aria-label="Cari di halaman ini" /></label>
          <div className="topbar-actions"><ThemeToggle /><button type="button" className="avatar topbar-avatar" aria-label={`Keluar dari akun ${user?.nama ?? "pengguna"}`} title="Keluar" onClick={() => void logOut()}>{(user?.nama ?? "U").slice(0, 1).toLocaleUpperCase("id-ID")}</button></div>
        </header>
        <div className="page-content">{children}</div>
      </main>
      <nav className="mobile-nav" aria-label="Navigasi bawah">
        {MENUS[role].slice(0, 4).map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === `/${role}`} className={({ isActive }) => `mobile-nav-item${isActive ? " active" : ""}`} aria-label={label}>
            <Icon size={20} aria-hidden="true" /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <Toast message={toast} kind="error" onClose={() => setToast("")} />
    </div>
  );
}

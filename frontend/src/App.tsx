import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthProvider";
import LoginPage from "./pages/LoginPage";
import DashboardLayout from "./components/DashboardLayout";
import RolePage from "./pages/RolePage";

function ProtectedRoute({ role }: { role: "admin" | "dosen" | "mahasiswa" }) {
  const { user, loading, error } = useAuth();
  const location = useLocation();
  if (loading) return <div className="loading-page">Memuat akun...</div>;
  if (error) return <div className="loading-page"><p role="alert">{error}</p><button className="secondary-button" onClick={() => window.location.reload()}>Muat ulang</button></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={`/${user.role}`} replace />;
  const [, , section, detailId] = location.pathname.split("/");
  return <DashboardLayout><RolePage role={role} section={section ?? ""} detailId={detailId} /></DashboardLayout>;
}

function LoginRoute() {
  const { user, loading, error } = useAuth();
  if (loading) return <div className="loading-page">Memuat akun...</div>;
  if (error) return <div className="loading-page"><p role="alert">{error}</p><button className="secondary-button" onClick={() => window.location.reload()}>Muat ulang</button></div>;
  if (user) return <Navigate to={`/${user.role}`} replace />;
  return <LoginPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/admin/*" element={<ProtectedRoute role="admin" />} />
        <Route path="/dosen/*" element={<ProtectedRoute role="dosen" />} />
        <Route path="/mahasiswa/*" element={<ProtectedRoute role="mahasiswa" />} />
        <Route path="/" element={<RoleRedirect />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  );
}

function RoleRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-page">Memuat akun...</div>;
  return <Navigate to={user ? `/${user.role}` : "/login"} replace />;
}

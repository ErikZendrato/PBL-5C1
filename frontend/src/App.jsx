import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import { Layout } from "./components.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import { Alerts, History, PredictionDetail, Predictions } from "./pages/Predictions.jsx";
import Crud from "./pages/Crud.jsx";
import { Audit, Completeness, ImportCsv, Models, Users } from "./pages/AdminPages.jsx";
import { GradeEntry, MyCourses } from "./pages/DosenPages.jsx";
import StudentHome from "./pages/StudentHome.jsx";

export default function App() {
  const { me, loading } = useAuth();
  if (loading) return <p style={{ padding: 24 }}>Memuat...</p>;
  if (!me) return <Login />;

  const shared = (
    <>
      <Route path="/predictions" element={<Predictions />} />
      <Route path="/predictions/:sid" element={<PredictionDetail />} />
      <Route path="/alerts" element={<Alerts />} />
      <Route path="/history" element={<History />} />
    </>
  );
  return (
    <Layout>
      <Routes>
        {me.role === "mahasiswa" && <Route path="/" element={<StudentHome />} />}
        {me.role === "dosen" && (
          <>
            <Route path="/" element={<Dashboard />} />
            <Route path="/courses" element={<MyCourses />} />
            <Route path="/courses/:aid" element={<GradeEntry />} />
            {shared}
          </>
        )}
        {me.role === "admin" && (
          <>
            <Route path="/" element={<Dashboard />} />
            <Route path="/master/:table" element={<Crud />} />
            <Route path="/import" element={<ImportCsv />} />
            <Route path="/completeness" element={<Completeness />} />
            <Route path="/users" element={<Users />} />
            <Route path="/models" element={<Models />} />
            <Route path="/audit" element={<Audit />} />
            {shared}
          </>
        )}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

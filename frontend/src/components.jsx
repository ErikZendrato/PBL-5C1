import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "./auth.jsx";

export const CAT = {
  stabil: ["Stabil", "g"],
  berpotensi_meningkat: ["Berpotensi meningkat", "i"],
  berpotensi_menurun: ["Berpotensi menurun", "a"],
};
export const Cat = ({ c }) => <span className={`badge ${CAT[c]?.[1]}`}>{CAT[c]?.[0] ?? c}</span>;
export const fmt = (x, d = 2) => (x === null || x === undefined ? "-" : Number(x).toFixed(d).replace(".", ","));

export const MENU = {
  admin: [
    ["/", "Dashboard"], ["/predictions", "Prediksi"], ["/alerts", "Peringatan Dini"], ["/history", "Riwayat Prediksi"],
    ["/master/students", "Mahasiswa"], ["/master/courses", "Mata Kuliah"], ["/master/semesters", "Semester"],
    ["/master/academic_programs", "Program Studi"], ["/master/course_assignments", "Penugasan Dosen"],
    ["/master/enrollments", "KRS"], ["/import", "Impor CSV"], ["/completeness", "Kelengkapan Nilai"],
    ["/users", "Pengguna"], ["/models", "Model & Prediksi"], ["/audit", "Audit Log"],
  ],
  dosen: [["/", "Dashboard"], ["/courses", "Mata Kuliah Saya"], ["/predictions", "Prediksi"],
    ["/alerts", "Peringatan Dini"], ["/history", "Riwayat Prediksi"]],
  mahasiswa: [["/", "Beranda"]],
};
const ROLE = { admin: "Admin", dosen: "Dosen", mahasiswa: "Mahasiswa" };

export function Layout({ children }) {
  const { me, logout } = useAuth();
  const initial = (me.name || "?").trim().charAt(0).toUpperCase();
  return (
    <div className="app">
      <aside className="side">
        <div className="brand">Prediksi<br />Performa Akademik</div>
        <nav>
          {MENU[me.role].map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>
          ))}
        </nav>
        <div className="profile">
          <div className="avatar">{initial}</div>
          <div className="pinfo">
            <b title={me.name}>{me.name}</b>
            <span>{ROLE[me.role]}</span>
          </div>
          <button className="logout" onClick={logout} title="Keluar" aria-label="Keluar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

export const Head = ({ title, sub, children }) => (
  <div className="head">
    <div><h1>{title}</h1>{sub && <p className="lbl" style={{ marginTop: 4 }}>{sub}</p>}</div>
    <div className="row">{children}</div>
  </div>
);
export const Stat = ({ label, value, sub }) => (
  <div className="card stat"><p className="lbl">{label}</p><b>{value}</b>{sub && <p className="lbl">{sub}</p>}</div>
);
export const Err = ({ msg }) => (msg ? <div className="err">{msg}</div> : null);
export const Disclaimer = () => (
  <div className="note">Prediksi adalah estimasi berbasis data, bukan nilai akademik resmi. Peringatan dini adalah
    indikator untuk pemeriksaan lebih lanjut, bukan bukti bahwa mahasiswa pasti mengalami masalah akademik.</div>
);

export function Table({ cols, rows, empty = "Belum ada data." }) {
  return (
    <div className="tbl">
      <table>
        <thead><tr>{cols.map((c) => <th key={c.label}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => <tr key={r.id ?? i}>{cols.map((c) => <td key={c.label}>{c.render ? c.render(r) : r[c.key]}</td>)}</tr>)}
          {rows.length === 0 && <tr><td colSpan={cols.length} className="lbl">{empty}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

/** records: [{semester, ip}], pred: {target, value} (opsional, digambar putus-putus) */
export function IpChart({ records, pred }) {
  const data = records.map((r) => ({ semester: r.semester, ip: r.ip }));
  if (pred && pred.value != null) {
    if (data.length) data[data.length - 1].pred = data[data.length - 1].ip;
    data.push({ semester: pred.target, pred: pred.value });
  }
  const dom = [(m) => Math.max(0, Math.floor((m - 0.3) * 10) / 10), (m) => Math.min(4, Math.ceil((m + 0.3) * 10) / 10)];
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e1e6ef" />
        <XAxis dataKey="semester" /><YAxis domain={dom} /><Tooltip />
        <Line dataKey="ip" name="IP" stroke="#2457c5" strokeWidth={3} connectNulls />
        <Line dataKey="pred" name="Prediksi" stroke="#b45309" strokeWidth={3} strokeDasharray="6 5" connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function useLoad(fn, deps = []) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const reload = () => { setErr(""); fn().then(setData).catch((e) => setErr(e.message)); };
  useEffect(reload, deps); // eslint-disable-line
  return { data, err, reload, setData };
}
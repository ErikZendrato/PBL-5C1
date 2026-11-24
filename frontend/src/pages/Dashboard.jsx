import { Link } from "react-router-dom";
import { Cat, Disclaimer, Err, fmt, Head, IpChart, Stat, Table, useLoad } from "../components.jsx";
import { api } from "../api.js";

const BARS = [["stabil", "Stabil", "#1b7f4b"], ["berpotensi_meningkat", "Berpotensi meningkat", "#2457c5"],
  ["berpotensi_menurun", "Berpotensi menurun", "#b45309"]];

export default function Dashboard() {
  const { data: d, err } = useLoad(() => api("/dashboard"));
  if (err) return <Err msg={err} />;
  if (!d) return <p>Memuat...</p>;
  const total = Object.values(d.categories).reduce((a, b) => a + b, 0) || 1;
  return (
    <>
      <Head title="Dashboard" sub={d.target ? `Ringkasan performa dan prediksi untuk semester ${d.target}` : "Belum ada prediksi. Admin perlu melatih model dan menjalankan prediksi."} />
      <div className="grid4">
        <Stat label="Total mahasiswa" value={d.total_students} />
        <Stat label="Rata-rata IPK" value={fmt(d.avg_ipk)} sub="IPK terakhir" />
        <Stat label="Rata-rata prediksi IP" value={fmt(d.avg_pred_ip)} sub={d.target ? `Semester ${d.target} (estimasi)` : ""} />
        <Stat label="Perlu pendampingan" value={d.need_attention} sub="Berpotensi menurun, belum ditindaklanjuti" />
      </div>
      <div className="grid2">
        <div className="card">
          <h3>Rata-rata IP per semester</h3>
          <p className="lbl" style={{ margin: "4px 0 12px" }}>Garis putus-putus adalah hasil prediksi</p>
          <IpChart records={d.trend} pred={d.target ? { target: d.target, value: d.avg_pred_ip } : null} />
        </div>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h3>Kategori performa</h3>
          {BARS.map(([k, l, c]) => (
            <div key={k}>
              <div className="row" style={{ justifyContent: "space-between", fontSize: 14 }}><span>{l}</span><b>{d.categories[k]}</b></div>
              <div className="bar"><i style={{ width: `${(d.categories[k] / total) * 100}%`, background: c }} /></div>
            </div>
          ))}
        </div>
      </div>
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}><h3>Mahasiswa yang perlu diperhatikan</h3><Link to="/alerts">Lihat semua</Link></div>
        <Table rows={d.watchlist} empty="Tidak ada peringatan." cols={[
          { label: "Mahasiswa", render: (r) => <Link to={`/predictions/${r.student_id}`}>{r.name}</Link> },
          { label: "IP terakhir", render: (r) => fmt(r.last_ip) },
          { label: "Prediksi IP", render: (r) => <b>{fmt(r.predicted_ip)}</b> },
          { label: "Kategori", render: (r) => <Cat c={r.category} /> },
        ]} />
      </div>
      <Disclaimer />
    </>
  );
}

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { Cat, Disclaimer, Err, fmt, Head, IpChart, Stat, Table, useLoad } from "../components.jsx";

export function Predictions() {
  const [sem, setSem] = useState("");
  const meta = useLoad(() => api("/meta"));
  const { data, err } = useLoad(() => api(`/predictions${sem ? `?semester_id=${sem}` : ""}`), [sem]);
  const [q, setQ] = useState("");
  const rows = (data?.rows ?? []).filter((r) => `${r.name} ${r.student_number}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <>
      <Head title="Daftar Prediksi" sub={data?.target ? `Estimasi IP semester ${data.target}` : "Belum ada prediksi"}>
        <input type="text" placeholder="Cari nama atau ID" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 220 }} />
        <select value={sem} onChange={(e) => setSem(e.target.value)} style={{ width: 160 }}>
          <option value="">Semester terbaru</option>
          {meta.data?.semesters.map((s) => <option key={s.id} value={s.id}>{s.code}</option>)}
        </select>
      </Head>
      <Err msg={err} />
      <div className="card">
        <Table rows={rows} cols={[
          { label: "ID", key: "student_number" },
          { label: "Mahasiswa", render: (r) => <b>{r.name}</b> },
          { label: "IP terakhir", render: (r) => fmt(r.last_ip) },
          { label: "Prediksi IP", render: (r) => <b>{fmt(r.predicted_ip)}</b> },
          { label: "Prediksi IPK", render: (r) => fmt(r.predicted_ipk) },
          { label: "Kategori", render: (r) => <Cat c={r.category} /> },
          { label: "", render: (r) => <Link to={`/predictions/${r.student_id}`}>Detail</Link> },
        ]} />
      </div>
      <Disclaimer />
    </>
  );
}

export function PredictionDetail() {
  const { sid } = useParams();
  const { data: d, err } = useLoad(() => api(`/predictions/student/${sid}`), [sid]);
  if (err) return <Err msg={err} />;
  if (!d) return <p>Memuat...</p>;
  const p = d.predictions[d.predictions.length - 1];
  const lastRec = d.records[d.records.length - 1];
  return (
    <>
      <Head title={d.student.full_name} sub={`${d.student.academic_programs?.name ?? ""} · Angkatan ${d.student.entry_year} · ID ${d.student.student_number}`} />
      <div className="grid4">
        <Stat label={p ? `Estimasi IP ${p.target}` : "Estimasi IP"} value={fmt(p?.predicted_ip)} sub={p ? <Cat c={p.category} /> : "Belum ada prediksi"} />
        <Stat label="Estimasi IPK" value={fmt(p?.predicted_ipk)} />
        <Stat label="IPK saat ini" value={fmt(lastRec?.ipk)} />
        <Stat label="SKS semester terakhir" value={lastRec?.sks ?? "-"} />
      </div>
      <div className="card">
        <h3>Perkembangan IP</h3>
        <p className="lbl" style={{ margin: "4px 0 12px" }}>Garis putus-putus adalah hasil prediksi</p>
        <IpChart records={d.records} pred={p ? { target: p.target, value: p.predicted_ip } : null} />
      </div>
      <div className="card">
        <h3>Riwayat prediksi mahasiswa ini</h3>
        <Table rows={d.predictions} cols={[
          { label: "Semester sasaran", key: "target" },
          { label: "Prediksi IP", render: (r) => fmt(r.predicted_ip) },
          { label: "Nilai aktual", render: (r) => (r.actual_ip == null ? "Menunggu" : fmt(r.actual_ip)) },
          { label: "Kategori", render: (r) => <Cat c={r.category} /> },
        ]} />
      </div>
      <Disclaimer />
    </>
  );
}

export function Alerts() {
  const { data, err, reload } = useLoad(() => api("/alerts"));
  const [msg, setMsg] = useState("");
  const follow = async (id) => {
    try { await api(`/alerts/${id}/follow-up`, { method: "POST" }); reload(); } catch (e) { setMsg(e.message); }
  };
  return (
    <>
      <Head title="Peringatan Dini" sub={data?.target ? `Mahasiswa yang diperkirakan IP-nya turun pada semester ${data.target}` : ""} />
      <Disclaimer /><Err msg={err || msg} />
      <div className="grid3">
        {data?.rows.map((r) => (
          <div className="card" key={r.id} style={{ display: "flex", flexDirection: "column", gap: 10, opacity: r.followed_up ? 0.6 : 1 }}>
            <div className="row" style={{ justifyContent: "space-between" }}><b>{r.name}</b><Cat c={r.category} /></div>
            <p className="lbl">ID {r.student_number}</p>
            <p style={{ fontSize: 14 }}>IP terakhir {fmt(r.last_ip)} menjadi estimasi {fmt(r.predicted_ip)}.</p>
            <div className="row">
              <Link className="btn small" to={`/predictions/${r.student_id}`}>Lihat detail</Link>
              {r.followed_up ? <span className="badge g">Sudah ditindaklanjuti</span>
                : <button className="btn secondary small" onClick={() => follow(r.id)}>Tandai ditindaklanjuti</button>}
            </div>
          </div>
        ))}
      </div>
      {data && data.rows.length === 0 && <p className="lbl">Tidak ada peringatan.</p>}
    </>
  );
}

export function History() {
  const { data, err } = useLoad(() => api("/history"));
  return (
    <>
      <Head title="Riwayat Prediksi" sub="Prediksi tersimpan dan perbandingannya dengan nilai aktual" />
      <Err msg={err} />
      <div className="grid4">
        <Stat label="Prediksi tersimpan" value={data?.rows.length ?? "-"} />
        <Stat label="Sudah ada nilai aktual" value={data?.with_actual ?? "-"} />
        <Stat label="Rata-rata selisih" value={fmt(data?.mean_abs_error, 3)} sub="Prediksi vs aktual" />
      </div>
      <div className="card">
        <Table rows={data?.rows ?? []} cols={[
          { label: "Semester sasaran", key: "target" }, { label: "Versi model", key: "version" },
          { label: "Mahasiswa", render: (r) => <b>{r.name}</b> },
          { label: "Prediksi IP", render: (r) => fmt(r.predicted_ip) },
          { label: "Nilai aktual", render: (r) => (r.actual_ip == null ? "Menunggu" : fmt(r.actual_ip)) },
          { label: "Selisih", render: (r) => fmt(r.abs_error) },
        ]} />
      </div>
    </>
  );
}

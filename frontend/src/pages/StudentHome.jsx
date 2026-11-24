import { api } from "../api.js";
import { Disclaimer, Err, fmt, Head, IpChart, Stat, Table, useLoad } from "../components.jsx";

export default function StudentHome() {
  const { data: d, err } = useLoad(() => api("/student/me"));
  if (err) return <Err msg={err} />;
  if (!d) return <p>Memuat...</p>;
  const last = d.records[d.records.length - 1];
  return (
    <>
      <Head title={`Halo, ${d.student.name}`} sub="Ringkasan akademik Anda" />
      <div className="grid3">
        <Stat label="IPK" value={fmt(last?.ipk)} sub={last ? `Hingga semester ${last.semester}` : ""} />
        <Stat label="IP semester terakhir" value={fmt(last?.ip)} />
        <Stat label="SKS ditempuh" value={last?.total_sks ?? "-"} />
      </div>
      <div className="grid2">
        <div className="card">
          <h3>Perkembangan IP</h3>
          <IpChart records={d.records} pred={d.prediction ? { target: d.prediction.target, value: d.prediction.predicted_ip } : null} />
        </div>
        {d.prediction && (
          <div className="card">
            <h3>Estimasi semester {d.prediction.target}</h3>
            <p style={{ fontSize: 48, fontWeight: 700, margin: "12px 0" }}>{fmt(d.prediction.predicted_ip)}</p>
            <p className="lbl">Estimasi IPK: {fmt(d.prediction.predicted_ipk)}</p>
          </div>
        )}
      </div>
      <div className="card">
        <h3>Nilai semester terakhir</h3>
        <Table rows={d.grades} cols={[{ label: "Mata kuliah", render: (r) => <b>{r.name}</b> }, { label: "SKS", key: "credits" }, { label: "Nilai", key: "letter" }]} />
      </div>
      {d.prediction && <Disclaimer />}
    </>
  );
}

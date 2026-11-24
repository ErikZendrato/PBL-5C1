import { useState } from "react";
import { api } from "../api.js";
import { Err, fmt, Head, Table, useLoad } from "../components.jsx";

const Report = ({ r }) => r && (
  <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
    <div className="ok">Berhasil: {r.inserted ?? r.saved ?? 0}{r.skipped ? ` · dilewati: ${r.skipped}` : ""}</div>
    {(r.error_count > 0 || r.errors?.length > 0) && (
      <div className="err">{r.error_count ?? r.errors.length} baris bermasalah (maks. 50 ditampilkan):
        <ul>{r.errors.map((e, i) => <li key={i}>{e}</li>)}</ul></div>
    )}
  </div>
);

const KINDS = {
  students: ["Mahasiswa", "student_number, full_name, program_code, entry_year"],
  courses: ["Mata kuliah", "code, name, credits, program_code (opsional)"],
  grades_history: ["Nilai historis (langsung final)", "student_number, course_code, semester_code, letter"],
};

export function ImportCsv() {
  const [kind, setKind] = useState("students");
  const [file, setFile] = useState(null);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setErr(""); setRes(null); setBusy(true);
    try { setRes(await api(`/admin/import/${kind}`, { method: "POST", file })); } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  return (
    <>
      <Head title="Impor Data CSV" sub="Untuk memasukkan data dalam jumlah besar, dengan laporan validasi" />
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 640 }}>
        <label className="lbl">Jenis data
          <select value={kind} onChange={(e) => { setKind(e.target.value); setRes(null); }}>
            {Object.entries(KINDS).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}
          </select></label>
        <p className="lbl">Kolom yang dibutuhkan (baris pertama sebagai header): <b>{KINDS[kind][1]}</b>.
          Pemisah koma atau titik koma. Urutan impor yang disarankan: program studi, semester, mata kuliah, mahasiswa, lalu nilai historis.</p>
        <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])} />
        <div><button className="btn" disabled={!file || busy} onClick={go}>{busy ? "Mengimpor..." : "Impor"}</button></div>
      </div>
      <Err msg={err} /><Report r={res} />
    </>
  );
}

export function Completeness() {
  const meta = useLoad(() => api("/meta"));
  const [sem, setSem] = useState("");
  const { data, err } = useLoad(() => (sem ? api(`/admin/completeness?semester_id=${sem}`) : Promise.resolve([])), [sem]);
  return (
    <>
      <Head title="Kelengkapan Nilai" sub="IP semester dihitung setelah semua mata kuliah mahasiswa berstatus final">
        <select value={sem} onChange={(e) => setSem(e.target.value)} style={{ width: 180 }}>
          <option value="">Pilih semester</option>
          {meta.data?.semesters.map((s) => <option key={s.id} value={s.id}>{s.code}</option>)}
        </select>
      </Head>
      <Err msg={err} />
      {data && data.length > 0 && <p className="lbl">{data.filter((r) => r.complete).length} dari {data.length} mata kuliah sudah final</p>}
      <div className="card">
        <Table rows={data ?? []} empty="Pilih semester untuk melihat kelengkapan." cols={[
          { label: "Mata kuliah", render: (r) => <b>{r.course.code} - {r.course.name}</b> },
          { label: "Dosen", key: "lecturer" },
          { label: "Nilai final", render: (r) => `${r.final} / ${r.total}` },
          { label: "Status", render: (r) => <span className={`badge ${r.complete ? "g" : "a"}`}>{r.complete ? "Lengkap" : "Belum lengkap"}</span> },
        ]} />
      </div>
    </>
  );
}

export function Users() {
  const { data, err, reload } = useLoad(() => api("/admin/users"));
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState("");
  const create = async (e) => {
    e.preventDefault(); setMsg("");
    try { await api("/admin/users", { method: "POST", body: form }); setForm(null); reload(); } catch (x) { setMsg(x.message); }
  };
  const patch = async (u, body) => {
    try { await api(`/admin/users/${u.id}`, { method: "PATCH", body }); reload(); } catch (x) { setMsg(x.message); }
  };
  return (
    <>
      <Head title="Pengguna dan Hak Akses" sub="Kelola akun serta peran Admin, Dosen, dan Mahasiswa">
        <button className="btn" onClick={() => setForm({ role: "dosen" })}>Tambah pengguna</button>
      </Head>
      <Err msg={err || msg} />
      {form && (
        <form className="card" onSubmit={create}>
          <div className="form">
            <label>Nama lengkap<input type="text" required onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
            <label>Email<input type="email" required onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            <label>Kata sandi awal<input type="password" required minLength={8} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
            <label>Peran<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="admin">Admin</option><option value="dosen">Dosen</option><option value="mahasiswa">Mahasiswa</option></select></label>
          </div>
          <div className="row" style={{ marginTop: 16 }}>
            <button className="btn">Simpan</button>
            <button type="button" className="btn secondary" onClick={() => setForm(null)}>Batal</button>
          </div>
        </form>
      )}
      <div className="card">
        <Table rows={data ?? []} cols={[
          { label: "Nama", render: (u) => <b>{u.full_name}</b> }, { label: "Email", key: "email" },
          { label: "Peran", render: (u) => (
            <select value={u.role} onChange={(e) => patch(u, { role: e.target.value })} style={{ width: 140 }}>
              <option value="admin">Admin</option><option value="dosen">Dosen</option><option value="mahasiswa">Mahasiswa</option></select>) },
          { label: "Status", render: (u) => <span className={`badge ${u.is_active ? "g" : "r"}`}>{u.is_active ? "Aktif" : "Nonaktif"}</span> },
          { label: "", render: (u) => <button className="btn secondary small" onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? "Nonaktifkan" : "Aktifkan"}</button> },
        ]} />
      </div>
    </>
  );
}

export function Models() {
  const { data, err, reload } = useLoad(() => api("/admin/models"));
  const meta = useLoad(() => api("/meta"));
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState("");
  const [thr, setThr] = useState("");
  const run = async (fn) => {
    setMsg(null); setBusy(true);
    try { setMsg({ ok: true, t: await fn() }); reload(); } catch (e) { setMsg({ ok: false, t: e.message }); }
    setBusy(false);
  };
  const train = () => run(async () => {
    const r = await api("/admin/models/train", { method: "POST" });
    return `Model ${r.model.version} (${r.model.algorithm}) dilatih. MAE ${fmt(r.model.mae, 3)} vs baseline ${fmt(r.baseline.mae, 3)}. ` +
      (r.better_than_baseline ? "Lebih baik dari baseline, layak diaktifkan." : "TIDAK lebih baik dari baseline.");
  });
  const activate = (m) => run(async () => { await api(`/admin/models/${m.id}/activate`, { method: "POST" }); return `Model ${m.version} aktif.`; });
  const predict = () => run(async () => {
    const r = await api("/admin/predict", { method: "POST", body: { target_semester_id: Number(target), threshold: thr ? Number(thr) : null } });
    return `${r.count} prediksi dibuat dengan model ${r.model} (batas kategori ${r.threshold}).`;
  });
  return (
    <>
      <Head title="Model & Prediksi" sub="Latih, bandingkan dengan baseline, aktifkan, lalu jalankan prediksi">
        <button className="btn" disabled={busy} onClick={train}>{busy ? "Memproses..." : "Latih model baru"}</button>
      </Head>
      <Err msg={err} />
      {msg && <div className={msg.ok ? "ok" : "err"}>{msg.t}</div>}
      <div className="card">
        <h3>Versi model</h3>
        <Table rows={data ?? []} empty="Belum ada model." cols={[
          { label: "Versi", render: (m) => <b>{m.version}</b> }, { label: "Algoritma", key: "algorithm" },
          { label: "MAE", render: (m) => fmt(m.mae, 3) }, { label: "RMSE", render: (m) => fmt(m.rmse, 3) },
          { label: "R²", render: (m) => fmt(m.r2, 3) }, { label: "Baseline MAE", render: (m) => fmt(m.baseline_mae, 3) },
          { label: "Status", render: (m) => (m.is_active ? <span className="badge g">Aktif</span> : <span className="badge i">Arsip</span>) },
          { label: "", render: (m) => !m.is_active && <button className="btn secondary small" disabled={busy} onClick={() => activate(m)}>Aktifkan</button> },
        ]} />
      </div>
      <div className="card">
        <h3>Jalankan prediksi</h3>
        <p className="lbl" style={{ margin: "4px 0 12px" }}>Memakai model aktif dan hanya data sebelum semester sasaran. Batas kategori kosong = otomatis dari MAE model.</p>
        <div className="row">
          <select value={target} onChange={(e) => setTarget(e.target.value)} style={{ width: 200 }}>
            <option value="">Semester sasaran</option>
            {meta.data?.semesters.map((s) => <option key={s.id} value={s.id}>{s.code}</option>)}
          </select>
          <input type="number" step="0.01" placeholder="Batas kategori (opsional)" value={thr} onChange={(e) => setThr(e.target.value)} style={{ width: 220 }} />
          <button className="btn" disabled={!target || busy} onClick={predict}>Jalankan prediksi</button>
        </div>
      </div>
    </>
  );
}

export function Audit() {
  const { data, err } = useLoad(() => api("/admin/audit"));
  return (
    <>
      <Head title="Audit Log" sub="Catatan perubahan data dan aktivitas administratif (300 terbaru)" />
      <Err msg={err} />
      <div className="card">
        <Table rows={data ?? []} cols={[
          { label: "Waktu", render: (r) => new Date(r.created_at).toLocaleString("id-ID") },
          { label: "Pengguna", render: (r) => r.profiles?.full_name ?? "Sistem/backend" },
          { label: "Aksi", key: "action" }, { label: "Tabel", key: "table_name" }, { label: "ID", key: "record_id" },
        ]} />
      </div>
    </>
  );
}

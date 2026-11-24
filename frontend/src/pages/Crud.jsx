import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { Err, Head, Table } from "../components.jsx";

const get = (o, path) => path.split(".").reduce((a, k) => (a == null ? a : Array.isArray(a) ? a[0]?.[k] : a[k]), o);
const prog = { ref: "academic_programs", rl: (r) => `${r.code} - ${r.name}` };

const CFG = {
  students: {
    title: "Data Mahasiswa",
    cols: [["student_number", "ID internal"], ["full_name", "Nama"], ["academic_programs.name", "Program studi"],
      ["entry_year", "Angkatan"]],
    fields: [
      { k: "student_number", l: "ID internal", req: 1 }, { k: "full_name", l: "Nama", req: 1 },
      { k: "program_id", l: "Program studi", req: 1, ...prog }, { k: "entry_year", l: "Angkatan", type: "number", req: 1 },
      { k: "advisor_id", l: "Dosen wali", ref: "users:dosen" }, { k: "profile_id", l: "Akun mahasiswa", ref: "users:mahasiswa" },
    ],
  },
  courses: {
    title: "Mata Kuliah",
    cols: [["code", "Kode"], ["name", "Nama"], ["credits", "SKS"], ["academic_programs.code", "Prodi"]],
    fields: [{ k: "code", l: "Kode", req: 1 }, { k: "name", l: "Nama", req: 1 },
      { k: "credits", l: "SKS", type: "number", req: 1 }, { k: "program_id", l: "Program studi", ...prog }],
  },
  semesters: {
    title: "Semester",
    cols: [["code", "Kode"], ["academic_year", "Tahun akademik"], ["term", "Ganjil/Genap"], ["sort_order", "Urutan"],
      ["is_active", "Aktif", (v) => (v ? "Ya" : "Tidak")]],
    fields: [{ k: "code", l: "Kode (contoh 2024-1)", req: 1 }, { k: "academic_year", l: "Tahun akademik (2024/2025)", req: 1 },
      { k: "term", l: "Term (1 ganjil, 2 genap)", type: "number", req: 1 },
      { k: "sort_order", l: "Urutan kronologis", type: "number", req: 1 }, { k: "is_active", l: "Semester aktif", type: "bool" }],
  },
  academic_programs: {
    title: "Program Studi",
    cols: [["code", "Kode"], ["name", "Nama"]],
    fields: [{ k: "code", l: "Kode", req: 1 }, { k: "name", l: "Nama", req: 1 }],
  },
  course_assignments: {
    title: "Penugasan Dosen",
    cols: [["profiles.full_name", "Dosen"], ["courses.name", "Mata kuliah"], ["semesters.code", "Semester"]],
    fields: [{ k: "lecturer_id", l: "Dosen", req: 1, ref: "users:dosen" },
      { k: "course_id", l: "Mata kuliah", req: 1, ref: "courses", rl: (r) => `${r.code} - ${r.name}` },
      { k: "semester_id", l: "Semester", req: 1, ref: "semesters", rl: (r) => r.code }],
  },
  enrollments: {
    title: "KRS (Mahasiswa per Mata Kuliah)",
    cols: [["students.student_number", "ID"], ["students.full_name", "Mahasiswa"], ["courses.name", "Mata kuliah"], ["semesters.code", "Semester"]],
    fields: [{ k: "student_id", l: "Mahasiswa", req: 1, ref: "students", rl: (r) => `${r.student_number} - ${r.full_name}` },
      { k: "course_id", l: "Mata kuliah", req: 1, ref: "courses", rl: (r) => `${r.code} - ${r.name}` },
      { k: "semester_id", l: "Semester", req: 1, ref: "semesters", rl: (r) => r.code }],
  },
};

export default function Crud() {
  const { table } = useParams();
  const cfg = CFG[table];
  const [rows, setRows] = useState([]);
  const [opts, setOpts] = useState({});
  const [form, setForm] = useState(null);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");

  const load = () => api(`/admin/tables/${table}?limit=2000`).then(setRows).catch((e) => setErr(e.message));
  useEffect(() => {
    setForm(null); setRows([]); setErr(""); setQ("");
    load();
    cfg.fields.filter((f) => f.ref).forEach(async (f) => {
      const [t, role] = f.ref.split(":");
      const list = t === "users"
        ? (await api("/admin/users")).filter((u) => u.role === role).map((u) => ({ v: u.id, t: `${u.full_name} (${u.email})` }))
        : (await api(`/admin/tables/${t}?limit=2000`)).map((r) => ({ v: r.id, t: f.rl(r) }));
      setOpts((o) => ({ ...o, [f.k]: list }));
    });
  }, [table]); // eslint-disable-line

  const save = async (e) => {
    e.preventDefault(); setErr("");
    const body = {};
    cfg.fields.forEach((f) => {
      let v = form[f.k];
      if (v === "" || v === undefined) v = null;
      if (v !== null && (f.type === "number" || (f.ref && !f.ref.startsWith("users")))) v = Number(v);
      if (f.type === "bool") v = !!form[f.k];
      body[f.k] = v;
    });
    try {
      if (form.id) await api(`/admin/tables/${table}/${form.id}`, { method: "PATCH", body });
      else await api(`/admin/tables/${table}`, { method: "POST", body });
      setForm(null); load();
    } catch (x) { setErr(x.message); }
  };
  const del = async (r) => {
    if (!confirm("Hapus data ini?")) return;
    try { await api(`/admin/tables/${table}/${r.id}`, { method: "DELETE" }); load(); } catch (x) { setErr(x.message); }
  };

  const shown = rows.filter((r) => JSON.stringify(r).toLowerCase().includes(q.toLowerCase()));
  return (
    <>
      <Head title={cfg.title} sub={`${rows.length} data`}>
        <input type="text" placeholder="Cari..." value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 200 }} />
        <button className="btn" onClick={() => setForm({})}>Tambah</button>
      </Head>
      <Err msg={err} />
      {form && (
        <form className="card" onSubmit={save}>
          <h3>{form.id ? "Ubah data" : "Tambah data"}</h3>
          <div className="form">
            {cfg.fields.map((f) => (
              <label key={f.k}>{f.l}
                {f.type === "bool" ? (
                  <input type="checkbox" checked={!!form[f.k]} onChange={(e) => setForm({ ...form, [f.k]: e.target.checked })} />
                ) : f.ref ? (
                  <select required={!!f.req} value={form[f.k] ?? ""} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })}>
                    <option value="">- pilih -</option>
                    {(opts[f.k] ?? []).map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
                  </select>
                ) : (
                  <input type={f.type === "number" ? "number" : "text"} required={!!f.req} value={form[f.k] ?? ""}
                    onChange={(e) => setForm({ ...form, [f.k]: e.target.value })} />
                )}
              </label>
            ))}
          </div>
          <div className="row" style={{ marginTop: 16 }}>
            <button className="btn">Simpan</button>
            <button type="button" className="btn secondary" onClick={() => setForm(null)}>Batal</button>
          </div>
        </form>
      )}
      <div className="card">
        <Table rows={shown} cols={[
          ...cfg.cols.map(([path, label, fn]) => ({ label, render: (r) => { const v = get(r, path); return fn ? fn(v) : v; } })),
          { label: "Aksi", render: (r) => (
            <div className="row">
              <button className="btn secondary small" onClick={() => setForm(r)}>Ubah</button>
              <button className="btn danger small" onClick={() => del(r)}>Hapus</button>
            </div>) },
        ]} />
      </div>
    </>
  );
}

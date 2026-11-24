import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { Err, Head, Table, useLoad } from "../components.jsx";

export function MyCourses() {
  const { data, err } = useLoad(() => api("/dosen/courses"));
  return (
    <>
      <Head title="Mata Kuliah Saya" sub="Mata kuliah yang Anda ampu dan status input nilainya" />
      <Err msg={err} />
      <div className="card">
        <Table rows={data ?? []} empty="Belum ada penugasan. Hubungi Admin." cols={[
          { label: "Semester", key: "semester" },
          { label: "Mata kuliah", render: (r) => <b>{r.course.code} - {r.course.name}</b> },
          { label: "SKS", render: (r) => r.course.credits },
          { label: "Nilai final", render: (r) => `${r.final} / ${r.total}` },
          { label: "Status", render: (r) => <span className={`badge ${r.total > 0 && r.final === r.total ? "g" : "a"}`}>{r.total > 0 && r.final === r.total ? "Final" : "Belum final"}</span> },
          { label: "", render: (r) => <Link className="btn small" to={`/courses/${r.id}`}>Input nilai</Link> },
        ]} />
      </div>
    </>
  );
}

export function GradeEntry() {
  const { aid } = useParams();
  const meta = useLoad(() => api("/meta"));
  const { data, err, reload } = useLoad(() => api(`/dosen/courses/${aid}/grades`), [aid]);
  const [draft, setDraft] = useState({});
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setDraft({}); }, [data]);

  const letterOf = (r) => (r.enrollment_id in draft ? draft[r.enrollment_id] : r.letter ?? "");
  const dirty = Object.keys(draft).length > 0;
  const run = async (fn) => {
    setMsg(null); setBusy(true);
    try { setMsg(await fn()); reload(); } catch (e) { setMsg({ ok: false, t: e.message }); }
    setBusy(false);
  };
  const result = (r, extra = "") => ({ ok: !r.errors?.length, t: `${extra}${r.saved ?? 0} nilai tersimpan sebagai draf.` + (r.errors?.length ? ` Masalah: ${r.errors.join("; ")}` : "") });
  const save = () => run(async () => {
    const items = Object.entries(draft).map(([id, letter]) => ({ enrollment_id: Number(id), letter: letter || null }));
    return result(await api(`/dosen/courses/${aid}/grades`, { method: "PUT", body: { items } }));
  });
  const importCsv = (file) => run(async () => result(await api(`/dosen/courses/${aid}/grades/import`, { method: "POST", file }), "Impor CSV: "));
  const finalize = () => {
    if (!confirm("Tandai semua nilai kelas ini sebagai FINAL? Setelah final, nilai terkunci dan hanya Admin yang bisa mengubahnya.")) return;
    run(async () => {
      const r = await api(`/dosen/courses/${aid}/finalize`, { method: "POST" });
      return { ok: true, t: `${r.finalized} nilai difinalkan. IP dihitung untuk ${r.records_computed ?? 0} mahasiswa yang seluruh mata kuliahnya sudah final.` };
    });
  };
  if (err) return <Err msg={err} />;
  if (!data) return <p>Memuat...</p>;
  const allFinal = data.rows.length > 0 && data.rows.every((r) => r.status === "final");
  return (
    <>
      <Head title={`${data.course.code} - ${data.course.name}`} sub={`Semester ${data.semester} · ${data.course.credits} SKS`}>
        <label className="btn secondary">Impor CSV<input type="file" accept=".csv" hidden onChange={(e) => e.target.files[0] && importCsv(e.target.files[0])} /></label>
        <button className="btn secondary" disabled={!dirty || busy} onClick={save}>Simpan draf</button>
        <button className="btn" disabled={busy || dirty || allFinal} onClick={finalize}>Tandai final</button>
      </Head>
      <p className="lbl">CSV: kolom student_number dan letter. Simpan draf dulu sebelum menandai final.</p>
      {msg && <div className={msg.ok ? "ok" : "err"}>{msg.t}</div>}
      <div className="card">
        <Table rows={data.rows} empty="Belum ada mahasiswa terdaftar (KRS) di kelas ini." cols={[
          { label: "ID", key: "student_number" }, { label: "Mahasiswa", render: (r) => <b>{r.name}</b> },
          { label: "Nilai", render: (r) => (
            <select style={{ width: 100 }} disabled={r.status === "final"} value={letterOf(r)}
              onChange={(e) => setDraft({ ...draft, [r.enrollment_id]: e.target.value })}>
              <option value="">-</option>
              {meta.data?.letters.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>) },
          { label: "Status", render: (r) => <span className={`badge ${r.status === "final" ? "g" : r.status === "draft" ? "i" : "a"}`}>{r.status}</span> },
        ]} />
      </div>
    </>
  );
}

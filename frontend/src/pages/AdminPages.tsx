import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  Activity, BookOpen, GraduationCap, Plus, TrendingUp, Users,
} from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "../services/apiRequest";
import {
  ConfirmDialog, DataTable, EmptyState, FileDropzone, Skeleton, StatCard,
  InfoTooltip, Stepper, Toast, type DataColumn,
} from "../components/SharedUI";

type DashboardData = {
  total_mahasiswa: number;
  total_dosen: number;
  prediksi_bulan_ini: number;
  model_metrics: { mae: number; rmse: number; r2: number };
  kategori: Record<string, number>;
  angkatan: Record<string, number>;
  aktivitas: { hasil: string; student_id: string; created_at: string }[];
};
type Student = {
  id: string;
  kode_anonim: string;
  prodi: string;
  angkatan: number;
  dosen_wali_id: string | null;
  profile_id: string | null;
};
type Account = { id: string; nama: string; role: "admin" | "dosen" | "mahasiswa"; email: string | null };
type Validation = {
  valid: boolean;
  total_baris: number;
  errors: { baris: number | number[]; pesan: string }[];
  preview: Record<string, string>[];
};

const COLORS = ["#10b981", "#f59e0b", "#f97316"];
const UPLOAD_TEMPLATE_HEADER = "student_id,semester,ips,ipk,sks,kehadiran,age,admission_grade,previous_qualification_grade,gpa_semester_1,attendance_rate,assignments_submitted_rate,library_visits_per_month,lms_logins_per_week,weekly_work_hours,missed_deadlines,commute_time_mins,sleep_hours,course_type,study_mode";
const UPLOAD_TEMPLATE_EXAMPLE = "00000000-0000-4000-8000-000000000001,1,3.25,3.2,20,95,20,150,150,3.2,95,90,4,8,5,1,30,7,STEM,Full-time";

export function AdminDashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: () => apiRequest<DashboardData>("/dashboard/admin"),
  });
  if (isLoading) return <Skeleton rows={5} />;
  if (error || !data) return <RetryPanel onRetry={() => void refetch()} />;
  const categories = ["Baik", "Cukup", "Perlu Perhatian"].map((name, index) => ({
    name,
    value: data.kategori[name] ?? 0,
    color: COLORS[index],
  }));
  const cohorts = Object.entries(data.angkatan).map(([angkatan, jumlah]) => ({ angkatan, jumlah }));
  return (
    <>
      <section className="welcome-panel">
        <div><p className="eyebrow">RUANG ADMIN</p><h2>Ringkasan perkembangan kampus</h2><p>Pantau data mahasiswa, aktivitas prediksi, dan pembaruan model.</p></div>
        <GraduationCap className="welcome-symbol" aria-hidden="true" />
      </section>
      <section className="stats-grid">
        <StatCard icon={<Users />} label="Total mahasiswa" value={data.total_mahasiswa} />
        <StatCard icon={<GraduationCap />} label="Total dosen" value={data.total_dosen} />
        <StatCard icon={<Activity />} label="Prediksi bulan ini" value={data.prediksi_bulan_ini} />
        <StatCard icon={<TrendingUp />} label="MAE model" value={data.model_metrics.mae.toFixed(3)} delta={`R² ${data.model_metrics.r2.toFixed(3)}`} />
      </section>
      <section className="chart-grid">
        <article className="content-card">
          <div className="section-heading"><div><h2>Hasil prediksi</h2><p>Sebaran kategori dari catatan prediksi yang tersimpan.</p></div></div>
          {categories.every((item) => item.value === 0) ? <EmptyState title="Belum ada prediksi" text="Hasil kategori akan terlihat setelah prediksi tersimpan." /> : (
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart><Pie data={categories} dataKey="value" nameKey="name" innerRadius={62} outerRadius={96} paddingAngle={4} label>{categories.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip /></PieChart>
              </ResponsiveContainer>
              <div className="chart-legend">{categories.map((item) => <span key={item.name}><i style={{ background: item.color }} />{item.name}: {item.value}</span>)}</div>
            </div>
          )}
        </article>
        <article className="content-card">
          <div className="section-heading"><div><h2>Mahasiswa per angkatan</h2><p>Jumlah data mahasiswa pada tiap angkatan.</p></div></div>
          {cohorts.length ? (
            <div className="chart-box"><ResponsiveContainer width="100%" height={280}><BarChart data={cohorts}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="angkatan" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="jumlah" name="Mahasiswa" fill="#4f46e5" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></div>
          ) : <EmptyState title="Belum ada data angkatan" text="Data akan muncul setelah mahasiswa terdaftar." />}
        </article>
      </section>
      <section className="content-card">
        <div className="section-heading"><div><h2>Aktivitas terbaru</h2><p>Ringkasan hasil prediksi terakhir tanpa menampilkan data pribadi.</p></div></div>
        {data.aktivitas.length ? <DataTable
          rows={data.aktivitas}
          rowId={(row) => `${row.student_id}-${row.created_at}`}
          columns={[
            { key: "created_at", label: "Waktu", value: (row) => new Date(row.created_at).toLocaleString("id-ID") },
            { key: "hasil", label: "Kategori", value: (row) => row.hasil },
          ]}
        /> : <EmptyState title="Belum ada aktivitas" text="Aktivitas akan muncul setelah prediksi tersimpan." />}
      </section>
    </>
  );
}

export function StudentManagement() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Student | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Student | null>(null);
  const [toast, setToast] = useState("");
  const [form, setForm] = useState({ kode_anonim: "", prodi: "", angkatan: "2026", dosen_wali_id: "", profile_id: "" });
  const students = useQuery({ queryKey: ["students"], queryFn: async () => (await apiRequest<{ students: Student[] }>("/students")).students });
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: async () => (await apiRequest<{ accounts: Account[] }>("/admin/accounts")).accounts });
  const save = useMutation({
    mutationFn: async () => {
      const body = {
        kode_anonim: form.kode_anonim.trim(),
        prodi: form.prodi.trim(),
        angkatan: Number(form.angkatan),
        dosen_wali_id: form.dosen_wali_id || null,
        profile_id: form.profile_id || null,
      };
      return editing
        ? apiRequest(`/admin/students/${editing.id}`, { method: "PATCH", body: JSON.stringify(body) })
        : apiRequest("/admin/students", { method: "POST", body: JSON.stringify(body) });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["students"] });
      setShowForm(false);
      setEditing(null);
      setToast("Data mahasiswa berhasil disimpan.");
    },
    onError: (error) => setToast(error.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => apiRequest(`/admin/students/${id}`, { method: "DELETE" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["students"] });
      setDeleteTarget(null);
      setToast("Data mahasiswa berhasil dihapus.");
    },
    onError: (error) => setToast(error.message),
  });
  const lecturerOptions = useMemo(() => accounts.data?.filter((item) => item.role === "dosen") ?? [], [accounts.data]);
  const studentAccounts = useMemo(() => accounts.data?.filter((item) => item.role === "mahasiswa") ?? [], [accounts.data]);

  function openForm(student?: Student) {
    setEditing(student ?? null);
    setForm(student ? {
      kode_anonim: student.kode_anonim,
      prodi: student.prodi,
      angkatan: String(student.angkatan),
      dosen_wali_id: student.dosen_wali_id ?? "",
      profile_id: student.profile_id ?? "",
    } : { kode_anonim: "", prodi: "", angkatan: "2026", dosen_wali_id: "", profile_id: "" });
    setShowForm(true);
  }
  const columns: DataColumn<Student>[] = [
    { key: "kode_anonim", label: "Kode", value: (row) => row.kode_anonim },
    { key: "prodi", label: "Program studi", value: (row) => row.prodi },
    { key: "angkatan", label: "Angkatan", value: (row) => row.angkatan },
    { key: "dosen", label: "Dosen wali", value: (row) => accounts.data?.find((account) => account.id === row.dosen_wali_id)?.nama ?? "Belum ditetapkan" },
    { key: "aksi", label: "Tindakan", value: () => "", render: (row) => <div className="row-actions"><button className="text-button" onClick={(event) => { event.stopPropagation(); openForm(row); }}>Ubah</button><button className="text-button danger-text" onClick={(event) => { event.stopPropagation(); setDeleteTarget(row); }}>Hapus</button></div> },
  ];

  return (
    <>
      <PageIntro eyebrow="PENGELOLAAN DATA" title="Mahasiswa" subtitle="Kelola data mahasiswa, akun, dan dosen wali." action={<button className="primary-button" onClick={() => openForm()}><Plus size={18} />Tambah mahasiswa</button>} />
      {students.isLoading ? <Skeleton /> : students.error ? <RetryPanel onRetry={() => void students.refetch()} /> : (
        <section className="content-card">
          <DataTable rows={students.data ?? []} columns={columns} rowId={(row) => row.id} emptyTitle="Belum ada mahasiswa" emptyText="Tambahkan mahasiswa untuk mulai mengelola data." />
        </section>
      )}
      {showForm && <div className="dialog-backdrop"><section className="confirm-dialog form-dialog" role="dialog" aria-modal="true" aria-labelledby="student-form-title"><h2 id="student-form-title">{editing ? "Ubah mahasiswa" : "Tambah mahasiswa"}</h2><form onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
        <label className="field"><span>Kode anonim</span><input required value={form.kode_anonim} onChange={(event) => setForm({ ...form, kode_anonim: event.target.value })} /></label>
        <label className="field"><span>Program studi</span><input required value={form.prodi} onChange={(event) => setForm({ ...form, prodi: event.target.value })} /></label>
        <label className="field"><span>Angkatan</span><input type="number" min="2020" max="2100" required value={form.angkatan} onChange={(event) => setForm({ ...form, angkatan: event.target.value })} /></label>
        <label className="field"><span>Dosen wali</span><select value={form.dosen_wali_id} onChange={(event) => setForm({ ...form, dosen_wali_id: event.target.value })}><option value="">Belum ditetapkan</option>{lecturerOptions.map((item) => <option key={item.id} value={item.id}>{item.nama}</option>)}</select></label>
        <label className="field"><span>Akun mahasiswa</span><select value={form.profile_id} onChange={(event) => setForm({ ...form, profile_id: event.target.value })}><option value="">Belum terhubung</option>{studentAccounts.map((item) => <option key={item.id} value={item.id}>{item.nama} · {item.email}</option>)}</select></label>
        <div className="dialog-actions"><button type="button" className="secondary-button" onClick={() => setShowForm(false)}>Batal</button><button className="primary-button" disabled={save.isPending}>{save.isPending ? "Menyimpan..." : "Simpan"}</button></div>
      </form></section></div>}
      {deleteTarget && <ConfirmDialog title="Hapus data mahasiswa?" message={`Data ${deleteTarget.kode_anonim} dan riwayat terkait akan dihapus.`} onCancel={() => setDeleteTarget(null)} onConfirm={() => remove.mutate(deleteTarget.id)} />}
      <Toast message={toast} kind={toast.includes("berhasil") ? "success" : "error"} onClose={() => setToast("")} />
    </>
  );
}

export function AccountManagement() {
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<Account | null>(null);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [editForm, setEditForm] = useState<{ nama: string; role: Account["role"] }>({ nama: "", role: "mahasiswa" });
  const [toast, setToast] = useState("");
  const [form, setForm] = useState({ nama: "", email: "", role: "mahasiswa", temporary_password: "" });
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: async () => (await apiRequest<{ accounts: Account[] }>("/admin/accounts")).accounts });
  const create = useMutation({
    mutationFn: () => apiRequest("/admin/accounts", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setForm({ nama: "", email: "", role: "mahasiswa", temporary_password: "" });
      setToast("Akun berhasil dibuat.");
    },
    onError: (error) => setToast(error.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => apiRequest(`/admin/accounts/${id}`, { method: "DELETE" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setDeleteTarget(null);
      setToast("Akun berhasil dihapus.");
    },
    onError: (error) => setToast(error.message),
  });
  const update = useMutation({
    mutationFn: ({ account, nama, role }: { account: Account; nama: string; role: Account["role"] }) =>
      apiRequest(`/admin/accounts/${account.id}`, { method: "PATCH", body: JSON.stringify({ nama, role }) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setEditingAccount(null);
      setToast("Perubahan akun tersimpan.");
    },
    onError: (error) => setToast(error.message),
  });
  return (
    <>
      <PageIntro eyebrow="PENGELOLAAN AKSES" title="Akun pengguna" subtitle="Buat akun dari admin. Pendaftaran publik tidak tersedia." />
      <section className="content-card">
        <div className="section-heading"><div><h2>Buat akun baru</h2><p>Kata sandi sementara minimal 12 karakter.</p></div></div>
        <form className="form-grid" onSubmit={(event: FormEvent) => { event.preventDefault(); create.mutate(); }}>
          <label className="field"><span>Nama</span><input required maxLength={120} value={form.nama} onChange={(event) => setForm({ ...form, nama: event.target.value })} /></label>
          <label className="field"><span>Email</span><input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
          <label className="field"><span>Peran</span><select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}><option value="admin">Admin</option><option value="dosen">Dosen</option><option value="mahasiswa">Mahasiswa</option></select></label>
          <label className="field"><span>Kata sandi sementara</span><input type="password" autoComplete="new-password" minLength={12} required value={form.temporary_password} onChange={(event) => setForm({ ...form, temporary_password: event.target.value })} /></label>
          <button className="primary-button" disabled={create.isPending}>{create.isPending ? "Membuat akun..." : "Buat akun"}</button>
        </form>
      </section>
      <section className="content-card">
        <div className="section-heading"><div><h2>Daftar akun</h2><p>Ubah nama/peran atau hapus akun yang sudah tidak digunakan.</p></div></div>
        {accounts.isLoading ? <Skeleton /> : accounts.error ? <RetryPanel onRetry={() => void accounts.refetch()} /> : <DataTable
          rows={accounts.data ?? []}
          rowId={(row) => row.id}
          columns={[
            { key: "nama", label: "Nama", value: (row) => row.nama },
            { key: "email", label: "Email", value: (row) => row.email ?? "—" },
            { key: "role", label: "Peran", value: (row) => row.role },
            { key: "aksi", label: "Tindakan", value: () => "", render: (row) => <div className="row-actions"><button className="text-button" onClick={() => { setEditingAccount(row); setEditForm({ nama: row.nama, role: row.role }); }}>Ubah</button><button className="text-button danger-text" onClick={() => setDeleteTarget(row)}>Hapus</button></div> },
          ]}
          emptyTitle="Belum ada akun"
          emptyText="Akun baru akan ditampilkan di sini."
        />}
      </section>
      {editingAccount && <div className="dialog-backdrop"><section className="confirm-dialog form-dialog" role="dialog" aria-modal="true" aria-labelledby="account-form-title"><h2 id="account-form-title">Ubah akun pengguna</h2><form onSubmit={(event) => { event.preventDefault(); update.mutate({ account: editingAccount, ...editForm }); }}><label className="field"><span>Nama</span><input required maxLength={120} value={editForm.nama} onChange={(event) => setEditForm({ ...editForm, nama: event.target.value })} /></label><label className="field"><span>Peran</span><select value={editForm.role} onChange={(event) => setEditForm({ ...editForm, role: event.target.value as Account["role"] })}><option value="admin">Admin</option><option value="dosen">Dosen</option><option value="mahasiswa">Mahasiswa</option></select></label><div className="dialog-actions"><button type="button" className="secondary-button" onClick={() => setEditingAccount(null)}>Batal</button><button className="primary-button" disabled={update.isPending}>{update.isPending ? "Menyimpan..." : "Simpan"}</button></div></form></section></div>}
      {deleteTarget && <ConfirmDialog title="Hapus akun pengguna?" message={`Akun ${deleteTarget.nama} akan dihapus dan sesi terkait dicabut.`} onCancel={() => setDeleteTarget(null)} onConfirm={() => remove.mutate(deleteTarget.id)} />}
      <Toast message={toast} kind={toast.includes("berhasil") || toast.includes("tersimpan") ? "success" : "error"} onClose={() => setToast("")} />
    </>
  );
}

export function UploadData() {
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<Validation | null>(null);
  const [step, setStep] = useState(0);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const [templateVisible, setTemplateVisible] = useState(false);
  const queryClient = useQueryClient();
  const upload = useMutation({
    mutationFn: async (action: "validate" | "commit") => {
      if (!file) throw new Error("Pilih file CSV terlebih dahulu.");
      const requiredColumns = [
        "student_id", "semester", "ips", "ipk", "sks", "kehadiran",
        "age", "admission_grade", "previous_qualification_grade",
        "gpa_semester_1", "attendance_rate", "assignments_submitted_rate",
        "library_visits_per_month", "lms_logins_per_week", "weekly_work_hours",
        "missed_deadlines", "commute_time_mins", "sleep_hours", "course_type",
        "study_mode",
      ];
      const header = (await file.slice(0, 8192).text())
        .split(/\r?\n/, 1)[0]
        .replace(/^\uFEFF/, "")
        .split(",")
        .map((column) => column.trim());
      const missingColumns = requiredColumns.filter((column) => !header.includes(column));
      if (missingColumns.length) {
        throw new Error(
          "File ini bukan CSV unggah akademik. Pilih upload_admin_test.csv "
          + "atau CSV yang dibuat dari template web, bukan students.csv.",
        );
      }
      const formData = new FormData();
      formData.append("file", file);
      return apiRequest<Validation & { disimpan?: number; pesan?: string }>(`/upload/${action}`, { method: "POST", body: formData });
    },
    onSuccess: async (result, action) => {
      if (action === "validate") {
        setValidation(result);
        setStep(2);
        setMessage(result.valid ? `${result.total_baris} baris lolos pemeriksaan.` : "Periksa daftar kesalahan sebelum menyimpan.");
        setMessageIsError(!result.valid);
      } else {
        setStep(3);
        setMessage(`${result.disimpan ?? 0} baris tersimpan beserta prediksi.`);
        setMessageIsError(false);
        setFile(null);
        setValidation(null);
        await queryClient.invalidateQueries();
      }
    },
    onError: (error) => {
      setMessageIsError(true);
      setMessage(
        error instanceof TypeError || /networkerror|failed to fetch/i.test(error.message)
          ? "Tidak tersambung ke backend di http://127.0.0.1:8000. Jalankan backend, lalu coba lagi."
          : error.message,
      );
    },
  });
  function chooseFile(next: File) {
    setFile(next);
    setValidation(null);
    setStep(1);
    setMessage("");
    setMessageIsError(false);
  }
  function downloadTemplate() {
    const url = URL.createObjectURL(new Blob([`${UPLOAD_TEMPLATE_HEADER}\n${UPLOAD_TEMPLATE_EXAMPLE}\n`], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "template-data-model.csv";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <PageIntro eyebrow="UNGGAH DATA" title="Impor data akademik" subtitle="Periksa format dan nilai sebelum menyimpan serta membuat perkiraan." />
      <section className="content-card upload-card">
        <Stepper steps={["Unduh template", "Pilih file", "Periksa data", "Simpan & prediksi"]} current={step} />
        <div className="upload-step-content">
          {step === 0 && <>
            <p>Lihat format kolom di sini. Unduhan hanya diperlukan jika Anda ingin mengedit template sebagai file.</p>
            <div className="row-actions">
              <button className="primary-button" type="button" onClick={() => setTemplateVisible((visible) => !visible)}>{templateVisible ? "Tutup template" : "Lihat template"}</button>
              <button className="secondary-button" type="button" onClick={downloadTemplate}>Unduh salinan CSV</button>
            </div>
            {templateVisible && <div className="template-preview">
              <strong>Header dan satu baris contoh</strong>
              <pre>{UPLOAD_TEMPLATE_HEADER}{"\n"}{UPLOAD_TEMPLATE_EXAMPLE}</pre>
              <p>Ganti UUID contoh dengan ID mahasiswa terdaftar. Baris contoh ini hanya untuk melihat format, bukan data yang siap disimpan.</p>
              <button className="primary-button" type="button" onClick={() => { setStep(1); setMessage("Pilih CSV yang sudah diisi untuk melanjutkan."); setMessageIsError(false); }}>Lanjut pilih file</button>
            </div>}
          </>}
          {step > 0 && <>
            <FileDropzone onFile={chooseFile} fileName={file?.name} />
            {file && <div className="row-actions"><button className="secondary-button" disabled={upload.isPending} onClick={() => upload.mutate("validate")}>{upload.isPending ? "Memeriksa..." : "Periksa pratinjau"}</button><button className="text-button" onClick={() => { setStep(0); setFile(null); setValidation(null); setMessage(""); }}>Mulai ulang</button></div>}
          </>}
          {validation && <div className="validation-results">
            {validation.errors.length > 0 ? <div className="upload-errors"><strong>Ada yang perlu diperbaiki</strong><ul>{validation.errors.map((item, index) => <li key={`${index}-${item.pesan}`}>Baris {Array.isArray(item.baris) ? item.baris.join(", ") : item.baris}: {item.pesan}</li>)}</ul></div> : <p className="success-message">{validation.total_baris} baris siap disimpan.</p>}
            {validation.preview.length > 0 && <div className="table-wrap preview-table"><table><thead><tr>{Object.keys(validation.preview[0]).map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{validation.preview.map((row, index) => <tr key={index}>{Object.values(row).map((value, cell) => <td key={cell}>{value}</td>)}</tr>)}</tbody></table></div>}
            {validation.valid && <button className="primary-button" disabled={upload.isPending} onClick={() => upload.mutate("commit")}>{upload.isPending ? "Menyimpan..." : "Simpan dan buat prediksi"}</button>}
          </div>}
          {message && <p role={messageIsError ? "alert" : "status"} className={messageIsError ? "error-message" : "success-message"}>{message}</p>}
        </div>
      </section>
    </>
  );
}

export function ModelPage() {
  const query = useQuery({
    queryKey: ["model-info"],
    queryFn: () => apiRequest<{ active: { versi: string; algoritma: string; metrik: { mae: number; rmse: number; r2: number }; features: { faktor: string; arah: string; coefficient?: number }[] }; versions: { versi: string; algoritma: string; metrik: Record<string, number>; tanggal: string }[] }>("/model/info"),
  });
  if (query.isLoading) return <Skeleton rows={4} />;
  if (query.error || !query.data) return <RetryPanel onRetry={() => void query.refetch()} />;
  const { active, versions } = query.data;
  return (
    <>
      <PageIntro eyebrow="PERFORMA MODEL" title="Model prediksi" subtitle="Metrik dihitung dari data uji yang tidak digunakan saat pelatihan." />
      <section className="content-card model-active">
        <div><span className="active-tag">Versi aktif</span><h2>{active.algoritma}</h2><p>{active.versi} · dataset Kaggle · target nilai semester berikutnya</p></div>
        <div className="stats-grid model-metrics"><StatCard icon={<TrendingUp />} label={<>MAE · selisih rata-rata <InfoTooltip label="MAE" text="Rata-rata selisih mutlak antara perkiraan dan nilai pada data uji." /></>} value={active.metrik.mae.toFixed(3)} /><StatCard icon={<Activity />} label="RMSE" value={active.metrik.rmse.toFixed(3)} /><StatCard icon={<BookOpen />} label={<>R² <InfoTooltip label="R²" text="Menunjukkan seberapa baik model menjelaskan variasi nilai pada data uji." /></>} value={active.metrik.r2.toFixed(3)} /></div>
      </section>
      <section className="content-card">
        <div className="section-heading"><div><h2>Faktor yang paling berpengaruh</h2><p>Koefisien terstandar; arah menunjukkan hubungannya dengan perkiraan. <InfoTooltip label="Koefisien terstandar" text="Angka ini membandingkan pengaruh relatif faktor setelah skala datanya disetarakan." /></p></div></div>
        <div className="chart-box horizontal-chart"><ResponsiveContainer width="100%" height={Math.max(300, active.features.length * 38)}><BarChart data={active.features} layout="vertical" margin={{ left: 36, right: 24 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" /><YAxis type="category" dataKey="faktor" width={180} tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey="coefficient" name="Koefisien terstandar" fill="#14b8a6" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer></div>
      </section>
      <section className="content-card"><div className="section-heading"><div><h2>Riwayat versi</h2><p>Versi yang sudah dicatat pada basis data.</p></div></div>{versions.length ? <DataTable rows={versions} rowId={(row) => row.versi} columns={[{ key: "versi", label: "Versi", value: (row) => row.versi }, { key: "algoritma", label: "Algoritma", value: (row) => row.algoritma }, { key: "tanggal", label: "Tanggal", value: (row) => row.tanggal }, { key: "metrik", label: "Metrik", value: (row) => Object.entries(row.metrik).map(([key, value]) => `${key}: ${Number(value).toFixed(3)}`).join(" · ") }]} /> : <EmptyState title="Riwayat belum tersedia" text="Versi aktif tetap tersedia. Seed histori dapat dimasukkan setelah ditinjau." />}</section>
    </>
  );
}

export function AdminPredictions() {
  const [page, setPage] = useState(0);
  const pageSize = 1000;
  const query = useQuery({
    queryKey: ["admin-predictions", page],
    queryFn: () => apiRequest<{
      predictions: {
        id: string;
        kode_anonim: string;
        semester_target: number;
        hasil: string;
        nilai_prediksi: number;
        batas_bawah: number;
        batas_atas: number;
        model_version: string;
        created_at: string;
      }[];
      total: number;
      limit: number;
      offset: number;
    }>(`/admin/predictions?limit=${pageSize}&offset=${page * pageSize}`),
  });
  if (query.isLoading) return <Skeleton rows={5} />;
  if (query.error || !query.data) return <RetryPanel onRetry={() => void query.refetch()} />;
  return (
    <>
      <PageIntro eyebrow="RIWAYAT PREDIKSI" title="Semua prediksi" subtitle="Tinjau hasil, rentang nilai, mahasiswa, dan versi model yang digunakan." />
      <section className="content-card">
        {query.data.predictions.length ? <DataTable
          rows={query.data.predictions}
          rowId={(row) => row.id}
          columns={[
            { key: "kode", label: "Mahasiswa", value: (row) => row.kode_anonim },
            { key: "semester", label: "Semester target", value: (row) => row.semester_target },
            { key: "nilai", label: "Perkiraan nilai", value: (row) => Number(row.nilai_prediksi).toFixed(2) },
            { key: "rentang", label: "Rentang", value: (row) => `${Number(row.batas_bawah).toFixed(2)}–${Number(row.batas_atas).toFixed(2)}` },
            { key: "kategori", label: "Kondisi", value: (row) => row.hasil },
            { key: "model", label: "Versi model", value: (row) => row.model_version },
            { key: "tanggal", label: "Waktu", value: (row) => new Date(row.created_at).toLocaleString("id-ID") },
          ]}
        /> : <EmptyState title="Belum ada prediksi" text="Hasil prediksi yang tersimpan akan tampil di sini." />}
        <div className="table-pagination">
          <span>{query.data.total} prediksi tersimpan</span>
          <div className="row-actions">
            <button type="button" className="secondary-button" disabled={page === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>Sebelumnya</button>
            <button type="button" className="secondary-button" disabled={(page + 1) * pageSize >= query.data.total} onClick={() => setPage((current) => current + 1)}>Berikutnya</button>
          </div>
        </div>
      </section>
    </>
  );
}

export function MoreAdminPages() {
  return <section className="content-card"><PageIntro eyebrow="PENGATURAN" title="Data dan model" subtitle="Pilih fitur pengelolaan yang ingin dibuka." /><div className="quick-links"><Link className="secondary-button" to="/admin/upload">Unggah data CSV</Link><Link className="secondary-button" to="/admin/prediksi">Riwayat prediksi</Link><Link className="secondary-button" to="/admin/model">Metrik dan versi model</Link></div></section>;
}

export function PageIntro({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: React.ReactNode }) {
  return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{subtitle}</p></div>{action}</header>;
}

export function RetryPanel({ onRetry }: { onRetry: () => void }) {
  return <section className="content-card retry-panel"><p role="alert">Data belum dapat dimuat. Periksa koneksi, lalu coba lagi.</p><button className="secondary-button" onClick={onRetry}>Coba lagi</button></section>;
}

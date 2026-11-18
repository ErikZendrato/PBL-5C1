import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import {
  Activity, ArrowUpRight, GraduationCap, Moon, Sun, Users,
} from "lucide-react";
import { apiRequest } from "../services/apiRequest";
import { AdminDashboard, AccountManagement, AdminPredictions, ModelPage, MoreAdminPages, StudentManagement, UploadData } from "./AdminPages";
import { AdviseeDetail, AdviseeList, LecturerDashboard, StudentHome } from "./AdvisorPages";
import { useAuth } from "../auth/AuthProvider";
import {
  EmptyState, PredictionCard, Skeleton, StatCard, Toast,
  type Status,
} from "../components/SharedUI";

type Student = { id: string; kode_anonim: string; prodi: string; angkatan: number };
type ModelFeatures = {
  age: number;
  admission_grade: number;
  previous_qualification_grade: number;
  gpa_semester_1: number;
  attendance_rate: number;
  assignments_submitted_rate: number;
  library_visits_per_month: number;
  lms_logins_per_week: number;
  weekly_work_hours: number;
  missed_deadlines: number;
  commute_time_mins: number;
  sleep_hours: number;
  course_type: string;
  study_mode: string;
};
type PredictionResult = {
  nilai_prediksi: number;
  batas_bawah: number;
  batas_atas: number;
  kategori: Status;
  faktor: { faktor: string; arah: "naik" | "turun"; penjelasan: string }[];
  penjelasan: string;
};
type Field = { key: keyof ModelFeatures; label: string; min: number; max: number; step: number };

const FIELDS: Field[] = [
  { key: "age", label: "Usia", min: 15, max: 30, step: 1 },
  { key: "admission_grade", label: "Nilai saat masuk", min: 5.5, max: 200, step: 0.1 },
  { key: "previous_qualification_grade", label: "Nilai pendidikan sebelumnya", min: 30.2, max: 200, step: 0.1 },
  { key: "gpa_semester_1", label: "Nilai semester sebelumnya", min: 0, max: 4, step: 0.01 },
  { key: "attendance_rate", label: "Kehadiran (%)", min: 0, max: 100, step: 0.1 },
  { key: "assignments_submitted_rate", label: "Tugas dikumpulkan (%)", min: 0, max: 100, step: 0.1 },
  { key: "library_visits_per_month", label: "Kunjungan perpustakaan/bulan", min: 0, max: 30, step: 1 },
  { key: "lms_logins_per_week", label: "Aktivitas belajar daring/minggu", min: 0, max: 29.6, step: 0.1 },
  { key: "weekly_work_hours", label: "Jam kerja/minggu", min: 0, max: 40, step: 1 },
  { key: "missed_deadlines", label: "Tugas terlambat", min: 0, max: 20, step: 1 },
  { key: "commute_time_mins", label: "Waktu perjalanan (menit)", min: 0, max: 120, step: 1 },
  { key: "sleep_hours", label: "Jam tidur", min: 4, max: 10, step: 0.1 },
];
const INITIAL_FEATURES: ModelFeatures = {
  age: 20,
  admission_grade: 150,
  previous_qualification_grade: 150,
  gpa_semester_1: 3.2,
  attendance_rate: 90,
  assignments_submitted_rate: 90,
  library_visits_per_month: 4,
  lms_logins_per_week: 8,
  weekly_work_hours: 5,
  missed_deadlines: 1,
  commute_time_mins: 30,
  sleep_hours: 7,
  course_type: "STEM",
  study_mode: "Full-time",
};
const OPTIONS = {
  course_type: ["Arts & Humanities", "Business", "Health Sciences", "Law & Social Sciences", "STEM"],
  study_mode: ["Full-time", "Online", "Part-time"],
};

export default function RolePage({
  role,
  section = "",
  detailId,
}: {
  role: "admin" | "dosen" | "mahasiswa";
  section?: string;
  detailId?: string;
}) {
  if (role === "admin") {
    if (!section) return <AdminDashboard />;
    if (section === "mahasiswa") return <StudentManagement />;
    if (section === "akun") return <AccountManagement />;
    if (section === "upload") return <UploadData />;
    if (section === "prediksi") return <AdminPredictions />;
    if (section === "model") return <ModelPage />;
    if (section === "lainnya") return <MoreAdminPages />;
    return <Navigate to="/admin" replace />;
  }
  if (role === "dosen") {
    if (!section) return <LecturerDashboard />;
    if (section === "mahasiswa" && detailId) return <AdviseeDetail studentId={detailId} />;
    if (section === "mahasiswa") return <AdviseeList />;
    if (section === "prediksi") return <ManualPrediction />;
    return <Navigate to="/dosen" replace />;
  }
  return section ? <Navigate to="/mahasiswa" replace /> : <StudentHome />;
}

export function ManualPrediction() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [values, setValues] = useState(INITIAL_FEATURES);
  const [studentId, setStudentId] = useState("");
  const [semesterTarget, setSemesterTarget] = useState("2");
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [toast, setToast] = useState("");
  const students = useQuery({
    queryKey: ["students"],
    queryFn: async () => (await apiRequest<{ students: Student[] }>("/students")).students,
  });
  const predict = useMutation({
    mutationFn: () => apiRequest<PredictionResult>("/predict", {
      method: "POST",
      body: JSON.stringify({
        ...values,
        student_id: studentId || undefined,
        semester_target: studentId ? Number(semesterTarget) : undefined,
      }),
    }),
    onSuccess: async (prediction) => {
      setResult(prediction);
      setToast("Perkiraan berhasil dibuat.");
      await queryClient.invalidateQueries();
    },
    onError: (error) => setToast(error.message),
  });

  return (
    <>
      <header className="page-header"><div><p className="eyebrow">PREDIKSI MANUAL</p><h1>Perkiraan nilai</h1><p>Masukkan data yang tersedia. Hasil ditampilkan tanpa meninggalkan halaman.</p></div></header>
      <section className="content-card">
        <div className="prediction-layout">
          <form className="prediction-form" onSubmit={(event: FormEvent) => { event.preventDefault(); predict.mutate(); }}>
            {students.data?.length ? <label className="field"><span>Mahasiswa</span><select value={studentId} onChange={(event) => setStudentId(event.target.value)}><option value="">Prediksi tanpa menyimpan ke riwayat</option>{students.data.map((student) => <option key={student.id} value={student.id}>{student.kode_anonim} · {student.prodi}</option>)}</select></label> : null}
            {studentId && <label className="field"><span>Semester target</span><input type="number" min={1} max={14} required value={semesterTarget} onChange={(event) => setSemesterTarget(event.target.value)} /></label>}
            {FIELDS.map((field) => <label className="field" key={field.key}><span>{field.label}</span><input type="number" min={field.min} max={field.max} step={field.step} required value={values[field.key] as number} onChange={(event) => setValues((current) => ({ ...current, [field.key]: Number(event.target.value) }))} /></label>)}
            {(Object.keys(OPTIONS) as (keyof typeof OPTIONS)[]).map((key) => <label className="field" key={key}><span>{key === "course_type" ? "Jenis program studi" : "Mode kuliah"}</span><select value={values[key]} onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))}>{OPTIONS[key].map((option) => <option key={option}>{option}</option>)}</select></label>)}
            <button className="primary-button" disabled={predict.isPending}>{predict.isPending ? "Menghitung..." : "Lihat perkiraan"}</button>
          </form>
          <aside className="prediction-result" aria-live="polite">
            {students.isLoading ? <Skeleton rows={2} /> : null}
            {students.error && <p role="alert">Daftar mahasiswa tidak dapat dimuat. Prediksi tetap dapat dilakukan tanpa menyimpan riwayat.</p>}
            {result ? <><PredictionCard value={result.nilai_prediksi} lower={result.batas_bawah} upper={result.batas_atas} status={result.kategori} /><p>{result.penjelasan}</p><h3>Faktor yang berkaitan</h3><ul>{result.faktor.map((factor) => <li key={factor.faktor}><strong>{factor.faktor} · {factor.arah}</strong><p>{factor.penjelasan}</p></li>)}</ul></> : <EmptyState title="Hasil akan muncul di sini" text="Isi kolom yang tersedia, lalu pilih tombol lihat perkiraan." />}
          </aside>
        </div>
      </section>
      {user?.role === "admin" && <section className="content-card"><StatCard icon={<Activity />} label="Model aktif" value="Linear Regression" delta="Metrik tersedia di menu Model" /></section>}
      <Toast message={toast} kind={toast.includes("berhasil") ? "success" : "error"} onClose={() => setToast("")} />
    </>
  );
}

export function ThemeToggle() {
  const [dark, setDark] = useState(() => localStorage.getItem("theme") === "dark");
  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    localStorage.setItem("theme", next ? "dark" : "light");
  }
  return <button className="icon-button" type="button" onClick={toggle} aria-label={dark ? "Gunakan tema terang" : "Gunakan tema gelap"}>{dark ? <Sun size={20} /> : <Moon size={20} />}</button>;
}

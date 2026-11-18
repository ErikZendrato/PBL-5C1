import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, HeartHandshake, TrendingUp } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiRequest } from "../services/apiRequest";
import { useAuth } from "../auth/AuthProvider";
import {
  DataTable, EmptyState, InfoTooltip, PredictionCard, Skeleton, StatCard, StatusBadge, Toast,
  type DataColumn, type Status,
} from "../components/SharedUI";
import { PageIntro, RetryPanel } from "./AdminPages";

type Student = { id: string; kode_anonim: string; prodi: string; angkatan: number; dosen_wali_id: string | null; profile_id: string | null };
type Prediction = { id: string; student_id: string; semester_target: number; hasil: Status; nilai_prediksi: number; batas_bawah: number; batas_atas: number; faktor: { items?: Factor[] }; created_at: string };
type Factor = { faktor: string; arah: "naik" | "turun"; penjelasan: string };
type AcademicRecord = { id: string; semester: number; ips: number; ipk: number; kehadiran: number; gpa_semester_1?: number };
type FollowUp = { id: string; prediction_id: string; catatan: string; status: "baru" | "dalam_penanganan" | "selesai"; created_at: string };
type HistoryData = { student: Student; records: AcademicRecord[]; predictions: Prediction[]; follow_ups: FollowUp[] };

export function LecturerDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const query = useQuery({ queryKey: ["lecturer-dashboard"], queryFn: () => apiRequest<{ students: Student[]; predictions: Prediction[]; kategori: Record<string, number>; prioritas: Prediction[] }>("/dashboard/dosen") });
  if (query.isLoading) return <Skeleton rows={5} />;
  if (query.error || !query.data) return <RetryPanel onRetry={() => void query.refetch()} />;
  const { students, kategori, prioritas } = query.data;
  return (
    <>
      <section className="welcome-panel">
        <div><p className="eyebrow">RUANG DOSEN WALI</p><h2>Halo, {user?.nama ?? "Bapak/Ibu Dosen"}</h2><p>Pantau perkembangan mahasiswa bimbingan dan pilih langkah dukungan berikutnya.</p></div>
        <HeartHandshake className="welcome-symbol" aria-hidden="true" />
      </section>
      <section className="stats-grid three-stats">
        {(["Baik", "Cukup", "Perlu Perhatian"] as Status[]).map((status) => <StatCard key={status} icon={<TrendingUp />} label={status} value={kategori[status] ?? 0} />)}
      </section>
      <section className="content-card">
        <div className="section-heading"><div><h2>Perlu perhatian minggu ini</h2><p>Mahasiswa dengan perkiraan nilai terendah didahulukan untuk ditinjau.</p></div></div>
        {prioritas.length ? <DataTable
          rows={prioritas}
          rowId={(row) => row.id}
          columns={[
            { key: "student", label: "Mahasiswa", value: (row) => students.find((student) => student.id === row.student_id)?.kode_anonim ?? "Mahasiswa" },
            { key: "nilai", label: "Perkiraan nilai", value: (row) => Number(row.nilai_prediksi).toFixed(2) },
            { key: "hasil", label: "Kondisi", value: (row) => row.hasil, render: (row) => <StatusBadge status={row.hasil} /> },
            { key: "detail", label: "Tindakan", value: () => "", render: (row) => <button className="text-button" onClick={() => navigate(`/dosen/mahasiswa/${row.student_id}`)}>Lihat detail <ArrowRight size={16} /></button> },
          ]}
        /> : <EmptyState title="Belum ada yang perlu ditinjau" text="Mahasiswa dengan hasil yang perlu perhatian akan tampil di sini." />}
      </section>
      <AdviseeTable students={students} predictions={query.data.predictions} onOpen={(id) => navigate(`/dosen/mahasiswa/${id}`)} />
    </>
  );
}

export function AdviseeList() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["lecturer-dashboard"], queryFn: () => apiRequest<{ students: Student[]; predictions: Prediction[] }>("/dashboard/dosen") });
  if (query.isLoading) return <Skeleton />;
  if (query.error || !query.data) return <RetryPanel onRetry={() => void query.refetch()} />;
  return (
    <>
      <PageIntro eyebrow="DAFTAR BIMBINGAN" title="Mahasiswa bimbingan" subtitle="Daftar ini hanya memuat mahasiswa yang berada dalam bimbingan Anda." />
      <AdviseeTable students={query.data.students} predictions={query.data.predictions} onOpen={(id) => navigate(`/dosen/mahasiswa/${id}`)} />
    </>
  );
}

function AdviseeTable({ students, predictions, onOpen }: { students: Student[]; predictions: Prediction[]; onOpen: (id: string) => void }) {
  const [category, setCategory] = useState("");
  const latestByStudent = useMemo(() => {
    const result = new Map<string, Prediction>();
    for (const prediction of predictions) {
      if (!result.has(prediction.student_id) || prediction.semester_target > (result.get(prediction.student_id)?.semester_target ?? 0)) {
        result.set(prediction.student_id, prediction);
      }
    }
    return result;
  }, [predictions]);
  const rows = students.filter((student) => !category || latestByStudent.get(student.id)?.hasil === category);
  const columns: DataColumn<Student>[] = [
    { key: "kode", label: "Kode", value: (row) => row.kode_anonim },
    { key: "prodi", label: "Program studi", value: (row) => row.prodi },
    { key: "angkatan", label: "Angkatan", value: (row) => row.angkatan },
    { key: "status", label: "Kondisi", value: (row) => latestByStudent.get(row.id)?.hasil ?? "Belum ada", render: (row) => { const status = latestByStudent.get(row.id)?.hasil; return status ? <StatusBadge status={status} /> : "Belum ada prediksi"; } },
    { key: "aksi", label: "Detail", value: () => "", render: (row) => <button className="text-button" onClick={() => onOpen(row.id)}>Lihat detail <ArrowRight size={16} /></button> },
  ];
  return (
    <section className="content-card">
      <div className="section-heading"><div><h2>Daftar mahasiswa bimbingan</h2><p>Cari, urutkan, atau saring berdasarkan kondisi terkini.</p></div><label className="filter-field"><span>Kondisi</span><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">Semua</option><option>Baik</option><option>Cukup</option><option>Perlu Perhatian</option></select></label></div>
      <DataTable rows={rows} columns={columns} rowId={(row) => row.id} emptyTitle="Belum ada mahasiswa" emptyText="Daftar mahasiswa bimbingan akan tampil di sini." />
    </section>
  );
}

export function AdviseeDetail({ studentId }: { studentId?: string }) {
  const query = useQuery({
    queryKey: ["student-history", studentId],
    queryFn: () => apiRequest<HistoryData>(`/students/${studentId}/history`),
    enabled: Boolean(studentId),
  });
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [toast, setToast] = useState("");
  const latest = query.data?.predictions.at(-1);
  const saveNote = useMutation({
    mutationFn: () => {
      if (!latest) throw new Error("Buat prediksi terlebih dahulu sebelum menambah catatan.");
      return apiRequest("/follow-ups", { method: "POST", body: JSON.stringify({ prediction_id: latest.id, catatan: note, status: "baru" }) });
    },
    onSuccess: async () => {
      setNote("");
      setToast("Catatan berhasil disimpan.");
      await queryClient.invalidateQueries({ queryKey: ["student-history", studentId] });
    },
    onError: (error) => setToast(error.message),
  });
  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: FollowUp["status"] }) => apiRequest(`/follow-ups/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: async () => {
      setToast("Status catatan berhasil diperbarui.");
      await queryClient.invalidateQueries({ queryKey: ["student-history", studentId] });
    },
    onError: (error) => setToast(error.message),
  });
  if (!studentId) return <EmptyState title="Mahasiswa tidak dipilih" text="Pilih mahasiswa dari daftar bimbingan." />;
  if (query.isLoading) return <Skeleton rows={4} />;
  if (query.error || !query.data) return <RetryPanel onRetry={() => void query.refetch()} />;
  const { student, records, predictions, follow_ups: followUps } = query.data;
  const chartData = records.map((record) => ({ semester: `S${record.semester}`, ips: Number(record.ips), ipk: Number(record.ipk) }));
  const lastTwo = records.slice(-2);
  const trendSentence = lastTwo.length < 2
    ? "Catatan nilai akan membantu melihat perubahan dari waktu ke waktu."
    : Number(lastTwo[1].ips) > Number(lastTwo[0].ips)
      ? "IPS naik dalam dua semester terakhir."
      : Number(lastTwo[1].ips) < Number(lastTwo[0].ips)
        ? "IPS menurun dalam dua semester terakhir; mari cari dukungan yang sesuai."
        : "IPS relatif stabil dalam dua semester terakhir.";
  return (
    <>
      <PageIntro eyebrow="DETAIL MAHASISWA" title={student.kode_anonim} subtitle={`${student.prodi} · Angkatan ${student.angkatan}`} />
      {latest && <section className="detail-status"><StatusBadge status={latest.hasil} large /><span>Perkiraan untuk semester {latest.semester_target}</span></section>}
      <section className="content-card">
        <div className="section-heading"><div><h2>{trendSentence}</h2><p>Perkembangan IPS <InfoTooltip label="IPS" text="Indeks prestasi untuk satu semester." /> dan IPK <InfoTooltip label="IPK" text="Indeks prestasi kumulatif dari semester yang sudah ditempuh." /> berdasarkan catatan semester.</p></div></div>
        {chartData.length ? <div className="chart-box"><ResponsiveContainer width="100%" height={300}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="semester" /><YAxis domain={[0, 4]} /><Tooltip /><Line type="monotone" dataKey="ips" name="IPS" stroke="#4f46e5" strokeWidth={3} /><Line type="monotone" dataKey="ipk" name="IPK" stroke="#14b8a6" strokeWidth={3} /></LineChart></ResponsiveContainer></div> : <EmptyState title="Belum ada riwayat nilai" text="Riwayat akan tampil setelah data akademik dicatat." />}
      </section>
      {latest && <PredictionCard value={Number(latest.nilai_prediksi)} lower={Number(latest.batas_bawah)} upper={Number(latest.batas_atas)} status={latest.hasil} />}
      {latest?.faktor.items?.length ? <section className="content-card"><div className="section-heading"><div><h2>Faktor yang paling berpengaruh</h2><p>Ringkasan hubungan faktor dengan perkiraan nilai.</p></div></div><ul className="factor-list">{latest.faktor.items.slice(0, 5).map((factor) => <li key={factor.faktor}><strong>{factor.faktor} · {factor.arah}</strong><p>{factor.penjelasan}</p></li>)}</ul></section> : null}
      <section className="content-card">
        <div className="section-heading"><div><h2>Riwayat akademik</h2><p>Nilai dan kehadiran tercatat per semester.</p></div></div>
        {records.length ? <DataTable rows={records} rowId={(row) => row.id} columns={[{ key: "semester", label: "Semester", value: (row) => row.semester }, { key: "ips", label: "IPS", value: (row) => Number(row.ips).toFixed(2) }, { key: "ipk", label: "IPK", value: (row) => Number(row.ipk).toFixed(2) }, { key: "kehadiran", label: "Kehadiran", value: (row) => `${Number(row.kehadiran).toFixed(1)}%` }]} /> : <EmptyState title="Belum ada catatan" text="Data akademik belum diunggah." />}
      </section>
      <section className="content-card">
        <div className="section-heading"><div><h2>Catatan tindak lanjut</h2><p>Catat dukungan dan pantau langkah yang sudah dilakukan.</p></div></div>
        <form className="followup-form" onSubmit={(event: FormEvent) => { event.preventDefault(); saveNote.mutate(); }}>
          <label className="field"><span>Catatan baru</span><textarea required maxLength={5000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Tuliskan rencana dukungan..." /></label>
          <button className="primary-button" disabled={!latest || saveNote.isPending}>{saveNote.isPending ? "Menyimpan..." : "Tambah catatan"}</button>
        </form>
        {followUps.length ? <div className="followup-list">{followUps.map((item) => <article key={item.id}><p>{item.catatan}</p><small>{new Date(item.created_at).toLocaleDateString("id-ID")}</small><select aria-label={`Status catatan ${item.catatan.slice(0, 30)}`} value={item.status} onChange={(event) => changeStatus.mutate({ id: item.id, status: event.target.value as FollowUp["status"] })}><option value="baru">Baru</option><option value="dalam_penanganan">Diproses</option><option value="selesai">Selesai</option></select></article>)}</div> : <EmptyState title="Belum ada catatan" text="Tambahkan catatan singkat tentang tindak lanjut." />}
      </section>
      <Toast message={toast} kind={toast.includes("berhasil") ? "success" : "error"} onClose={() => setToast("")} />
      <span className="visually-hidden">{predictions.length} prediksi tersimpan</span>
    </>
  );
}

export function StudentHome() {
  const { user } = useAuth();
  const query = useQuery({ queryKey: ["student-dashboard"], queryFn: () => apiRequest<{ student: Student | null; records: AcademicRecord[]; predictions: Prediction[]; follow_ups: FollowUp[] }>("/dashboard/mahasiswa") });
  if (query.isLoading) return <Skeleton rows={4} />;
  if (query.error || !query.data) return <RetryPanel onRetry={() => void query.refetch()} />;
  const { student, records, predictions } = query.data;
  const latest = predictions.at(-1);
  const chartData = records.map((record) => ({ semester: `S${record.semester}`, ips: Number(record.ips), ipk: Number(record.ipk) }));
  const recommendations = latest?.faktor.items?.slice(0, 3).map((factor) => suggestionFor(factor.faktor, factor.arah)) ?? [
    "Buat jadwal belajar yang nyaman untukmu.",
    "Sisihkan waktu untuk mengulang materi setiap minggu.",
    "Bicarakan target belajarmu dengan dosen wali.",
  ];
  return (
    <>
      <section className="welcome-panel student-welcome">
        <div><p className="eyebrow">RUANG BELAJAR KAMU</p><h2>Hai, {user?.nama ?? student?.kode_anonim ?? "teman"}!</h2><p>Setiap langkah kecil tetap berarti. Kamu bisa melihat perkembangan dan memilih langkah berikutnya di sini.</p></div>
        <HeartHandshake className="welcome-symbol" aria-hidden="true" />
      </section>
      {latest ? <PredictionCard value={Number(latest.nilai_prediksi)} lower={Number(latest.batas_bawah)} upper={Number(latest.batas_atas)} status={latest.hasil} studentFriendly /> : <section className="content-card"><EmptyState title="Perjalananmu baru dimulai" text="Belum ada perkiraan baru. Dosen wali akan membantu memperbarui catatanmu." /></section>}
      <section className="content-card">
        <div className="section-heading"><div><h2>Perkembangan belajarmu</h2><p>Grafik sederhana untuk melihat perjalanan dari semester ke semester.</p></div></div>
        {chartData.length ? <div className="chart-box"><ResponsiveContainer width="100%" height={280}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="semester" /><YAxis domain={[0, 4]} /><Tooltip /><Line type="monotone" dataKey="ips" name="IPS" stroke="#4f46e5" strokeWidth={3} /><Line type="monotone" dataKey="ipk" name="IPK" stroke="#14b8a6" strokeWidth={3} /></LineChart></ResponsiveContainer></div> : <EmptyState title="Belum ada grafik" text="Perkembanganmu akan terlihat setelah nilai semester dicatat." />}
      </section>
      <section className="content-card">
        <div className="section-heading"><div><h2>Tiga langkah yang bisa kamu coba</h2><p>Pilih yang terasa paling sesuai untukmu.</p></div></div>
        <ol className="recommendation-list">{recommendations.map((text, index) => <li key={`${index}-${text}`}><span>{index + 1}</span>{text}</li>)}</ol>
      </section>
    </>
  );
}

function suggestionFor(factor: string, direction: string) {
  const normalized = factor.toLocaleLowerCase("id");
  if (normalized.includes("kehadiran")) return direction === "turun" ? "Pilih satu cara agar lebih mudah hadir, misalnya menyiapkan perjalanan sehari sebelumnya." : "Pertahankan kebiasaan hadir dan siapkan materi sebelum kelas.";
  if (normalized.includes("tugas")) return "Bagi tugas menjadi bagian kecil dan mulai dari tenggat yang paling dekat.";
  if (normalized.includes("semester")) return "Tinjau materi semester lalu dan pilih satu topik untuk diperkuat.";
  if (normalized.includes("tidur")) return "Coba atur waktu istirahat yang cukup agar rutinitas belajarmu terasa lebih ringan.";
  if (normalized.includes("kerja")) return "Atur jadwal belajar singkat di sela aktivitas mingguan.";
  return "Bicarakan faktor ini dengan dosen wali untuk mencari dukungan yang cocok.";
}

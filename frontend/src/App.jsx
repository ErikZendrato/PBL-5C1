
import { useEffect, useState } from "react";
import {
  predictGPA,
  predictDropout,
  getPredictions,
} from "./services/api";
import "./App.css";

const initialForm = {
  age: 20,
  admission_grade: 145,
  previous_qualification_grade: 130,
  gpa_semester_1: 2.8,
  attendance_rate: 85,
  assignments_submitted_rate: 90,
  library_visits_per_month: 8,
  lms_logins_per_week: 15,
  weekly_work_hours: 10,
  missed_deadlines: 2,
  commute_time_mins: 30,
  sleep_hours: 7,
  course_type: "STEM",
  study_mode: "Full-time",
};

function App() {
  const [page, setPage] = useState("dashboard");
  const [form, setForm] = useState(initialForm);
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadHistory() {
    try {
      const data = await getPredictions(50);
      setHistory(data.predictions ?? []);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function submitPrediction(type) {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = Object.fromEntries(
        Object.entries(form).map(([key, value]) => [
          key,
          value === "" ? value : Number(value),
        ])
      );

      // Dua field kategori tetap berupa teks.
      data.course_type = form.course_type;
      data.study_mode = form.study_mode;

      const response =
        type === "GPA"
          ? await predictGPA(data)
          : await predictDropout(data);

      setResult({ type, ...response });
      await loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const gpaCount = history.filter(
    (item) => item.prediction_type === "GPA"
  ).length;

  const dropoutCount = history.filter(
    (item) => item.prediction_type === "DROPOUT"
  ).length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">P</div>
          <div>
            <strong>Prediksi Mahasiswa</strong>
            <span>Academic Intelligence</span>
          </div>
        </div>

        <p className="nav-label">MENU UTAMA</p>

        {[
          ["dashboard", "Dashboard"],
          ["predict", "Prediksi Performa"],
          ["history", "Riwayat Prediksi"],
        ].map(([key, label]) => (
          <button
            key={key}
            className={`nav-item ${page === key ? "active" : ""}`}
            onClick={() => setPage(key)}
          >
            {label}
          </button>
        ))}

        <div className="sidebar-footer">
          <span className="status-dot" />
          Sistem Prediksi Mahasiswa
          <small>Prototype PBL</small>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">ACADEMIC ANALYTICS</p>
            <h1>
              {page === "dashboard"
                ? "Dashboard"
                : page === "predict"
                  ? "Prediksi Performa"
                  : "Riwayat Prediksi"}
            </h1>
          </div>
          <span className="topbar-tag">Semester 5 · PBL</span>
        </header>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {page === "dashboard" && (
          <>
            <section className="welcome-panel">
              <div>
                <p className="eyebrow light">STUDENT PERFORMANCE SYSTEM</p>
                <h2>Memahami performa mahasiswa lebih awal.</h2>
                <p>
                  Gunakan model machine learning untuk memperkirakan
                  GPA dan mengidentifikasi indikasi risiko dropout.
                </p>
                <button
                  className="primary-button"
                  onClick={() => setPage("predict")}
                >
                  Mulai Prediksi
                </button>
              </div>
              <div className="welcome-symbol">P.</div>
            </section>

            <section className="stats-grid">
              <article className="stat-card">
                <span>Total Riwayat</span>
                <strong>{history.length}</strong>
                <small>Data dari database</small>
              </article>
              <article className="stat-card">
                <span>Prediksi GPA</span>
                <strong>{gpaCount}</strong>
                <small>Estimasi nilai akademik</small>
              </article>
              <article className="stat-card">
                <span>Prediksi Dropout</span>
                <strong>{dropoutCount}</strong>
                <small>Analisis risiko</small>
              </article>
            </section>

            <section className="content-card">
              <div className="section-heading">
                <div>
                  <h2>Prediksi Terbaru</h2>
                  <p>Hasil yang terakhir tersimpan di database.</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => setPage("history")}
                >
                  Lihat semua
                </button>
              </div>
              <HistoryTable items={history.slice(0, 5)} />
            </section>
          </>
        )}

        {page === "predict" && (
          <section className="content-card">
            <div className="section-heading">
              <div>
                <h2>Data Input Mahasiswa</h2>
                <p>
                  Masukkan data untuk menjalankan model prediksi.
                </p>
              </div>
            </div>

            <div className="form-grid">
              {[
                ["age", "Usia", 0, 100, 1],
                ["admission_grade", "Nilai Penerimaan", 0, 200, 0.1],
                ["previous_qualification_grade", "Nilai Kualifikasi Sebelumnya", 0, 200, 0.1],
                ["gpa_semester_1", "GPA Semester 1", 0, 4, 0.01],
                ["attendance_rate", "Kehadiran (%)", 0, 100, 0.1],
                ["assignments_submitted_rate", "Tugas Dikumpulkan (%)", 0, 100, 0.1],
                ["library_visits_per_month", "Kunjungan Perpustakaan/Bulan", 0, 100, 1],
                ["lms_logins_per_week", "Login LMS/Minggu", 0, 500, 1],
                ["weekly_work_hours", "Jam Kerja/Minggu", 0, 168, 0.5],
                ["missed_deadlines", "Tugas Terlambat", 0, 100, 1],
                ["commute_time_mins", "Waktu Perjalanan (Menit)", 0, 1440, 1],
                ["sleep_hours", "Jam Tidur/Hari", 0, 24, 0.5],
              ].map(([name, label, min, max, step]) => (
                <label className="field" key={name}>
                  <span>{label}</span>
                  <input
                    type="number"
                    name={name}
                    min={min}
                    max={max}
                    step={step}
                    value={form[name]}
                    onChange={updateField}
                    required
                  />
                </label>
              ))}

              <label className="field">
                <span>Jenis Program</span>
                <select
                  name="course_type"
                  value={form.course_type}
                  onChange={updateField}
                >
                  {[
                    "STEM",
                    "Arts & Humanities",
                    "Business",
                    "Health Sciences",
                    "Law & Social Sciences",
                  ].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Mode Studi</span>
                <select
                  name="study_mode"
                  value={form.study_mode}
                  onChange={updateField}
                >
                  {["Online", "Full-time", "Part-time"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="form-actions">
              <button
                className="secondary-button"
                onClick={() => {
                  setForm(initialForm);
                  setResult(null);
                }}
              >
                Reset
              </button>
              <button
                className="primary-button"
                disabled={loading}
                onClick={() => submitPrediction("GPA")}
              >
                {loading ? "Memproses..." : "Prediksi GPA"}
              </button>
              <button
                className="primary-button dark-button"
                disabled={loading}
                onClick={() => submitPrediction("DROPOUT")}
              >
                {loading ? "Memproses..." : "Prediksi Dropout"}
              </button>
            </div>

            {result && (
              <div className="result-panel">
                <h3>Hasil Prediksi</h3>
                {result.type === "GPA" ? (
                  <p>
                    Estimasi GPA:{" "}
                    <strong>{result.predicted_gpa}</strong> dari skala 4.
                  </p>
                ) : (
                  <>
                    <p>
                      Klasifikasi model:{" "}
                      <strong>
                        {result.dropout_prediction === 1
                          ? "Terindikasi dropout"
                          : "Tidak terindikasi dropout"}
                      </strong>
                    </p>
                    <p>
                      Probabilitas kelas dropout:{" "}
                      <strong>
                        {(
                          result.dropout_probability * 100
                        ).toFixed(1)}%
                      </strong>
                    </p>
                  </>
                )}
                <small>
                  Hasil merupakan estimasi model, bukan keputusan
                  akademik atau kepastian kondisi mahasiswa.
                </small>
              </div>
            )}
          </section>
        )}

        {page === "history" && (
          <section className="content-card">
            <div className="section-heading">
              <div>
                <h2>Riwayat Prediksi</h2>
                <p>
                  {history.length} data ditemukan dari API.
                </p>
              </div>
              <button
                className="secondary-button"
                onClick={loadHistory}
              >
                Muat Ulang
              </button>
            </div>
            <HistoryTable items={history} />
          </section>
        )}

        <footer className="page-footer">
          Prediksi Performa Mahasiswa · Proyek PBL · Prototype
        </footer>
      </main>
    </div>
  );
}

function HistoryTable({ items }) {
  if (!items.length) {
    return (
      <div className="empty-state">
        <strong>Belum ada riwayat prediksi</strong>
        <p>Jalankan prediksi terlebih dahulu untuk melihat data di sini.</p>
      </div>
    );
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Jenis</th>
            <th>Hasil</th>
            <th>Probabilitas</th>
            <th>Waktu</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>#{item.id}</td>
              <td>
                <span className="type-tag">
                  {item.prediction_type}
                </span>
              </td>
              <td>
                {item.prediction_type === "GPA"
                  ? item.predicted_value ?? "—"
                  : item.predicted_class === 1
                    ? "Terindikasi dropout"
                    : item.predicted_class === 0
                      ? "Tidak terindikasi dropout"
                      : "—"}
              </td>
              <td>
                {item.dropout_probability == null
                  ? "—"
                  : `${(
                      Number(item.dropout_probability) * 100
                    ).toFixed(1)}%`}
              </td>
              <td>
                {item.created_at
                  ? new Date(item.created_at).toLocaleString("id-ID")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;

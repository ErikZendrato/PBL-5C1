import { useState, type FormEvent } from "react";
import { Eye, EyeOff, GraduationCap } from "lucide-react";
import { supabase } from "../lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError) setError("Email atau kata sandi belum tepat. Periksa kembali lalu coba lagi.");
    } catch {
      setError("Belum dapat terhubung. Periksa koneksi internet lalu coba lagi.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-story" aria-label="Tentang Performa Akademik">
        <div className="story-brand"><span className="brand-icon"><GraduationCap size={26} /></span><strong>Performa Akademik</strong></div>
        <div className="story-content">
          <div className="story-illustration" aria-hidden="true">
            <div className="story-orbit orbit-one" /><div className="story-orbit orbit-two" />
            <GraduationCap className="story-cap" />
            <span className="story-star star-one">✦</span><span className="story-star star-two">✦</span>
          </div>
          <p className="eyebrow">RUANG TUMBUH BERSAMA</p>
          <h2>Bantu setiap mahasiswa tumbuh lebih baik</h2>
          <p>Pantau perjalanan belajar, temukan dukungan yang tepat, dan rayakan setiap kemajuan.</p>
        </div>
        <span className="story-footer">Satu langkah kecil hari ini berarti.</span>
      </section>
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-logo" aria-hidden="true"><GraduationCap /></div>
        <p className="eyebrow">Sistem Akademik</p>
        <h1 id="login-title">Masuk ke akun kamu</h1>
        <p className="login-subtitle">Gunakan akun yang diberikan oleh admin.</p>
        <form onSubmit={submit}>
          <label className="field"><span>Email</span><input type="email" autoComplete="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <label className="field password-field">
            <span>Kata sandi</span>
            <div>
              <input type={visible ? "text" : "password"} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <button type="button" aria-label={visible ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"} onClick={() => setVisible((value) => !value)}>
                {visible ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </label>
          {error && <p role="alert" className="error-message">{error}</p>}
          <button className="primary-button login-button" disabled={loading}>{loading ? "Memproses..." : "Masuk"}</button>
          <button type="button" className="forgot-link" onClick={() => setError("Untuk mengatur ulang kata sandi, silakan hubungi admin kampus.")}>Lupa kata sandi?</button>
        </form>
      </section>
    </main>
  );
}

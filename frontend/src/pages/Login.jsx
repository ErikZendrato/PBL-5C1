import { useState } from "react";
import { useAuth } from "../auth.jsx";
import { Err } from "../components.jsx";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { await login(email, password); } catch (x) { setErr(x.message); }
    setBusy(false);
  };
  return (
    <div className="login">
      <section className="left">
        <h1>Sistem Prediksi Performa Akademik Mahasiswa</h1>
        <p>Informasi tambahan berbasis data untuk mendukung dosen dan pihak akademik dalam memantau dan mendampingi mahasiswa.</p>
      </section>
      <section className="right">
        <form className="card" onSubmit={submit}>
          <div><h2>Masuk</h2><p className="lbl" style={{ marginTop: 6 }}>Gunakan akun Admin, Dosen, atau Mahasiswa.</p></div>
          <label className="lbl">Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@kampus.ac.id" /></label>
          <label className="lbl">Kata sandi<input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          <Err msg={err} />
          <button className="btn" disabled={busy}>{busy ? "Memproses..." : "Masuk"}</button>
        </form>
      </section>
    </div>
  );
}

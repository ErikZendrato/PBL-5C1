# Sistem Prediksi Performa Akademik Mahasiswa

React (frontend) + FastAPI (backend) + scikit-learn + Supabase (PostgreSQL dan autentikasi).
Yang diprediksi: IP semester berikutnya. IPK dihitung dari IP prediksi dan SKS.

```
supabase/   001_schema.sql, 002_backend_support.sql
backend/    FastAPI (app/routers, app/services/ml.py)
frontend/   React + Vite
```

## 1. Supabase
1. Buat project di supabase.com.
2. SQL Editor: jalankan `supabase/001_schema.sql`, lalu `supabase/002_backend_support.sql`.
3. Authentication > Users > Add user: buat akun Admin pertama (email + kata sandi), salin UUID-nya.
4. SQL Editor, jadikan akun itu Admin:
   ```sql
   insert into profiles (id, full_name, role) values ('UUID-ADMIN', 'Admin', 'admin');
   ```
5. Settings > API: catat Project URL, anon key, dan service_role key.

## 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # isi SUPABASE_URL dan SUPABASE_SERVICE_KEY
uvicorn app.main:app --reload
```
Dokumentasi API: http://localhost:8000/docs

## 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env        # isi VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY (anon, bukan service role)
npm run dev
```
Buka http://localhost:5173

## 4. Urutan pemakaian pertama kali
1. Login sebagai Admin. Menu Program Studi dan Semester: isi data (kolom "Urutan" semester harus kronologis).
2. Impor CSV: mata kuliah, mahasiswa, lalu nilai historis (`grades_history`). Format kolom ada di halaman Impor CSV.
3. Pengguna: buat akun Dosen dan Mahasiswa. Hubungkan akun mahasiswa lewat menu Mahasiswa (kolom Akun mahasiswa).
4. Penugasan Dosen dan KRS untuk semester berjalan. Dosen login, input nilai per mata kuliah, lalu Tandai final.
   IP dan IPK dihitung otomatis jika semua mata kuliah mahasiswa pada semester itu sudah final.
5. Model & Prediksi: Latih model baru, aktifkan (hanya jika lebih baik dari baseline), lalu Jalankan prediksi.
6. Dashboard, Prediksi, Peringatan Dini, dan Riwayat Prediksi terisi.

## Catatan penting
- Backend memakai service role dan menegakkan hak akses sendiri (deps.py dan scope.py). RLS di database tetap
  aktif sebagai lapisan kedua untuk akses langsung ke database.
- Aturan "mahasiswa mana yang boleh dilihat dosen" ada di `backend/app/scope.py`. Sesuaikan dengan keputusan kampus.
- Model butuh data: minimal 40 pasang (mahasiswa, semester) dan minimal 2 semester sasaran. Dengan data sedikit,
  hasilnya tidak bisa dipercaya. Model tidak boleh dipakai jika tidak mengalahkan baseline.
- Batas kategori (stabil, meningkat, menurun) default-nya mengikuti MAE model. Validasi dengan data kampus.
- Audit log: trigger database mencatat perubahan, tetapi `actor_id` kosong untuk perubahan lewat backend
  (service role). Jika perlu pelaku tercatat, tambahkan pencatatan di backend.
- Skala nilai ada di tabel `grade_scale`. Sesuaikan dengan aturan kampus sebelum impor nilai.
- Jangan commit file `.env`. Kunci service role tidak boleh ada di frontend.

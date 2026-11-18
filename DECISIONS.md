- Stack dan struktur proyek mengikuti FastAPI + React/Vite yang sudah tersedia.
- Model akademik awal dipetakan ke kategori Baik, Cukup, dan Perlu Perhatian.
- Aplikasi memakai timezone Indonesia Barat untuk penanggalan dan seed.
- Semua seed mahasiswa adalah dummy dan tidak memiliki data identitas nyata.
- Supabase Auth menjadi sumber identitas; roles disimpan di profiles.
- Service role key hanya digunakan oleh backend dan tidak disimpan di frontend.
- Demo password default adalah Demo123! dan wajib diganti di deployment.
- Migrasi utama dibuat untuk Supabase CLI; seed dipisahkan agar mudah dijalankan.


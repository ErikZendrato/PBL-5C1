# Sistem Prediksi Performa Akademik Mahasiswa

Aplikasi berbasis FastAPI dan React untuk memantau performa akademik mahasiswa serta mendukung tindak lanjut dosen.

## Jalankan lokal

1. Buat akun Auth di Supabase dengan UID yang tercantum pada `supabase/seed.sql` dan tetapkan kata sandi masing-masing.
2. Jalankan berurutan semua file `supabase/migrations/` di Supabase SQL Editor, lalu tinjau dan jalankan `supabase/seed.sql` secara manual.
3. Backend:
   ```powershell
   cd backend
   Copy-Item .env.example .env
   uv sync
   uv run uvicorn backend.main:app --reload
   ```
4. Frontend:
   ```powershell
   cd frontend
   Copy-Item .env.example .env.local
   npm install
   npm run dev
   ```

## Akun demo

| Peran | Email | UID |
|---|---|---|
| Admin | `admin@dummy.local` | `35b36fe9-c93b-4326-980e-669cf65be43a` |
| Dosen | `dosen@dummy.local` | `9c17c214-dde8-4126-8a57-66c08745a6f2` |
| Mahasiswa | `mahasiswa@dummy.local` | `3f6e66b4-b288-4dc3-bdd4-a147bc4d7c45` |

Buat akun dengan email dan UID tersebut melalui Supabase Auth sebelum menjalankan seed; kata sandi ditetapkan saat pembuatan akun. Ganti akun dan kata sandi demo sebelum deployment.

## Pengujian

```powershell
cd backend
uv run pytest -q
cd ../frontend
npm run build
```

## Deploy

- **Supabase:** buat project, Auth, migrasi, dan seed.
- **Backend:** deploy `backend/` ke Render atau Railway sebagai service Python. Set semua variabel dari `backend/.env.example`. Jalankan perintah startup `uv run uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- **Frontend:** deploy `frontend/` ke Vercel dengan framework Vite. Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, dan `VITE_API_URL`.
- Batasi `CORS_ORIGINS` pada domain backend/frontend produksi.
- Jangan letakkan service role key atau JWT secret di frontend.

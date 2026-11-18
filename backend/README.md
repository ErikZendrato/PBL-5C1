# Backend

FastAPI, scikit-learn, Supabase Auth, dan joblib.

## Konfigurasi

```powershell
Copy-Item .env.example .env
uv sync
uv run uvicorn backend.main:app --reload
```

Isi URL Supabase, anon key, service role key, JWT secret, dan alamat CORS.
Service role key hanya boleh berada pada environment backend. Autentikasi
mendukung signing key Supabase ES256 melalui JWKS publik proyek dan HS256
legacy melalui `SUPABASE_JWT_SECRET`.

## Model prediksi

Model aktif adalah Pipeline `LinearRegression` untuk target `gpa_semester_2`
(skala 0–4), dimuat dari `models/linear_regression_v2_1/model.pkl`.
Endpoint `/predict` mengembalikan perkiraan, rentang berbasis MAE, kategori,
dan lima faktor teratas. Input mengikuti kolom fitur pada template CSV.

Buat sampel evaluasi web dan hitung MAE/RMSE dari ekspor prediksi `/predict/batch`:

```powershell
uv run python -m backend.make_upload_sample
uv run python -m backend.evaluate_upload data\prediksi_web.json
```

Ekspor JSON respons `/predict/batch` langsung ke `data\prediksi_web.json`;
alternatifnya gunakan CSV dengan kolom `nilai_prediksi` dalam urutan sampel.

## Pengujian

```powershell
uv run pytest -q
```

Evaluasi 30 baris acak dari `data\test.csv` langsung dengan model tersimpan:

```powershell
uv run python -m backend.evaluate_test_sample
```

Skrip menyimpan kunci jawaban, hasil prediksi, dan fitur sampel untuk unggah
web; metrik dicetak untuk sampel dan seluruh test set.

## Siapkan CSV untuk unggah web

Ekspor tabel `students` dari Supabase sebagai CSV yang memuat kolom `id`, lalu
gabungkan ID tersebut dengan fitur pada `data\upload_test_features.csv`:

```powershell
uv run python -m backend.make_upload_template --input data\upload_test_features.csv --students data\students.csv --output data\upload_admin_test.csv
```

Skrip menghasilkan `data\upload_admin_test.csv` tanpa mengakses database. IPS
dan IPK diisi dari `gpa_semester_1`, kehadiran dari `attendance_rate`, semester
ditetapkan ke 7, dan SKS diisi 20. Siapkan setidaknya satu ID mahasiswa unik
untuk setiap baris sampel agar tidak ada duplikat mahasiswa-semester.
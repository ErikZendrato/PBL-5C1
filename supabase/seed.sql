-- Akun demo dibuat terlebih dahulu melalui Supabase Auth.

insert into public.profiles (id, nama, role) values
  ('35b36fe9-c93b-4326-980e-669cf65be43a'::uuid, 'Admin Demo', 'admin'),
  ('9c17c214-dde8-4126-8a57-66c08745a6f2'::uuid, 'Dosen Demo', 'dosen'),
  ('3f6e66b4-b288-4dc3-bdd4-a147bc4d7c45'::uuid, 'Mahasiswa Demo', 'mahasiswa')
on conflict (id) do update set nama = excluded.nama, role = excluded.role;

insert into public.students (id, kode_anonim, prodi, angkatan, dosen_wali_id, profile_id)
select gen_random_uuid(), 'MHS-DUMMY-' || lpad(n::text, 3, '0'),
       case when n % 3 = 0 then 'Teknik Informatika' when n % 3 = 1 then 'Sistem Informasi' else 'Teknologi Informasi' end,
       2023 + (n % 3), '9c17c214-dde8-4126-8a57-66c08745a6f2'::uuid,
       case when n = 1 then '3f6e66b4-b288-4dc3-bdd4-a147bc4d7c45'::uuid else null end
from generate_series(1, 30) n
on conflict (kode_anonim) do nothing;

insert into public.academic_records (
  student_id, semester, ips, ipk, sks, kehadiran, mata_kuliah_lulus,
  mata_kuliah_gagal, age, admission_grade, previous_qualification_grade,
  gpa_semester_1, attendance_rate, assignments_submitted_rate,
  library_visits_per_month, lms_logins_per_week, weekly_work_hours,
  missed_deadlines, commute_time_mins, sleep_hours, course_type, study_mode
)
select s.id, sem, round((case
         when n <= 10 then 2.55 + n * 0.055 + sem * 0.015
         when n <= 20 then 3.35 - n * 0.015 + sem * 0.025
         else 2.95 + (n % 7) * 0.05 + sem * 0.018 end)::numeric, 2),
       round((case
         when n <= 10 then 2.60 + n * 0.045 + sem * 0.012
         when n <= 20 then 3.30 - n * 0.012 + sem * 0.02
         else 2.90 + (n % 7) * 0.04 + sem * 0.015 end)::numeric, 2),
       18 + sem % 4, round((88 + (n % 10) - sem * 0.6)::numeric, 2),
       14 + sem, greatest(0, sem / 8),
       18 + n % 8, 100 + n % 80, 90 + n % 90,
       round((2.2 + (n % 15) * 0.1 + (sem % 3) * 0.05)::numeric, 2),
       80 + n % 15, 70 + (n + sem) % 20, n % 12,
       round((4 + (n % 20) * 1.2)::numeric, 1),
       n % 41, (n + sem) % 8, 10 + n % 100,
       round((5 + (n + sem) % 5 * 0.5)::numeric, 1),
       case n % 5
         when 0 then 'Arts & Humanities'
         when 1 then 'Business'
         when 2 then 'Health Sciences'
         when 3 then 'Law & Social Sciences'
         else 'STEM'
       end,
       case n % 3
         when 0 then 'Full-time'
         when 1 then 'Online'
         else 'Part-time'
       end
from public.students s
join lateral (
  select cast(regexp_replace(s.kode_anonim, '[^0-9]', '', 'g') as integer) n
) rn on true
cross join generate_series(1, 6) sem
where not exists (select 1 from public.academic_records ar where ar.student_id = s.id and ar.semester = sem)
  and s.kode_anonim like 'MHS-DUMMY-%';

insert into public.model_versions (versi, algoritma, metrik, tanggal) values
  ('v2.1-kaggle', 'LinearRegression', '{"mae": 0.3197907134312804, "rmse": 0.39978101687024753, "r2": 0.69102662505606}'::jsonb, current_date)
on conflict (versi) do update set algoritma = excluded.algoritma, metrik = excluded.metrik;

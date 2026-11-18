create extension if not exists pgcrypto;

create type user_role as enum ('admin', 'dosen', 'mahasiswa');
create type follow_up_status as enum ('baru', 'dalam_penanganan', 'selesai');

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nama text not null,
  role user_role not null
);

create table if not exists public.students (
  id uuid primary key default gen_random_uuid(),
  kode_anonim text unique not null,
  prodi text not null,
  angkatan integer not null check (angkatan between 2020 and 2100),
  dosen_wali_id uuid references auth.users(id),
  profile_id uuid unique references public.profiles(id)
);

create table if not exists public.academic_records (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  semester integer not null check (semester between 1 and 14),
  ips numeric(3,2) not null check (ips between 0 and 4),
  ipk numeric(3,2) not null check (ipk between 0 and 4),
  sks integer not null check (sks >= 0),
  kehadiran numeric(5,2) not null check (kehadiran between 0 and 100),
  mata_kuliah_lulus integer not null default 0 check (mata_kuliah_lulus >= 0),
  mata_kuliah_gagal integer not null default 0 check (mata_kuliah_gagal >= 0),
  created_at timestamptz not null default now(),
  unique (student_id, semester)
);

create table if not exists public.predictions (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.students(id) on delete cascade,
  semester_target integer not null,
  hasil text not null check (hasil in ('Baik', 'Cukup', 'Perlu Perhatian')),
  probabilitas numeric(5,4) not null check (probabilitas between 0 and 1),
  faktor jsonb not null default '{}'::jsonb,
  model_version text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.model_versions (
  versi text primary key,
  algoritma text not null,
  metrik jsonb not null default '{}'::jsonb,
  tanggal date not null default current_date
);

create table if not exists public.follow_ups (
  id uuid primary key default gen_random_uuid(),
  prediction_id uuid not null references public.predictions(id) on delete cascade,
  dosen_id uuid not null references auth.users(id),
  catatan text not null,
  status follow_up_status not null default 'baru',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_students_wali on public.students(dosen_wali_id);
create index if not exists idx_students_profile on public.students(profile_id);
create index if not exists idx_records_student_semester on public.academic_records(student_id, semester);
create index if not exists idx_predictions_student on public.predictions(student_id, created_at desc);
create index if not exists idx_followups_prediction on public.follow_ups(prediction_id);

create or replace function public.current_role()
returns user_role language sql stable security definer set search_path = public as
$$ select role from public.profiles where id = auth.uid() $$;

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as
$$ select public.current_role() = 'admin' $$;

create or replace function public.is_dosen()
returns boolean language sql stable security definer set search_path = public as
$$ select public.current_role() = 'dosen' $$;

alter table public.profiles enable row level security;
alter table public.students enable row level security;
alter table public.academic_records enable row level security;
alter table public.predictions enable row level security;
alter table public.model_versions enable row level security;
alter table public.follow_ups enable row level security;

create policy profiles_read on public.profiles for select using (
  public.is_admin() or id = auth.uid()
);

create policy profiles_admin_write on public.profiles for all using (public.is_admin())
  with check (public.is_admin());

create policy students_access on public.students for select using (
  public.is_admin()
  or dosen_wali_id = auth.uid()
  or profile_id = auth.uid()
);

create policy students_admin_write on public.students for all using (public.is_admin())
  with check (public.is_admin());

create policy records_access on public.academic_records for select using (
  exists (
    select 1 from public.students s
    where s.id = student_id
      and (public.is_admin() or s.dosen_wali_id = auth.uid() or s.profile_id = auth.uid())
  )
);

create policy records_admin_write on public.academic_records for all using (public.is_admin())
  with check (public.is_admin());

create policy predictions_access on public.predictions for select using (
  exists (
    select 1 from public.students s
    where s.id = student_id
      and (public.is_admin() or s.dosen_wali_id = auth.uid() or s.profile_id = auth.uid())
  )
);

create policy predictions_admin_write on public.predictions for all using (public.is_admin())
  with check (public.is_admin());

create policy model_versions_read on public.model_versions for select using (auth.role() = 'authenticated');
create policy model_versions_admin_write on public.model_versions for all using (public.is_admin())
  with check (public.is_admin());

create policy follow_ups_access on public.follow_ups for select using (
  public.is_admin()
  or dosen_id = auth.uid()
  or exists (
    select 1 from public.predictions p join public.students s on s.id = p.student_id
    where p.id = prediction_id and s.profile_id = auth.uid()
  )
);

create policy follow_ups_dosen_write on public.follow_ups for all using (
  public.is_admin() or (public.is_dosen() and dosen_id = auth.uid())
) with check (
  public.is_admin() or (public.is_dosen() and dosen_id = auth.uid())
);


-- =====================================================================
-- Sistem Prediksi Performa Akademik Mahasiswa
-- Skema database PostgreSQL (Supabase) + Row Level Security
-- Yang diprediksi: IP semester berikutnya. IPK dihitung dari IP dan SKS.
-- Dosen menginput nilai mata kuliah yang diampunya sendiri.
-- =====================================================================

-- ---------- 1. ENUM ----------
create type user_role     as enum ('admin', 'dosen', 'mahasiswa');
create type grade_status  as enum ('draft', 'final');
create type perf_category as enum ('stabil', 'berpotensi_meningkat', 'berpotensi_menurun');

-- ---------- 2. DATA INDUK ----------
-- Profil pengguna, terhubung ke tabel auth.users milik Supabase
create table profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  full_name   text        not null,
  role        user_role   not null default 'mahasiswa',
  is_active   boolean     not null default true,
  created_at  timestamptz not null default now()
);

create table academic_programs (
  id    bigint generated always as identity primary key,
  code  text not null unique,
  name  text not null
);

create table students (
  id             bigint generated always as identity primary key,
  profile_id     uuid unique references profiles(id) on delete set null,
  student_number text not null unique,              -- ID internal / NIM
  full_name      text not null,
  program_id     bigint not null references academic_programs(id),
  entry_year     int    not null check (entry_year between 2000 and 2100),
  advisor_id     uuid references profiles(id),      -- dosen wali (opsional, lihat keputusan terbuka)
  show_prediction boolean not null default false,   -- mahasiswa boleh melihat prediksinya?
  created_at     timestamptz not null default now()
);

create table semesters (
  id            bigint generated always as identity primary key,
  code          text not null unique,               -- contoh: '2024-1'
  academic_year text not null,                      -- contoh: '2024/2025'
  term          smallint not null check (term in (1, 2)),
  sort_order    int not null unique,                -- urutan kronologis semester
  is_active     boolean not null default false
);

create table courses (
  id         bigint generated always as identity primary key,
  code       text not null unique,
  name       text not null,
  credits    smallint not null check (credits > 0),
  program_id bigint references academic_programs(id)
);

-- Skala nilai (sesuaikan dengan aturan kampus)
create table grade_scale (
  letter text primary key,
  points numeric(3,2) not null check (points between 0 and 4)
);
insert into grade_scale (letter, points) values
  ('A', 4.00), ('AB', 3.50), ('B', 3.00), ('BC', 2.50),
  ('C', 2.00), ('D', 1.00), ('E', 0.00);

-- ---------- 3. PENUGASAN DAN KRS ----------
-- Dosen yang mengampu mata kuliah pada semester tertentu
create table course_assignments (
  id          bigint generated always as identity primary key,
  lecturer_id uuid   not null references profiles(id),
  course_id   bigint not null references courses(id),
  semester_id bigint not null references semesters(id),
  unique (lecturer_id, course_id, semester_id)
);

-- KRS: mahasiswa mengambil mata kuliah pada semester tertentu
create table enrollments (
  id          bigint generated always as identity primary key,
  student_id  bigint not null references students(id) on delete cascade,
  course_id   bigint not null references courses(id),
  semester_id bigint not null references semesters(id),
  unique (student_id, course_id, semester_id)
);

-- ---------- 4. NILAI ----------
create table course_grades (
  id            bigint generated always as identity primary key,
  enrollment_id bigint not null unique references enrollments(id) on delete cascade,
  letter        text references grade_scale(letter),
  status        grade_status not null default 'draft',  -- draf bisa diubah dosen, final terkunci
  entered_by    uuid references profiles(id),
  finalized_at  timestamptz,
  updated_at    timestamptz not null default now()
);

-- IP, IPK, dan SKS per mahasiswa per semester (hasil hitung otomatis)
create table academic_records (
  id                 bigint generated always as identity primary key,
  student_id         bigint not null references students(id) on delete cascade,
  semester_id        bigint not null references semesters(id),
  semester_gpa       numeric(3,2),          -- IP semester
  cumulative_gpa     numeric(3,2),          -- IPK sampai semester ini
  credits_taken      int,                   -- SKS semester ini
  cumulative_credits int,                   -- total SKS sampai semester ini
  calculated_at      timestamptz not null default now(),
  unique (student_id, semester_id)
);

-- ---------- 5. MACHINE LEARNING ----------
create table model_versions (
  id                bigint generated always as identity primary key,
  version           text not null unique,         -- contoh: 'v1.0'
  algorithm         text not null,                -- contoh: 'Gradient Boosting'
  training_semesters text,                        -- semester yang dipakai melatih
  mae               numeric(5,3),
  rmse              numeric(5,3),
  r2                numeric(5,3),
  baseline_mae      numeric(5,3),                 -- pembanding: IP terakhir dianggap sama
  artifact_path     text,                         -- lokasi file model
  is_active         boolean not null default false,
  created_by        uuid references profiles(id),
  created_at        timestamptz not null default now()
);
-- Hanya satu model yang boleh aktif
create unique index one_active_model on model_versions (is_active) where is_active;

create table predictions (
  id                 bigint generated always as identity primary key,
  student_id         bigint not null references students(id) on delete cascade,
  target_semester_id bigint not null references semesters(id),
  model_version_id   bigint not null references model_versions(id),
  predicted_ip       numeric(3,2) not null,
  predicted_ipk      numeric(3,2),
  category           perf_category not null,
  actual_ip          numeric(3,2),                -- terisi otomatis setelah nilai aktual ada
  abs_error          numeric(3,2) generated always as (abs(predicted_ip - actual_ip)) stored,
  followed_up        boolean not null default false,  -- peringatan sudah ditindaklanjuti
  followed_up_by     uuid references profiles(id),
  followed_up_at     timestamptz,
  created_at         timestamptz not null default now(),
  unique (student_id, target_semester_id, model_version_id)
);

-- ---------- 6. AUDIT ----------
create table audit_logs (
  id         bigint generated always as identity primary key,
  actor_id   uuid references profiles(id),
  action     text not null,                       -- INSERT / UPDATE / DELETE
  table_name text not null,
  record_id  text,
  old_data   jsonb,
  new_data   jsonb,
  created_at timestamptz not null default now()
);

-- ---------- 7. INDEKS ----------
create index on students (program_id);
create index on students (advisor_id);
create index on course_assignments (course_id, semester_id);
create index on course_assignments (lecturer_id);
create index on enrollments (student_id, semester_id);
create index on enrollments (course_id, semester_id);
create index on academic_records (student_id, semester_id);
create index on predictions (student_id, target_semester_id);
create index on predictions (category) where not followed_up;
create index on audit_logs (table_name, created_at desc);

-- =====================================================================
-- FUNGSI BANTU
-- =====================================================================
create or replace function auth_role() returns user_role
language sql stable security definer set search_path = public as $$
  select role from profiles where id = auth.uid() and is_active
$$;

-- Apakah dosen yang login boleh melihat mahasiswa ini?
-- Aturan sementara: dosen wali, atau dosen yang mengampu salah satu mata kuliah mahasiswa.
-- Ubah sesuai keputusan (hanya kelas, atau semua mahasiswa bimbingan).
create or replace function dosen_can_see_student(p_student_id bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from students s where s.id = p_student_id and s.advisor_id = auth.uid())
      or exists (
        select 1
        from enrollments e
        join course_assignments ca
          on ca.course_id = e.course_id and ca.semester_id = e.semester_id
        where e.student_id = p_student_id and ca.lecturer_id = auth.uid()
      )
$$;

-- Apakah dosen yang login mengampu enrollment ini?
create or replace function dosen_teaches_enrollment(p_enrollment_id bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1
    from enrollments e
    join course_assignments ca
      on ca.course_id = e.course_id and ca.semester_id = e.semester_id
    where e.id = p_enrollment_id and ca.lecturer_id = auth.uid()
  )
$$;

-- Apakah student ini adalah mahasiswa yang login?
create or replace function is_own_student(p_student_id bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from students s where s.id = p_student_id and s.profile_id = auth.uid())
$$;

-- =====================================================================
-- PERHITUNGAN IP DAN IPK OTOMATIS
-- IP dihitung hanya jika SEMUA mata kuliah mahasiswa pada semester itu sudah final.
-- IPK = rata-rata IP tertimbang SKS dari semua semester sampai semester ini.
-- Dipanggil oleh backend (service role) setelah dosen memfinalkan nilai.
-- =====================================================================
create or replace function compute_semester_records(p_semester_id bigint) returns int
language plpgsql security definer set search_path = public as $$
declare
  n int;
begin
  insert into academic_records (student_id, semester_id, semester_gpa, credits_taken)
  select s.student_id, p_semester_id, round(s.ip, 2), s.sks
  from (
    select e.student_id,
           sum(gs.points * c.credits) / nullif(sum(c.credits), 0) as ip,
           sum(c.credits)::int as sks,
           bool_and(coalesce(cg.status = 'final', false)) as all_final
    from enrollments e
    join courses c on c.id = e.course_id
    left join course_grades cg on cg.enrollment_id = e.id
    left join grade_scale gs on gs.letter = cg.letter
    where e.semester_id = p_semester_id
    group by e.student_id
  ) s
  where s.all_final
  on conflict (student_id, semester_id) do update
    set semester_gpa  = excluded.semester_gpa,
        credits_taken = excluded.credits_taken,
        calculated_at = now();
  get diagnostics n = row_count;

  update academic_records ar
  set cumulative_gpa     = round(x.cgpa, 2),
      cumulative_credits = x.cs
  from (
    select a2.student_id, a2.semester_id,
           sum(a3.semester_gpa * a3.credits_taken) / nullif(sum(a3.credits_taken), 0) as cgpa,
           sum(a3.credits_taken)::int as cs
    from academic_records a2
    join semesters s2 on s2.id = a2.semester_id
    join academic_records a3 on a3.student_id = a2.student_id
    join semesters s3 on s3.id = a3.semester_id and s3.sort_order <= s2.sort_order
    where a2.semester_id = p_semester_id
    group by a2.student_id, a2.semester_id
  ) x
  where ar.student_id = x.student_id and ar.semester_id = x.semester_id;

  return n;
end $$;

revoke execute on function compute_semester_records(bigint) from public, anon, authenticated;
grant  execute on function compute_semester_records(bigint) to service_role;

-- Ringkasan kelengkapan nilai per semester (untuk layar Admin)
create or replace view semester_completeness as
select ca.semester_id,
       ca.course_id,
       ca.lecturer_id,
       count(e.id)                                             as total_students,
       count(cg.id) filter (where cg.status = 'final')         as final_grades,
       (count(e.id) > 0 and count(e.id) = count(cg.id) filter (where cg.status = 'final')) as is_complete
from course_assignments ca
left join enrollments e
       on e.course_id = ca.course_id and e.semester_id = ca.semester_id
left join course_grades cg on cg.enrollment_id = e.id
group by ca.semester_id, ca.course_id, ca.lecturer_id;

-- Isi nilai aktual pada prediksi saat IP semester sasaran tersedia
create or replace function link_actual_ip() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  update predictions
  set actual_ip = new.semester_gpa
  where student_id = new.student_id
    and target_semester_id = new.semester_id;
  return new;
end $$;

create trigger trg_link_actual_ip
after insert or update of semester_gpa on academic_records
for each row execute function link_actual_ip();

-- Nilai final terkunci: tidak bisa diubah kecuali oleh Admin
create or replace function lock_final_grade() returns trigger
language plpgsql as $$
begin
  if old.status = 'final' and coalesce(auth_role()::text, '') <> 'admin' then
    raise exception 'Nilai sudah final. Perubahan hanya dapat dilakukan oleh Admin.';
  end if;
  new.updated_at := now();
  if new.status = 'final' and old.status <> 'final' then
    new.finalized_at := now();
  end if;
  return new;
end $$;

create trigger trg_lock_final_grade
before update on course_grades
for each row execute function lock_final_grade();

-- Audit otomatis
create or replace function log_audit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into audit_logs (actor_id, action, table_name, record_id, old_data, new_data)
  values (
    auth.uid(), tg_op, tg_table_name,
    coalesce((to_jsonb(new) ->> 'id'), (to_jsonb(old) ->> 'id')),
    case when tg_op in ('UPDATE', 'DELETE') then to_jsonb(old) end,
    case when tg_op in ('INSERT', 'UPDATE') then to_jsonb(new) end
  );
  return coalesce(new, old);
end $$;

create trigger audit_course_grades after insert or update or delete on course_grades
  for each row execute function log_audit();
create trigger audit_students after insert or update or delete on students
  for each row execute function log_audit();
create trigger audit_course_assignments after insert or update or delete on course_assignments
  for each row execute function log_audit();
create trigger audit_model_versions after insert or update or delete on model_versions
  for each row execute function log_audit();

-- =====================================================================
-- ROW LEVEL SECURITY
-- Backend FastAPI memakai service role untuk proses sistem (hitung IP, prediksi).
-- Kunci service role TIDAK boleh ada di frontend atau repositori Git.
-- =====================================================================
alter table profiles            enable row level security;
alter table academic_programs   enable row level security;
alter table students            enable row level security;
alter table semesters           enable row level security;
alter table courses             enable row level security;
alter table grade_scale         enable row level security;
alter table course_assignments  enable row level security;
alter table enrollments         enable row level security;
alter table course_grades       enable row level security;
alter table academic_records    enable row level security;
alter table model_versions      enable row level security;
alter table predictions         enable row level security;
alter table audit_logs          enable row level security;

-- profiles
create policy profiles_self  on profiles for select using (id = auth.uid() or auth_role() = 'admin');
create policy profiles_admin on profiles for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');

-- Data master: semua pengguna login boleh membaca, hanya Admin yang boleh mengubah
create policy read_programs  on academic_programs for select to authenticated using (true);
create policy admin_programs on academic_programs for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy read_semesters on semesters for select to authenticated using (true);
create policy admin_semesters on semesters for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy read_courses   on courses for select to authenticated using (true);
create policy admin_courses  on courses for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy read_scale     on grade_scale for select to authenticated using (true);
create policy admin_scale    on grade_scale for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');

-- students
create policy students_admin on students for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy students_self  on students for select using (profile_id = auth.uid());
create policy students_dosen on students for select
  using (auth_role() = 'dosen' and dosen_can_see_student(id));

-- course_assignments
create policy assign_admin on course_assignments for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy assign_dosen on course_assignments for select using (lecturer_id = auth.uid());

-- enrollments
create policy enroll_admin on enrollments for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy enroll_self  on enrollments for select using (is_own_student(student_id));
create policy enroll_dosen on enrollments for select
  using (auth_role() = 'dosen' and exists (
    select 1 from course_assignments ca
    where ca.course_id = enrollments.course_id
      and ca.semester_id = enrollments.semester_id
      and ca.lecturer_id = auth.uid()));

-- course_grades: dosen hanya untuk mata kuliah yang diampunya, dan hanya saat masih draf
create policy grades_admin on course_grades for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy grades_dosen_select on course_grades for select
  using (auth_role() = 'dosen' and dosen_teaches_enrollment(enrollment_id));
create policy grades_dosen_insert on course_grades for insert
  with check (auth_role() = 'dosen' and dosen_teaches_enrollment(enrollment_id));
create policy grades_dosen_update on course_grades for update
  using (auth_role() = 'dosen' and dosen_teaches_enrollment(enrollment_id) and status = 'draft')
  with check (auth_role() = 'dosen' and dosen_teaches_enrollment(enrollment_id));
create policy grades_self on course_grades for select
  using (status = 'final' and exists (
    select 1 from enrollments e where e.id = course_grades.enrollment_id and is_own_student(e.student_id)));

-- academic_records
create policy records_admin on academic_records for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy records_self  on academic_records for select using (is_own_student(student_id));
create policy records_dosen on academic_records for select
  using (auth_role() = 'dosen' and dosen_can_see_student(student_id));

-- model_versions: semua pengguna login boleh membaca versi aktif, Admin mengelola
create policy model_admin on model_versions for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy model_read  on model_versions for select to authenticated using (is_active);

-- predictions
create policy pred_admin on predictions for all
  using (auth_role() = 'admin') with check (auth_role() = 'admin');
create policy pred_dosen_select on predictions for select
  using (auth_role() = 'dosen' and dosen_can_see_student(student_id));
create policy pred_dosen_update on predictions for update
  using (auth_role() = 'dosen' and dosen_can_see_student(student_id))
  with check (auth_role() = 'dosen' and dosen_can_see_student(student_id));
create policy pred_self on predictions for select
  using (exists (
    select 1 from students s
    where s.id = predictions.student_id and s.profile_id = auth.uid() and s.show_prediction));

-- audit_logs: hanya Admin yang boleh membaca
create policy audit_admin on audit_logs for select using (auth_role() = 'admin');

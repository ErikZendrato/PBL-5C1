alter table public.academic_records
  add column if not exists age integer,
  add column if not exists admission_grade numeric,
  add column if not exists previous_qualification_grade numeric,
  add column if not exists gpa_semester_1 numeric,
  add column if not exists attendance_rate numeric,
  add column if not exists assignments_submitted_rate numeric,
  add column if not exists library_visits_per_month integer,
  add column if not exists lms_logins_per_week numeric,
  add column if not exists weekly_work_hours numeric,
  add column if not exists missed_deadlines integer,
  add column if not exists commute_time_mins numeric,
  add column if not exists sleep_hours numeric,
  add column if not exists course_type text,
  add column if not exists study_mode text;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_age_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_age_range check (age between 15 and 30);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_admission_grade_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_admission_grade_range
      check (admission_grade between 5.5 and 200);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_previous_qualification_grade_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_previous_qualification_grade_range
      check (previous_qualification_grade between 30.2 and 200);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_gpa_semester_1_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_gpa_semester_1_range
      check (gpa_semester_1 between 0 and 4);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_attendance_rate_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_attendance_rate_range
      check (attendance_rate between 0 and 100);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_assignments_submitted_rate_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_assignments_submitted_rate_range
      check (assignments_submitted_rate between 0 and 100);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_library_visits_per_month_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_library_visits_per_month_range
      check (library_visits_per_month between 0 and 30);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_lms_logins_per_week_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_lms_logins_per_week_range
      check (lms_logins_per_week between 0 and 29.6);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_weekly_work_hours_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_weekly_work_hours_range
      check (weekly_work_hours between 0 and 40);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_missed_deadlines_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_missed_deadlines_range
      check (missed_deadlines between 0 and 20);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_commute_time_mins_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_commute_time_mins_range
      check (commute_time_mins between 0 and 120);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_sleep_hours_range'
  ) then
    alter table public.academic_records
      add constraint academic_records_sleep_hours_range
      check (sleep_hours between 4 and 10);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_course_type_known'
  ) then
    alter table public.academic_records
      add constraint academic_records_course_type_known
      check (course_type in (
        'Arts & Humanities',
        'Business',
        'Health Sciences',
        'Law & Social Sciences',
        'STEM'
      ));
  end if;

  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.academic_records'::regclass
      and conname = 'academic_records_study_mode_known'
  ) then
    alter table public.academic_records
      add constraint academic_records_study_mode_known
      check (study_mode in ('Full-time', 'Online', 'Part-time'));
  end if;
end
$$;

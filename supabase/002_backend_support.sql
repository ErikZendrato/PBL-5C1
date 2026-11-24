-- Jalankan SETELAH 001_schema.sql
-- Backend memakai service role (auth.uid() kosong), jadi koreksi nilai final oleh Admin
-- dilakukan lewat fungsi khusus yang hanya bisa dipanggil service role.

create or replace function lock_final_grade() returns trigger
language plpgsql as $$
begin
  if old.status = 'final'
     and coalesce(current_setting('app.override', true), '') <> '1'
     and coalesce(auth_role()::text, '') <> 'admin' then
    raise exception 'Nilai sudah final. Perubahan hanya dapat dilakukan oleh Admin.';
  end if;
  new.updated_at := now();
  if new.status = 'final' and old.status <> 'final' then
    new.finalized_at := now();
  end if;
  return new;
end $$;

create or replace function admin_override_grade(p_enrollment_id bigint, p_letter text, p_actor uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
  perform set_config('app.override', '1', true);
  update course_grades
     set letter = p_letter, status = 'final', entered_by = p_actor
   where enrollment_id = p_enrollment_id;
  if not found then
    insert into course_grades (enrollment_id, letter, status, entered_by, finalized_at)
    values (p_enrollment_id, p_letter, 'final', p_actor, now());
  end if;
end $$;

revoke execute on function admin_override_grade(bigint, text, uuid) from public, anon, authenticated;
grant  execute on function admin_override_grade(bigint, text, uuid) to service_role;

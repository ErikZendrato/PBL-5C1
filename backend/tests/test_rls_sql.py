from pathlib import Path


MIGRATION = Path(__file__).parents[2] / "supabase" / "migrations" / "202611080001_academic_prediction.sql"


def test_rls_covers_student_and_dosen_boundaries():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "s.dosen_wali_id = auth.uid()" in sql
    assert "s.profile_id = auth.uid()" in sql
    assert "public.is_admin()" in sql
    assert "dosen_id = auth.uid()" in sql

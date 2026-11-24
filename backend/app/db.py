from functools import lru_cache

from supabase import create_client

from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL


@lru_cache
def get_db():
    """Klien Supabase dengan service role. Hak akses ditegakkan di backend (deps.py)."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

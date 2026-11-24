import csv
import io

from fastapi import UploadFile

from .db import get_db


def fetch_all(table: str, select: str = "*", **eq):
    """Ambil semua baris (PostgREST membatasi 1000 baris per permintaan)."""
    out, start = [], 0
    while True:
        q = get_db().table(table).select(select)
        for k, v in eq.items():
            q = q.eq(k, v)
        rows = q.range(start, start + 999).execute().data
        out += rows
        if len(rows) < 1000:
            return out
        start += 1000


def one(x):
    """Relasi satu-ke-satu bisa kembali sebagai dict atau list berisi satu dict."""
    if isinstance(x, list):
        return x[0] if x else None
    return x


def chunks(lst, n=500):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def read_csv(file: UploadFile) -> list[dict]:
    raw = (await file.read()).decode("utf-8-sig")
    first = raw.splitlines()[0] if raw.strip() else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(raw), delimiter=delim)
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in reader]

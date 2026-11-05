from backend.database import supabase

try:
    response = (
        supabase.table("predictions")
        .select("id")
        .limit(1)
        .execute()
    )

    print("Koneksi Supabase berhasil!")
    print("Data:", response.data)

except Exception as error:
    print("Koneksi Supabase gagal!")
    print(error)
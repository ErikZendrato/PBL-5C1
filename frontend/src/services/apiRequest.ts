import { supabase } from "../lib/supabase";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();
  if (sessionError) throw sessionError;
  if (!session) throw new Error("Sesi masuk berakhir. Silakan masuk kembali.");

  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  const payload = (await response.json()) as
    | T
    | { detail?: string | { pesan?: string } };
  if (!response.ok) {
    const detail = "detail" in payload ? payload.detail : undefined;
    throw new Error(
      typeof detail === "string"
        ? detail
        : (detail?.pesan ?? "Permintaan belum berhasil. Coba lagi."),
    );
  }
  return payload as T;
}

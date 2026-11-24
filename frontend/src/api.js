import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function api(path, { method = "GET", body, file } = {}) {
  const { data } = await supabase.auth.getSession();
  const headers = {};
  if (data.session) headers.Authorization = `Bearer ${data.session.access_token}`;
  let payload;
  if (file) {
    payload = new FormData();
    payload.append("file", file);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, { method, headers, body: payload });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch { /* abaikan */ }
    throw new Error(msg);
  }
  return res.json();
}

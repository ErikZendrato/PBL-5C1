# Frontend

React, Vite, TypeScript, React Router, TanStack Query, Supabase Auth, dan Recharts.

## Konfigurasi

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, dan `VITE_API_URL`.
Jangan menempatkan service role key pada variabel frontend.

## Build

```powershell
npm run build
npm run preview
```

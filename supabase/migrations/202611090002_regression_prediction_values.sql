alter table public.predictions
  add column if not exists nilai_prediksi numeric,
  add column if not exists batas_bawah numeric,
  add column if not exists batas_atas numeric,
  alter column probabilitas drop not null;

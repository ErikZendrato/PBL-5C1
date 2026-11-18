-- Seed versi model hasil pelatihan train_v2.py; jalankan secara manual setelah ditinjau.
insert into public.model_versions (versi, algoritma, metrik, tanggal)
values ('v2.1-kaggle', 'LinearRegression', '{"mae":0.3197907134312804,"r2":0.69102662505606,"rmse":0.39978101687024753}'::jsonb, '2026-11-09')
on conflict (versi) do update set
  algoritma = excluded.algoritma,
  metrik = excluded.metrik,
  tanggal = excluded.tanggal;

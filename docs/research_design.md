# Rancangan Penelitian (template, isi bertahap)

## 1. Latar belakang singkat
Data center AI meningkat pesat; dampak panasnya ke lingkungan sekitar belum banyak diukur. Paper acuan (Marinoni et al., 2026, arXiv:2603.20897) memakai LST satelit untuk mengusulkan "data heat island effect".

## 2. Rumusan masalah
- (isi) contoh: Berapa perubahan LST di sekitar data center setelah mulai beroperasi di [ROI]?

## 3. Tujuan
- Kuantifikasi kenaikan LST setelah operasi data center
- Wilayah pengaruh (jarak) dari data center
- (opsional) estimasi penduduk terdampak

## 4. Area studi dan rentang waktu
- ROI: (isi)  - Rentang waktu: (isi)

## 5. Data
Lihat docs/data_inventory.md.

## 6. Persamaan (dari paper acuan)
- Persamaan (1): Delta_i(k) = T_i - (1/k) * sum_{j=1..k} T_{i-j}
  Pada paper, baseline adalah rata-rata LST k bulan sebelum mulai operasi (k=60 untuk grafik, k=120 untuk 10 tahun). Interpretasi ini dipakai di code/pipeline.py.
- Persamaan (2): sama, tetapi T dirata-rata pada titik berjarak r km dari data center (r = 0..10 km). Belum diimplementasikan (tahap berikutnya).

## 7. Metode prapemrosesan
Masking kualitas MODIS, agregasi bulanan, hapus seasonality (klimatologi bulanan dari periode sebelum operasi), buang outlier (MAD), hanya data center di luar area padat penduduk.

## 8. Parameter
| Parameter | Nilai awal | Alasan |
|---|---|---|
| k (bulan baseline) | 60 | mengikuti Gambar 2 paper acuan |
| radius titik pusat | 1 km | piksel MODIS 1 km |
| ambang outlier | robust z 3.5 | umum dipakai, perlu dievaluasi |
| ambang area padat | 50.000 jiwa dalam 5 km | ASUMSI sementara, paper tidak menyebut angkanya |

## 9. Evaluasi
(isi) contoh: bandingkan rata-rata kenaikan dengan 2,07 C di paper acuan; uji dengan area kontrol tanpa data center.

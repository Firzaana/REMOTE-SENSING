# code/ - pipeline gabungan

Satu file: `pipeline.py` (pengumpulan + prapemrosesan + persamaan 1).

## Setup
```
pip install -r requirements.txt
earthengine authenticate
```
Isi `EE_PROJECT` di bagian CFG pada pipeline.py dengan project Google Cloud Anda.

## Urutan jalan
1. Siapkan `data/raw/datacenters.csv` (format: lihat datacenters_template.csv; start_date = YYYY-MM-DD mulai operasi). Data DataCenterMap harus disiapkan manual, cek lisensinya.
2. `python pipeline.py locations`  - validasi dan filter area padat penduduk
3. `python pipeline.py collect`    - ekstraksi LST bulanan dari GEE
4. `python pipeline.py preprocess` - bersihkan (seasonality, outlier)
5. `python pipeline.py delta`      - hitung persamaan (1), ringkasan ke results/tables
6. `python test_synthetic.py`      - uji logika preprocess+delta dengan data sintetis (tanpa GEE)

## Asumsi yang perlu Anda putuskan
- LST: MOD11A2 1 km (di GEE), bukan LST rekonstruksi 500 m milik paper acuan.
- Ambang "area padat penduduk": 50.000 jiwa dalam 5 km (WorldPop 2020). Paper tidak menyebut angkanya.
- Baseline persamaan (1): k bulan sebelum mulai operasi.
- Kode ini belum dijalankan terhadap GEE sungguhan (butuh autentikasi Anda); bagian preprocess dan delta sudah diuji dengan data sintetis.

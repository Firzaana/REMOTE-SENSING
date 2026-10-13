# Inventaris Data

| Data | Sumber | Resolusi | Dipakai paper acuan | Status |
|---|---|---|---|---|
| Land Surface Temperature | MODIS MOD11A2 v061 di GEE (LST_Day_1km) | 1 km, 8 harian | Paper memakai MODIS LST rekonstruksi 500 m (Metz et al. 2014) | belum |
| Lokasi data center | DataCenterMap (paper acuan); alternatif Baxtel, datacenters.com | titik | ya | belum; cek lisensi, perlu disiapkan manual sebagai CSV |
| Populasi | WorldPop GP 100 m (GEE: WorldPop/GP/100m/pop) | 100 m | ya (di-downscale 1 km) | belum |
| Tutupan lahan / NDVI (opsional) | MODIS / Landsat | - | tidak | opsional |

Catatan: MOD11A2 di GEE (1 km) bukan data yang sama dengan LST rekonstruksi 500 m di paper acuan, jadi hasil bisa berbeda. Dokumentasikan ini di bagian metode.

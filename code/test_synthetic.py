"""Uji logika preprocess + delta dengan data sintetis (tanpa GEE)."""
import numpy as np, pandas as pd
from pipeline import preprocess_series, delta_table

rng = np.random.default_rng(0)
months = pd.period_range("2004-01", "2024-12", freq="M")
dcs, rows = [], []
for i in range(30):
    start = pd.Period("2015-01", "M") + int(rng.integers(0, 60))
    dcs.append((f"dc{i}", f"DC{i}", 0.0, 0.0, start.to_timestamp()))
    for m in months:
        v = 25 + 6 * np.sin(2 * np.pi * (m.month - 1) / 12) + rng.normal(0, 0.5)
        if m >= start: v += 2.0
        if rng.random() < 0.03: v += 15          # outlier
        if rng.random() < 0.10: v = np.nan       # data hilang
        rows.append((f"dc{i}", str(m), v))
long = pd.DataFrame(rows, columns=["dc_id", "ym", "lst"])
dc = pd.DataFrame(dcs, columns=["dc_id", "name", "lat", "lon", "start_date"])
clean = preprocess_series(long, dc)
d = delta_table(clean)
pre, post = d[d.rel_month < 0].delta.mean(), d[d.rel_month >= 1].delta.mean()
print(f"pre={pre:.2f} post={post:.2f} n_dc={d.dc_id.nunique()} outlier={int(clean.outlier.sum())}")
assert abs(pre) < 0.3 and 1.7 < post < 2.3, "Delta tidak mendekati 2 C"
print("OK")

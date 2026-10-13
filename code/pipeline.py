"""Pipeline gabungan: pengumpulan dan prapemrosesan LST (MODIS via GEE) di sekitar data center.

Subcommand: locations | collect | preprocess | delta
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, INTERIM, PROCESSED, TABLES = (
    ROOT / "data/raw", ROOT / "data/interim", ROOT / "data/processed", ROOT / "results/tables",
)

CFG = dict(
    EE_PROJECT=None,                       # isi project Google Cloud Anda
    datacenter_csv=RAW / "datacenters.csv",
    start="2004-01-01", end="2025-01-01",  # end eksklusif
    lst_collection="MODIS/061/MOD11A2", lst_band="LST_Day_1km", qc_band="QC_Day", scale_m=1000,
    center_radius_km=1.0,                  # buffer titik pusat (r=0)
    pop_collection="WorldPop/GP/100m/pop", pop_year=2020,
    dense_radius_km=5, dense_pop_threshold=50_000,   # ASUMSI, perlu diputuskan
    k_months=60, outlier_z=3.5, min_obs_per_month=3, batch=25,
    delta_window=(-10, 10),
)

# ---------------------------------------------------------------- lokasi
def load_datacenters(path: Path, cfg=CFG) -> pd.DataFrame:
    df = pd.read_csv(path)
    need = {"name", "lat", "lon", "start_date"}
    if not need <= set(df.columns):
        raise ValueError(f"CSV harus punya kolom {sorted(need)}")
    if "dc_id" not in df.columns:
        df["dc_id"] = [f"dc{i:05d}" for i in range(len(df))]
    n0 = len(df)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = df.dropna(subset=["lat", "lon", "start_date"])
    df = df[df.lat.between(-90, 90) & df.lon.between(-180, 180)]
    earliest = pd.Timestamp(cfg["start"]) + pd.DateOffset(months=cfg["k_months"])
    df = df[(df.start_date >= earliest) & (df.start_date < pd.Timestamp(cfg["end"]))]
    df = df.drop_duplicates("dc_id").reset_index(drop=True)
    print(f"lokasi valid: {len(df)} dari {n0} (butuh >= {cfg['k_months']} bulan data sebelum operasi)")
    return df


def _ee_init():
    import ee
    ee.Initialize(project=CFG["EE_PROJECT"])
    return ee


def cmd_locations(_args):
    ee = _ee_init()
    df = load_datacenters(CFG["datacenter_csv"])
    pop = (ee.ImageCollection(CFG["pop_collection"])
           .filterDate(f"{CFG['pop_year']}-01-01", f"{CFG['pop_year'] + 1}-01-01")
           .mosaic().select("population"))
    sums = {}
    for i in range(0, len(df), CFG["batch"]):
        b = df.iloc[i:i + CFG["batch"]]
        fc = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([r.lon, r.lat]).buffer(CFG["dense_radius_km"] * 1000), {"dc_id": r.dc_id})
            for r in b.itertuples()])
        out = pop.reduceRegions(fc, ee.Reducer.sum(), scale=100, tileScale=4).getInfo()
        for f in out["features"]:
            sums[f["properties"]["dc_id"]] = f["properties"].get("sum")
    df["pop_nearby"] = df.dc_id.map(sums)
    df["dense"] = df.pop_nearby.fillna(0) > CFG["dense_pop_threshold"]
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_csv(INTERIM / "datacenters_filtered.csv", index=False)
    print(f"lolos (non-dense): {(~df.dense).sum()} dari {len(df)} -> data/interim/datacenters_filtered.csv")

# ---------------------------------------------------------------- koleksi LST
def monthly_lst(ee, start, end):
    col = ee.ImageCollection(CFG["lst_collection"]).filterDate(start, end)

    def prep(img):
        good = img.select(CFG["qc_band"]).bitwiseAnd(3).eq(0)     # bit 0-1 = 0: LST bagus
        lst = img.select(CFG["lst_band"]).updateMask(good).multiply(0.02).subtract(273.15)
        return lst.rename("lst").copyProperties(img, ["system:time_start"])

    col = col.map(prep)
    s = ee.Date(start)
    n = ee.Date(end).difference(s, "month").round()
    empty = ee.Image.constant(0).rename("lst").updateMask(ee.Image.constant(0))

    def month(i):
        d0 = s.advance(ee.Number(i), "month")
        sub = col.filterDate(d0, d0.advance(1, "month"))
        img = ee.Image(ee.Algorithms.If(sub.size().gt(0), sub.mean(), empty))
        return img.set("ym", d0.format("YYYY-MM"))

    return ee.ImageCollection(ee.List.sequence(0, n.subtract(1)).map(month))


def cmd_collect(_args):
    ee = _ee_init()
    src = INTERIM / "datacenters_filtered.csv"
    if src.exists():
        df = pd.read_csv(src, parse_dates=["start_date"])
        df = df[~df.dense]
    else:
        print("PERINGATAN: datacenters_filtered.csv belum ada; filter area padat dilewati")
        df = load_datacenters(CFG["datacenter_csv"])
    col = monthly_lst(ee, CFG["start"], CFG["end"])
    stack = col.toBands().rename(ee.List(col.aggregate_array("ym")))
    rows = []
    for i in range(0, len(df), CFG["batch"]):
        b = df.iloc[i:i + CFG["batch"]]
        fc = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([r.lon, r.lat]).buffer(CFG["center_radius_km"] * 1000), {"dc_id": r.dc_id})
            for r in b.itertuples()])
        out = stack.reduceRegions(fc, ee.Reducer.mean(), scale=CFG["scale_m"], tileScale=4).getInfo()
        for f in out["features"]:
            p = f["properties"]
            for ym, v in p.items():
                if ym != "dc_id":
                    rows.append((p["dc_id"], ym, v))
        print(f"batch {i // CFG['batch'] + 1} selesai")
    long = pd.DataFrame(rows, columns=["dc_id", "ym", "lst"])
    INTERIM.mkdir(parents=True, exist_ok=True)
    long.to_csv(INTERIM / "lst_monthly.csv", index=False)
    df[["dc_id", "name", "lat", "lon", "start_date"]].to_csv(INTERIM / "datacenters_used.csv", index=False)
    print(f"{len(long)} baris -> data/interim/lst_monthly.csv (NaN = tidak ada citra bagus)")

# ---------------------------------------------------------------- prapemrosesan
def preprocess_series(long: pd.DataFrame, dcs: pd.DataFrame, cfg=CFG) -> pd.DataFrame:
    """Hapus seasonality (klimatologi bulanan dari periode SEBELUM operasi) dan outlier (MAD pada residu median bergulir).

    Klimatologi hanya dari data pra-operasi agar kenaikan setelah operasi tidak ikut terhapus.
    """
    start = dcs.assign(start_m=pd.to_datetime(dcs.start_date).dt.to_period("M")).set_index("dc_id")["start_m"]
    out = []
    for dc, g in long.groupby("dc_id"):
        if dc not in start.index:
            continue
        g = g.copy()
        g["period"] = pd.PeriodIndex(g["ym"], freq="M")
        g = g.sort_values("period")
        g["rel_month"] = (g["period"] - start[dc]).apply(lambda x: x.n)
        g["moy"] = g["period"].dt.month
        pre = g[(g.rel_month < 0) & g.lst.notna()]
        clim = pre.groupby("moy")["lst"].agg(["mean", "count"])
        clim = clim["mean"].where(clim["count"] >= cfg["min_obs_per_month"])
        g["lst_anom"] = g["lst"] - g["moy"].map(clim)
        # outlier: relatif terhadap median bergulir (lokal), agar lonjakan permanen
        # setelah operasi (sinyal yang dicari) tidak ikut dibuang
        roll = g["lst_anom"].rolling(7, center=True, min_periods=3).median()
        resid = g["lst_anom"] - roll
        mad = (resid - resid.median()).abs().median()
        if mad and mad > 0:
            z = 0.6745 * (resid - resid.median()) / mad
            g["outlier"] = (z.abs() > cfg["outlier_z"]).fillna(False)
        else:
            g["outlier"] = False
        g.loc[g.outlier, "lst_anom"] = np.nan
        g["dc_id"] = dc
        out.append(g[["dc_id", "ym", "rel_month", "lst", "lst_anom", "outlier"]])
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def cmd_preprocess(_args):
    long = pd.read_csv(INTERIM / "lst_monthly.csv")
    dcs = pd.read_csv(INTERIM / "datacenters_used.csv", parse_dates=["start_date"])
    clean = preprocess_series(long, dcs)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    clean.to_csv(PROCESSED / "lst_clean.csv", index=False)
    print(f"{clean.dc_id.nunique()} data center, outlier dibuang: {int(clean.outlier.sum())} -> data/processed/lst_clean.csv")

# ---------------------------------------------------------------- persamaan (1)
def delta_table(clean: pd.DataFrame, cfg=CFG) -> pd.DataFrame:
    """Delta_i(k) = T_i - mean(T pada k bulan sebelum mulai operasi), i = rel_month.

    Memakai anomali bebas-seasonality (lst_anom).
    """
    k, (lo, hi) = cfg["k_months"], cfg["delta_window"]
    rows = []
    for dc, g in clean.groupby("dc_id"):
        base = g[(g.rel_month < 0) & (g.rel_month >= -k)]["lst_anom"].dropna()
        if len(base) < k * 0.5:      # butuh setidaknya separuh bulan baseline
            continue
        b = base.mean()
        w = g[(g.rel_month >= lo) & (g.rel_month <= hi)]
        for r in w.itertuples():
            rows.append((dc, r.rel_month, r.lst_anom - b))
    return pd.DataFrame(rows, columns=["dc_id", "rel_month", "delta"])


def cmd_delta(_args):
    clean = pd.read_csv(PROCESSED / "lst_clean.csv")
    d = delta_table(clean)
    TABLES.mkdir(parents=True, exist_ok=True)
    d.to_csv(TABLES / "delta_lst_per_dc.csv", index=False)
    s = d.groupby("rel_month")["delta"].agg(
        mean="mean", min="min", max="max", p2_5=lambda x: x.quantile(.025), p97_5=lambda x: x.quantile(.975), n="count")
    s.to_csv(TABLES / "delta_lst_summary.csv")
    post = d[d.rel_month >= 1].delta.mean()
    print(f"rata-rata Delta setelah operasi: {post:.2f} C dari {d.dc_id.nunique()} data center (paper acuan: sekitar 2,07 C)")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd", choices=["locations", "collect", "preprocess", "delta"])
    a = p.parse_args()
    {"locations": cmd_locations, "collect": cmd_collect, "preprocess": cmd_preprocess, "delta": cmd_delta}[a.cmd](a)


if __name__ == "__main__":
    main()

"""
05_merge_and_process.py

Merges all five raw sources into one monthly panel, ready for regression.

FREQUENCY DECISION: monthly. Energy (Henry Hub) and CPI are already
monthly natively. Weather and FX aggregate cleanly into monthly
means/sums. USDA prices have enough reports per market/commodity per
month to compute a real monthly average (not too sparse). Production
(StatCan) is only ANNUAL -- spread evenly across each year's 12 months
as a proxy; this is a documented limitation, not true monthly production,
and is flagged in the thesis limitations section.

INPUT FILES (from raw_data/, produced by scripts 00-04):
  usda_prices_raw.csv, weather_raw.csv, energy_raw.csv,
  fx_cpi_raw.csv, statcan_greenhouse_production_raw.csv

OUTPUT:
  processed_data/monthly_panel.csv -- one row per (market, commodity, month)

DEDUPLICATION: raw price data can contain near-duplicates from interrupted
fetch/retry runs (see pipeline/dedupe_raw.py) -- this script re-applies
the same natural-key dedup before aggregating, so it's safe even if the
raw file wasn't manually deduped first.
"""

import os
import pandas as pd
import numpy as np

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
OUTPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")

DATE_START = "2001-01-01"
DATE_END = "2025-12-31"

# Maps growing-region weather to the terminal markets it's most relevant to.
# Ontario/Leamington supplies Chicago and Detroit most directly; Maine
# (Backyard Farms) supplies Boston and New York.
MARKET_TO_GROWING_REGION = {
    "chicago": "ontario_leamington",
    "detroit": "ontario_leamington",
    "boston": "maine_backyard_farms",
    "new_york": "maine_backyard_farms",
}


def load_prices():
    path = os.path.join(RAW_DATA_DIR, "usda_prices_raw.csv")
    df = pd.read_csv(path, low_memory=False)

    dedupe_key = [
        "report_date", "region", "commodity_query",
        "origin", "district", "variety", "package", "item_size",
        "low_price", "high_price",
    ]
    dedupe_key = [c for c in dedupe_key if c in df.columns]
    df = df.drop_duplicates(subset=dedupe_key)

    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    df = df.dropna(subset=["report_date"])
    df = df[(df["report_date"] >= DATE_START) & (df["report_date"] <= DATE_END)]

    # Price midpoint per line item, then monthly average per market/commodity
    df["price_mid"] = (df["low_price"] + df["high_price"]) / 2
    df["month"] = df["report_date"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        df.groupby(["month", "region", "commodity_query"])
        .agg(
            avg_price=("price_mid", "mean"),
            price_std=("price_mid", "std"),
            n_listings=("price_mid", "count"),
            pct_greenhouse=("environment", lambda x: (x.astype(str).str.contains("Greenhouse", case=False, na=False)).mean()),
        )
        .reset_index()
        .rename(columns={"region": "market", "commodity_query": "commodity"})
    )
    return monthly


def load_weather():
    path = os.path.join(RAW_DATA_DIR, "weather_raw.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[(df["date"] >= DATE_START) & (df["date"] <= DATE_END)]
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        df.groupby(["month", "region"])
        .agg(
            tmax_c_mean=("tmax_c", "mean"),
            tmin_c_mean=("tmin_c", "mean"),
            precip_mm_sum=("precip_mm", "sum"),
            sunshine_hours_sum=("sunshine_seconds", lambda x: x.sum() / 3600),
        )
        .reset_index()
        .rename(columns={"region": "growing_region"})
    )
    return monthly


def load_energy():
    path = os.path.join(RAW_DATA_DIR, "energy_raw.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[(df["date"] >= DATE_START) & (df["date"] <= DATE_END)]
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df[["month", "henry_hub_gas_price_usd_mmbtu"]]


def load_fx_cpi():
    path = os.path.join(RAW_DATA_DIR, "fx_cpi_raw.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[(df["date"] >= DATE_START) & (df["date"] <= DATE_END)]
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    monthly_fx = (
        df.groupby("month")
        .agg(usd_cad_mean=("usd_cad", "mean"), usd_mxn_mean=("usd_mxn", "mean"))
        .reset_index()
    )
    # CPI is already monthly -- take the one non-null value per month
    cpi = df.dropna(subset=["us_cpi_food"])[["month", "us_cpi_food"]].drop_duplicates(subset="month")
    return monthly_fx.merge(cpi, on="month", how="left")


def load_production():
    path = os.path.join(RAW_DATA_DIR, "statcan_greenhouse_production_raw.csv")
    df = pd.read_csv(path, low_memory=False)

    # Only need Production and Area harvested for the supply-side signal
    df = df[df["Production and value"].isin(["Production", "Area harvested"])]
    df["year"] = df["REF_DATE"].astype(int)
    df = df[(df["year"] >= 2001) & (df["year"] <= 2025)]

    # Simplify commodity labels to match usda_prices commodity_query values
    df["commodity"] = df["Commodity"].str.extract(r"Fresh (\w+)")[0].str.capitalize()

    pivoted = df.pivot_table(
        index=["year", "commodity"], columns="Production and value", values="VALUE", aggfunc="first"
    ).reset_index()
    pivoted.columns.name = None
    pivoted = pivoted.rename(columns={"Production": "annual_production", "Area harvested": "annual_area_harvested"})

    # Spread annual value evenly across 12 months of that year (documented
    # limitation -- true monthly production isn't published)
    rows = []
    for _, row in pivoted.iterrows():
        for m in range(1, 13):
            rows.append({
                "month": pd.Timestamp(year=int(row["year"]), month=m, day=1),
                "commodity": row["commodity"],
                "annual_production": row.get("annual_production"),
                "annual_area_harvested": row.get("annual_area_harvested"),
            })
    return pd.DataFrame(rows)


def main():
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

    print("Loading and aggregating each source to monthly...", flush=True)
    prices = load_prices()
    weather = load_weather()
    energy = load_energy()
    fx_cpi = load_fx_cpi()
    production = load_production()

    print(f"  prices: {len(prices)} rows (market x commodity x month)", flush=True)
    print(f"  weather: {len(weather)} rows (growing_region x month)", flush=True)
    print(f"  energy: {len(energy)} rows (month)", flush=True)
    print(f"  fx_cpi: {len(fx_cpi)} rows (month)", flush=True)
    print(f"  production: {len(production)} rows (commodity x month)", flush=True)

    # Start from prices (the DV), attach growing-region weather per market
    panel = prices.copy()
    panel["growing_region"] = panel["market"].map(MARKET_TO_GROWING_REGION)
    panel = panel.merge(weather, on=["month", "growing_region"], how="left")

    # Attach month-level series (same value across all markets/commodities that month)
    panel = panel.merge(energy, on="month", how="left")
    panel = panel.merge(fx_cpi, on="month", how="left")

    # Attach commodity-level annual production (spread monthly). Normalize
    # both sides to a base commodity word before joining -- USDA's price
    # data uses "Peppers, Bell Type" (needed to get real API results, see
    # 00_fetch_prices_usda.py) but StatCan's production table just says
    # "Peppers". A raw lowercase match would silently fail for every
    # Peppers row (confirmed: this caused annual_production/area_harvested
    # to go from 0/576 missing to 1180/1756 missing when Peppers was added).
    def base_commodity(name):
        return str(name).split(",")[0].strip().lower()

    panel["commodity_lower"] = panel["commodity"].apply(base_commodity)
    production["commodity_lower"] = production["commodity"].apply(base_commodity)
    panel = panel.merge(
        production.drop(columns=["commodity"]), on=["month", "commodity_lower"], how="left"
    )
    panel = panel.drop(columns=["commodity_lower"])

    panel = panel.sort_values(["market", "commodity", "month"])
    panel.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved {len(panel)} rows to {OUTPUT_PATH}", flush=True)
    print(f"Columns: {list(panel.columns)}", flush=True)
    print(f"\nMissing-value check:\n{panel.isna().sum()}", flush=True)


if __name__ == "__main__":
    main()
"""
04d_fetch_diesel_foodservice.py

Pulls two more candidate IVs via FRED (reusing the existing FRED_API_KEY):

  1. diesel_price_usd_gal -- US diesel retail price. Captures the
     transportation-cost leg (trucking produce from greenhouse to
     terminal market) that's been a known gap since early in this
     project. Structurally distinct from natural gas price/carbon tax
     (diesel and gas don't move in lockstep the way the two heating-cost
     variables did), so has a real chance of surviving VIF rather than
     just re-splitting credit with total_gas_cost_usd_mmbtu.

  2. foodservice_sales -- US retail sales, food services & drinking
     places (restaurants). A DIRECT test of the mechanism hypothesized
     for the covid_disruption dummy's negative coefficient (restaurant
     closures crushing demand) instead of relying on a blunt on/off flag.

Output: raw_data/diesel_foodservice_raw.csv
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "diesel_foodservice_raw.csv")

DATE_START = "2001-01-01"
DATE_END = "2025-12-31"

# GASDESW: US No 2 Diesel Retail Prices, weekly
# RSFSDP: Retail Sales: Food Services and Drinking Places, monthly
FRED_SERIES = {
    "diesel_price_usd_gal": "GASDESW",
    "foodservice_sales": "RSFSDP",
}


def get_client():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        print("ERROR: FRED_API_KEY not found in .env")
        sys.exit(1)
    return Fred(api_key=key)


def fetch_series(fred, series_id, column_name):
    print(f"Fetching {series_id} ({column_name})...", flush=True)
    try:
        series = fred.get_series(series_id, observation_start=DATE_START, observation_end=DATE_END)
    except Exception as e:
        print(f"  ERROR fetching {series_id}: {e}", flush=True)
        print(f"  This series ID may be wrong -- search fred.stlouisfed.org for the correct one.", flush=True)
        return None
    df = series.reset_index()
    df.columns = ["date", column_name]
    print(f"  {len(df)} rows fetched", flush=True)
    return df


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    fred = get_client()

    dfs = []
    for col_name, series_id in FRED_SERIES.items():
        df = fetch_series(fred, series_id, col_name)
        if df is not None:
            df["date"] = pd.to_datetime(df["date"])
            dfs.append(df)

    if not dfs:
        print("No series fetched successfully.", flush=True)
        return

    merged = dfs[0]
    for df in dfs[1:]:
        merged = merged.merge(df, on="date", how="outer")
    merged = merged.sort_values("date")
    merged.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved {len(merged)} rows to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()

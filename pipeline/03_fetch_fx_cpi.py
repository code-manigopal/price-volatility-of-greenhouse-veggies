"""
03_fetch_fx_cpi.py

Pulls currency and inflation data, all via FRED:
- USD/CAD daily exchange rate (DEXCAUS)
- USD/MXN daily exchange rate (DEXMXUS) -- Mexico competes directly with
  Ontario greenhouse produce in the same US market
- US CPI, Food (CPIUFDSL) -- general food-price inflation trend to control for

WHY FRED FOR USD/CAD TOO (not Bank of Canada directly): Bank of Canada
discontinued their "noon rate" series (IEXE0101) on 2017-04-28 and replaced
it with a new "daily average" series (FXUSDCAD) starting 2017-05-01 -- a
real methodology change, not just a renamed series. Splicing the two
together would need a documented adjustment for the break. FRED's DEXCAUS
series covers the full 2001-2025 range as one continuous, consistently-
calculated series, avoiding that problem entirely. Same reasoning as
weather (Open-Meteo over NOAA) and energy (FRED over EIA): prefer the
single source that just works over stitching multiple with seams.

SETUP REQUIRED BEFORE RUNNING:
1. Get a free FRED key at https://fred.stlouisfed.org/docs/api/api_key.html
2. Add to .env: FRED_API_KEY=your_key_here

Output: raw_data/fx_cpi_raw.csv (overwritten each run -- small pull, no
manifest/resume machinery needed, same reasoning as 02_fetch_energy.py)
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "fx_cpi_raw.csv")

DATE_START = "2001-01-01"
DATE_END = "2025-12-31"

FRED_SERIES = {
    "usd_cad": "DEXCAUS",       # Canadian dollars per USD, daily
    "usd_mxn": "DEXMXUS",       # Mexican pesos per USD, daily
    "us_cpi_food": "CPIUFDSL",  # CPI: Food, US, monthly
}


def get_fred_client():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        print(
            "ERROR: FRED_API_KEY not found.\n"
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html, then:\n"
            "  Add FRED_API_KEY=your_key_here to .env"
        )
        sys.exit(1)
    return Fred(api_key=key)


def fetch_fred_series(fred, series_id, column_name):
    print(f"Fetching {series_id} ({column_name}) from FRED...", flush=True)
    series = fred.get_series(series_id, observation_start=DATE_START, observation_end=DATE_END)
    df = series.reset_index()
    df.columns = ["date", column_name]
    print(f"  {len(df)} rows fetched", flush=True)
    return df


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    fred = get_fred_client()

    usd_cad_df = fetch_fred_series(fred, FRED_SERIES["usd_cad"], "usd_cad")
    usd_cad_df["date"] = pd.to_datetime(usd_cad_df["date"])

    usd_mxn_df = fetch_fred_series(fred, FRED_SERIES["usd_mxn"], "usd_mxn")
    usd_mxn_df["date"] = pd.to_datetime(usd_mxn_df["date"])

    cpi_df = fetch_fred_series(fred, FRED_SERIES["us_cpi_food"], "us_cpi_food")
    cpi_df["date"] = pd.to_datetime(cpi_df["date"])

    # Outer-merge on date -- daily FX series and monthly CPI won't align
    # row-for-row; 05_merge_and_process.py handles resampling to a common
    # frequency. This raw file just preserves each source at its native
    # granularity, joined loosely on date where they do overlap.
    merged = usd_cad_df.merge(usd_mxn_df, on="date", how="outer").merge(cpi_df, on="date", how="outer")
    merged = merged.sort_values("date")
    merged.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved {len(merged)} rows to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
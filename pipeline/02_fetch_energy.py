"""
02_fetch_energy.py

Pulls natural gas price data -- the main greenhouse heating cost driver --
via FRED (Federal Reserve Economic Data), not directly from EIA.

WHY FRED INSTEAD OF EIA: FRED already re-publishes EIA's Henry Hub Natural
Gas Spot Price series (MHHNGSP) under its own API. Since FRED is already
needed later for CPI and USD/MXN (see README data source plan), pulling
gas prices through the same API avoids standing up a second energy-data
integration and a second API key for one series. Same reasoning as the
weather script: prefer the simpler, already-reliable source.

SETUP REQUIRED BEFORE RUNNING:
1. Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html
2. Add to .env: FRED_API_KEY=your_key_here

LIMITATION: FRED's Henry Hub series is MONTHLY, not daily -- fine for this
thesis since the price/weather data will be aggregated to weekly/monthly
anyway in 05_merge_and_process.py. Regional Ontario/US electricity and
diesel prices are NOT on FRED and don't have a clean free API; noted as a
known gap (see README) rather than force-fit through a shakier source.

Output: raw_data/energy_raw.csv (overwritten each run -- this is a single
small pull, not worth the manifest/resume machinery used for the larger
price and weather pulls)
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "energy_raw.csv")

# FRED series id for EIA's Henry Hub Natural Gas Spot Price (monthly, $/MMBtu)
SERIES_ID = "MHHNGSP"
DATE_START = "2001-01-01"
DATE_END = "2025-12-31"


def get_client():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        print(
            "ERROR: FRED_API_KEY not found.\n"
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html, then:\n"
            "  Add FRED_API_KEY=your_key_here to .env"
        )
        sys.exit(1)
    return Fred(api_key=key)


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    fred = get_client()

    print(f"Fetching {SERIES_ID} (Henry Hub Natural Gas Spot Price)...", flush=True)
    series = fred.get_series(SERIES_ID, observation_start=DATE_START, observation_end=DATE_END)

    df = series.reset_index()
    df.columns = ["date", "henry_hub_gas_price_usd_mmbtu"]
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df)} rows to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()

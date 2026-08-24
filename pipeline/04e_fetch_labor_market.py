"""
04h_fetch_labor_market.py

Pulls Canada's unemployment rate via FRED -- a proxy for LABOR
AVAILABILITY, not labor cost (which ontario_min_wage already covers).
This is a genuinely different mechanism: Ontario greenhouses depend
heavily on Canada's Seasonal Agricultural Worker Program (SAWP) for
harvest labor, and a tight overall labor market (low unemployment) can
mean fewer available workers even when crops are ready to pick.

WHY NOT SAWP WORK-PERMIT COUNTS DIRECTLY: IRCC publishes this via static
annual CSV downloads on the open data portal, not a queryable API --
annual granularity and manual-download fragility made it a worse
reliability/insight trade-off than a clean monthly FRED series. Flagged
as a known limitation: this unemployment-rate proxy captures general
labor tightness, not SAWP-specific worker availability, which would be
the more precise (but harder to source cleanly) variable.

Output: raw_data/labor_market_raw.csv
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "labor_market_raw.csv")

SERIES_ID = "LRUNTTTTCAM156S"  # Canada unemployment rate, monthly, via OECD/FRED
DATE_START = "2001-01-01"
DATE_END = "2025-12-31"


def get_client():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        print("ERROR: FRED_API_KEY not found in .env")
        sys.exit(1)
    return Fred(api_key=key)


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    fred = get_client()

    print(f"Fetching {SERIES_ID} (Canada unemployment rate)...", flush=True)
    try:
        series = fred.get_series(SERIES_ID, observation_start=DATE_START, observation_end=DATE_END)
    except Exception as e:
        print(f"  ERROR: {e} -- series ID may be wrong, search fred.stlouisfed.org to confirm", flush=True)
        return

    df = series.reset_index()
    df.columns = ["date", "canada_unemployment_rate"]
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(df)} rows to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()

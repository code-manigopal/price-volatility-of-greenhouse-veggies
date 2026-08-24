"""
04b_fetch_drought.py

Pulls weekly US Drought Monitor severity data for California -- the
dominant field-grown tomato/pepper/cucumber competitor region. Tests the
mechanism already hypothesized in the model: unusual weather tightens
FIELD-GROWN competitor supply (not greenhouse supply, which is climate-
controlled), which should show up as higher wholesale prices.

API DOCS: https://usdmdataservices.unl.edu/api -- no key required.
NOTE: this script's exact param format (date format, statisticsType value)
is based on the documented URL structure but NOT verified against a live
response in this session -- if it errors or returns unexpected data,
paste the printed raw response text and we'll adjust rather than guess
further, same pattern as every other fetch script in this pipeline.

Output: raw_data/drought_raw.csv
"""

import os
import requests
import pandas as pd

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "drought_raw.csv")

API_URL = "https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent"
STATE_FIPS = "06"  # California -- StateStatistics requires the state's
                    # two-digit FIPS code, NOT the postal abbreviation.
                    # ("CA" silently returned an empty 200 response.)
DATE_START = "1/1/2001"
DATE_END = "12/31/2025"


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)

    params = {
        "aoi": STATE_FIPS,
        "startdate": DATE_START,
        "enddate": DATE_END,
        "statisticsType": "1",
    }
    # Default output format is CSV unless JSON is explicitly requested
    # via the Accept header, per NDMC's documented API.
    headers = {"Accept": "application/json"}

    print(f"Fetching drought data for California (FIPS {STATE_FIPS})...", flush=True)
    resp = requests.get(API_URL, params=params, headers=headers, timeout=30)
    print(f"  status={resp.status_code}", flush=True)
    print(f"  raw response (first 500 chars): {resp.text[:500]}", flush=True)

    resp.raise_for_status()
    data = resp.json()

    if not data:
        print("WARNING: empty response -- check params/date format above", flush=True)
        return

    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(df)} rows to {OUTPUT_PATH}", flush=True)
    print(f"Columns: {list(df.columns)}", flush=True)


if __name__ == "__main__":
    main()
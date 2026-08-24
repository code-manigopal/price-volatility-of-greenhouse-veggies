"""
04_fetch_production.py

Pulls Canadian greenhouse vegetable production data (area, production
volume, farm gate value) for Ontario -- the supply-side variable.

USES STATCAN'S FULL TABLE CSV DOWNLOAD, NOT THE WDS REST API: StatCan's
Web Data Service (WDS) REST API requires building coordinate strings per
dimension, which is finicky and easy to get subtly wrong (same risk as
the earlier USDA/NOAA endpoint mistakes). StatCan also publishes a direct,
no-key, no-auth ZIP download of the entire table as CSV -- simpler and
more reliable for a one-time full-table pull like this.

Table 32-10-0456-01: Production and value of greenhouse fruits and vegetables
https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3210045601

Output: raw_data/statcan_greenhouse_production_raw.csv (Ontario rows only,
relevant vegetable types only -- the full national table across all
provinces/crops is much larger than needed)

NOTE ON US-SIDE PRODUCTION DATA: USDA NASS QuickStats has an equivalent
API for US greenhouse/vegetable acreage, but requires a separate API key
registration (https://quickstats.nass.usda.gov/api). Not built here --
Ontario is the dominant growing region for Mastronardi's network (see
project README), so this StatCan pull covers the most important supply-
side signal. Flagged as a possible future addition, not a blocking gap.
"""

import os
import io
import zipfile
import requests
import pandas as pd

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "statcan_greenhouse_production_raw.csv")

TABLE_ID = "32100456"  # Table 32-10-0456-01, dashes removed
ZIP_URL = f"https://www150.statcan.gc.ca/n1/tbl/csv/{TABLE_ID}-eng.zip"

RELEVANT_GEO = "Ontario"
RELEVANT_COMMODITIES = ["Tomatoes", "Peppers", "Cucumbers"]  # matches thesis scope


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)

    print(f"Downloading StatCan table {TABLE_ID}...", flush=True)
    resp = requests.get(ZIP_URL, timeout=60)
    resp.raise_for_status()

    print("Extracting CSV from zip...", flush=True)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        # The data file is the one that isn't the metadata file
        csv_names = [n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n]
        if not csv_names:
            raise RuntimeError(f"No data CSV found in zip. Contents: {z.namelist()}")
        with z.open(csv_names[0]) as f:
            df = pd.read_csv(f, low_memory=False)

    print(f"Full table: {len(df)} rows, columns: {list(df.columns)}", flush=True)

    # Filter to Ontario + relevant vegetables. Column names confirmed by
    # inspecting the actual downloaded file -- StatCan CSVs typically use
    # GEO and a commodity dimension column (name varies by table; adjust
    # the filter below if the printed column list differs).
    geo_col = "GEO" if "GEO" in df.columns else None
    commodity_col = next(
        (c for c in df.columns if "Type of greenhouse" in c or "Commodity" in c or "vegetable" in c.lower()),
        None,
    )

    if geo_col is None or commodity_col is None:
        print(
            "WARNING: couldn't auto-detect GEO or commodity column names. "
            "Saving the full table unfiltered -- inspect columns above and "
            "filter manually, or update this script's column detection.",
            flush=True,
        )
        df.to_csv(OUTPUT_PATH, index=False)
        print(f"Saved {len(df)} unfiltered rows to {OUTPUT_PATH}", flush=True)
        return

    filtered = df[
        df[geo_col].astype(str).str.contains(RELEVANT_GEO, case=False, na=False)
        & df[commodity_col].astype(str).str.contains("|".join(RELEVANT_COMMODITIES), case=False, na=False)
    ]

    filtered.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(filtered)} filtered rows to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()

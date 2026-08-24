"""
dedupe_raw.py

One-time cleanup: removes exact duplicate rows from usda_prices_raw.csv.
Duplicates happen when the fetch script gets interrupted between saving a
window's data and marking that window done in the manifest -- the next run
then re-fetches and re-appends the same window. This is a known, expected
risk of the append-then-mark-done design, not data corruption.

Run this any time after a fetch session that was interrupted, or just
before moving to 05_merge_and_process.py.
"""

import os
import pandas as pd

RAW_PATH = os.path.join(os.path.dirname(__file__), "..", "raw_data", "usda_prices_raw.csv")

# Natural key: a row is a duplicate if every one of these matches another row.
# (Excludes report_begin_date/report_end_date since those are always equal
# to report_date for daily terminal reports -- redundant for dedup purposes.)
DEDUPE_KEY = [
    "report_date", "region", "commodity_query",
    "origin", "district", "variety", "package", "item_size",
    "low_price", "high_price",
]

def main():
    print(f"Loading {RAW_PATH} ...")
    df = pd.read_csv(RAW_PATH, low_memory=False)
    before = len(df)

    key_cols = [c for c in DEDUPE_KEY if c in df.columns]
    df = df.drop_duplicates(subset=key_cols, keep="first")
    after = len(df)

    print(f"Rows before: {before}")
    print(f"Rows after:  {after}")
    print(f"Removed:     {before - after} duplicates")

    df.to_csv(RAW_PATH, index=False)
    print(f"Saved cleaned file back to {RAW_PATH}")

if __name__ == "__main__":
    main()
"""
05f_add_diesel_foodservice.py

Merges diesel price and foodservice sales into the monthly panel.
Run AFTER 05e_combine_gas_cost.py, BEFORE 06_regression.py.

Input:  processed_data/monthly_panel.csv, raw_data/diesel_foodservice_raw.csv
Output: processed_data/monthly_panel.csv (overwritten with new columns)
"""

import os
import pandas as pd

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
PANEL_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")
SOURCE_PATH = os.path.join(RAW_DATA_DIR, "diesel_foodservice_raw.csv")


def main():
    if not os.path.exists(SOURCE_PATH):
        print(f"{SOURCE_PATH} not found -- run 04d_fetch_diesel_foodservice.py first", flush=True)
        return

    panel = pd.read_csv(PANEL_PATH)
    panel["month"] = pd.to_datetime(panel["month"])

    source = pd.read_csv(SOURCE_PATH, parse_dates=["date"])
    source["month"] = source["date"].dt.to_period("M").dt.to_timestamp()

    value_cols = [c for c in source.columns if c not in ("date", "month")]
    print(f"Available columns to merge: {value_cols}", flush=True)

    monthly = source.groupby("month")[value_cols].mean().reset_index()
    panel = panel.merge(monthly, on="month", how="left")

    for col in value_cols:
        print(f"  {col}: {panel[col].isna().sum()} missing after merge", flush=True)

    panel.to_csv(PANEL_PATH, index=False)
    print(f"\nSaved updated panel to {PANEL_PATH}", flush=True)


if __name__ == "__main__":
    main()

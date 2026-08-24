"""
05j_add_labor_market.py

Merges Canada unemployment rate into the panel. Run AFTER
05i_add_oni_mexico.py, BEFORE 06_regression.py.

Input:  processed_data/monthly_panel.csv, raw_data/labor_market_raw.csv
Output: processed_data/monthly_panel.csv (overwritten with new column)
"""

import os
import pandas as pd

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
PANEL_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")
SOURCE_PATH = os.path.join(RAW_DATA_DIR, "labor_market_raw.csv")


def main():
    if not os.path.exists(SOURCE_PATH):
        print(f"{SOURCE_PATH} not found -- run 04h_fetch_labor_market.py first", flush=True)
        return

    panel = pd.read_csv(PANEL_PATH)
    panel["month"] = pd.to_datetime(panel["month"])

    source = pd.read_csv(SOURCE_PATH, parse_dates=["date"])
    source["month"] = source["date"].dt.to_period("M").dt.to_timestamp()
    monthly = source.groupby("month")["canada_unemployment_rate"].mean().reset_index()

    panel = panel.merge(monthly, on="month", how="left")
    print(f"Merged -- missing after merge: {panel['canada_unemployment_rate'].isna().sum()}", flush=True)

    panel.to_csv(PANEL_PATH, index=False)
    print(f"\nSaved updated panel to {PANEL_PATH}", flush=True)


if __name__ == "__main__":
    main()

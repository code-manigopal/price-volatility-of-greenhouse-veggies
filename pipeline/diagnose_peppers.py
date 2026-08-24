"""
diagnose_peppers.py

One-off diagnostic: every Peppers row disappears from the regression's
complete-case data, even though annual_area_harvested (the column known
to have real gaps for Tomatoes/Cucumbers in 2001-2006) is confirmed
complete for Peppers. This finds exactly which column is actually
responsible.
"""

import os
import pandas as pd

PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
INPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")

CANDIDATE_NUMERIC_IVS = [
    "tmax_c_mean", "tmin_c_mean", "precip_mm_sum", "sunshine_hours_sum",
    "henry_hub_gas_price_usd_mmbtu", "usd_cad_mean", "usd_mxn_mean",
    "us_cpi_food", "annual_production", "annual_area_harvested",
]

df = pd.read_csv(INPUT_PATH)
peppers = df[df["commodity"] == "Peppers"]

print(f"Total Peppers rows in panel: {len(peppers)}")
print(f"\nMissing count per column, Peppers rows only:")
print(peppers[["avg_price"] + CANDIDATE_NUMERIC_IVS].isna().sum())

print(f"\nFirst few Peppers rows:")
print(peppers[["month", "market", "avg_price"] + CANDIDATE_NUMERIC_IVS].head(10).to_string())
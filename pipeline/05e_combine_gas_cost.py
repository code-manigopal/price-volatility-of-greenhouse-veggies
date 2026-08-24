"""
05e_combine_gas_cost.py

Combines Henry Hub gas price and the Ontario carbon tax into ONE
"total gas cost" variable, replacing the two separate ones. This fixes
the collinearity problem where the two were splitting credit for the
same underlying "cost of heating with gas" effect -- each was
individually losing significance because they overlap so heavily.

Run AFTER 05d_add_drought_sentiment.py, BEFORE 06_regression.py.

UNIT CONVERSION: Henry Hub is USD/MMBtu; the carbon tax is CAD/GJ.
Converted to the same USD/MMBtu basis before combining:
  1. CAD/GJ -> USD/GJ: divide by usd_cad_mean (CAD per USD)
  2. USD/GJ -> USD/MMBtu: multiply by 1.055056 (1 MMBtu = 1.055056 GJ)

TRADE-OFF (documented, not hidden): combining means the model can no
longer separately report "market gas price effect" vs. "carbon tax
policy effect" -- only "total heating cost effect." This is a deliberate
choice to get a cleaner, more trustworthy coefficient at the cost of that
narrative granularity. See interview_talking_points.md for how to frame
this trade-off if asked.

Input:  processed_data/monthly_panel.csv
Output: processed_data/monthly_panel.csv (adds total_gas_cost_usd_mmbtu,
        keeps the two original columns for reference/comparison, but
        06_regression.py is updated to use only the combined one)
"""

import os
import pandas as pd

PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
PANEL_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")

GJ_PER_MMBTU = 1.055056


def main():
    df = pd.read_csv(PANEL_PATH)

    print("Converting carbon tax from CAD/GJ to USD/MMBtu...", flush=True)
    carbon_tax_usd_per_gj = df["ontario_carbon_tax_cad_per_gj"] / df["usd_cad_mean"]
    carbon_tax_usd_per_mmbtu = carbon_tax_usd_per_gj * GJ_PER_MMBTU

    print("Combining into total_gas_cost_usd_mmbtu...", flush=True)
    df["total_gas_cost_usd_mmbtu"] = df["henry_hub_gas_price_usd_mmbtu"] + carbon_tax_usd_per_mmbtu

    df.to_csv(PANEL_PATH, index=False)

    print(f"\nSaved updated panel to {PANEL_PATH}", flush=True)
    print(f"total_gas_cost_usd_mmbtu range: ${df['total_gas_cost_usd_mmbtu'].min():.2f} - ${df['total_gas_cost_usd_mmbtu'].max():.2f}", flush=True)
    print(f"(for comparison, henry_hub alone ranged ${df['henry_hub_gas_price_usd_mmbtu'].min():.2f} - ${df['henry_hub_gas_price_usd_mmbtu'].max():.2f})", flush=True)


if __name__ == "__main__":
    main()

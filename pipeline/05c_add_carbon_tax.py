"""
05c_add_carbon_tax.py

Adds Canada's federal carbon charge on natural gas ($/GJ) as a separate
variable from Henry Hub gas price. Run AFTER 05b_add_shock_variables.py
and BEFORE 06_regression.py.

WHY THIS IS LIKELY TO SURVIVE VIF (unlike ontario_min_wage, which got
dropped): Henry Hub is a continuously fluctuating US market price driven
by supply/demand. The carbon charge is a scheduled Canadian government
policy step-function, structurally unrelated to market gas price
movements -- it went up on fixed dates regardless of what Henry Hub was
doing, and was repealed to $0 in April 2025 even though Henry Hub kept
moving. That structural independence is what gives it a real chance of
adding distinct information rather than just duplicating gas price.

SOURCE: rates and effective dates confirmed directly from a natural gas
utility's own billing documentation (TransGas/SaskEnergy carbon charge
schedule), which reflects the federal backstop rate applied in provinces
(including Ontario) without their own equivalent system. Repeal date
(April 1, 2025) confirmed via Bill C-4, "Making Life More Affordable for
Canadians Act."

Input:  processed_data/monthly_panel.csv
Output: processed_data/monthly_panel.csv (overwritten with 1 new column)
"""

import os
import pandas as pd

PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
PANEL_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")

# Canada federal carbon charge on natural gas, CAD $/GJ, effective date -> rate.
CARBON_TAX_SCHEDULE = [
    ("2001-01-01", 0.00),   # didn't exist yet
    ("2019-04-01", 1.00),
    ("2020-04-01", 1.50),
    ("2021-04-01", 2.00),
    ("2022-04-01", 2.50),
    ("2023-04-01", 3.25),
    ("2024-04-01", 4.00),
    ("2025-04-01", 0.00),   # repealed -- Bill C-4, effective retroactive to Apr 1 2025
]


def build_carbon_tax_series(dates):
    schedule = pd.DataFrame(CARBON_TAX_SCHEDULE, columns=["effective_date", "rate_cad_per_gj"])
    schedule["effective_date"] = pd.to_datetime(schedule["effective_date"])
    schedule = schedule.sort_values("effective_date")

    result = []
    for d in dates:
        applicable = schedule[schedule["effective_date"] <= d]
        rate = applicable["rate_cad_per_gj"].iloc[-1] if len(applicable) else 0.0
        result.append(rate)
    return result


def main():
    df = pd.read_csv(PANEL_PATH)
    df["month_dt"] = pd.to_datetime(df["month"])

    print("Adding ontario_carbon_tax_cad_per_gj...", flush=True)
    df["ontario_carbon_tax_cad_per_gj"] = build_carbon_tax_series(df["month_dt"])

    df = df.drop(columns=["month_dt"])
    df.to_csv(PANEL_PATH, index=False)

    print(f"\nSaved updated panel with 1 new column to {PANEL_PATH}", flush=True)
    print(f"ontario_carbon_tax_cad_per_gj range: ${df['ontario_carbon_tax_cad_per_gj'].min():.2f} - ${df['ontario_carbon_tax_cad_per_gj'].max():.2f}", flush=True)
    print(f"Non-zero months: {(df['ontario_carbon_tax_cad_per_gj'] > 0).sum()} / {len(df)}", flush=True)


if __name__ == "__main__":
    main()

"""
05b_add_shock_variables.py

Adds three hand-coded, low-collinearity-risk variables to the monthly
panel, run AFTER 05_merge_and_process.py and BEFORE 06_regression.py:

  1. ontario_min_wage  -- Ontario general minimum wage ($/hr) in effect
     each month. A real labour-cost driver for greenhouse operations,
     moves independently of weather/energy/FX, so low collinearity risk.

  2. covid_disruption  -- dummy (1/0) for the acute COVID-19 supply chain
     disruption period. Cheap, near-zero collinearity risk (a step
     function structurally different from continuous IVs or monthly
     seasonality dummies), and the 25-year sample genuinely spans this
     shock, so leaving it out risks that variance leaking into the
     residual / other coefficients.

  3. tobrfv_period -- dummy (1/0) for the period since ToBRFV (Tomato
     Brown Rugose Fruit Virus) became a recognized North American
     greenhouse tomato industry concern. A genuine, documented supply
     shock specific to tomatoes.

ACCURACY NOTE: ontario_min_wage for 2009-2025 is sourced from a published
history table with internal date/rate consistency confirmed. The 2001-2008
portion is compiled from commonly-cited general knowledge of Ontario's
minimum wage freeze (1995-2003 at $6.85) and subsequent annual increases,
but was NOT independently verified against Ontario's official ESA history
page in this session -- confirm those specific years before treating them
as final in the thesis. covid_disruption and tobrfv_period date ranges are
reasonable approximations; cite specific sources for exact start dates if
using these in a formal writeup.

Input:  processed_data/monthly_panel.csv (from 05_merge_and_process.py)
Output: processed_data/monthly_panel.csv (overwritten with 3 new columns)
"""

import os
import pandas as pd

PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
PANEL_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")

# Ontario general minimum wage, $/hr, effective date -> rate.
# 2009-2025 confirmed against a published history table.
# 2001-2008 -- VERIFY against ontario.ca ESA history before final use.
MIN_WAGE_HISTORY = [
    ("2001-01-01", 6.85),   # frozen since 1995 -- VERIFY
    ("2004-02-01", 7.15),   # VERIFY
    ("2005-02-01", 7.45),   # VERIFY
    ("2006-02-01", 7.75),   # VERIFY
    ("2007-02-01", 8.00),   # VERIFY
    ("2008-02-01", 8.75),   # VERIFY (consistent with confirmed 2009 entry below)
    ("2009-03-31", 9.50),
    ("2010-03-31", 10.25),
    ("2014-06-01", 11.00),
    ("2015-10-01", 11.25),
    ("2016-10-01", 11.40),
    ("2017-10-01", 11.60),
    ("2018-01-01", 14.00),
    # 2019 scheduled increase was cancelled -- rate held at $14.00
    ("2020-10-01", 14.25),
    ("2021-10-01", 14.35),
    ("2022-01-01", 15.00),
    ("2022-10-01", 15.50),
    ("2023-10-01", 16.55),
    ("2024-10-01", 17.20),
    ("2025-10-01", 17.60),
]

COVID_START = "2020-03-01"
COVID_END = "2021-06-30"

TOBRFV_START = "2019-01-01"  # approximate -- verify exact detection/announcement date


def build_min_wage_series(dates):
    history = pd.DataFrame(MIN_WAGE_HISTORY, columns=["effective_date", "rate"])
    history["effective_date"] = pd.to_datetime(history["effective_date"])
    history = history.sort_values("effective_date")

    result = []
    for d in dates:
        applicable = history[history["effective_date"] <= d]
        rate = applicable["rate"].iloc[-1] if len(applicable) else history["rate"].iloc[0]
        result.append(rate)
    return result


def main():
    df = pd.read_csv(PANEL_PATH)
    df["month_dt"] = pd.to_datetime(df["month"])

    print("Adding ontario_min_wage...", flush=True)
    df["ontario_min_wage"] = build_min_wage_series(df["month_dt"])

    print("Adding covid_disruption dummy...", flush=True)
    df["covid_disruption"] = (
        (df["month_dt"] >= COVID_START) & (df["month_dt"] <= COVID_END)
    ).astype(int)

    print("Adding tobrfv_period dummy...", flush=True)
    df["tobrfv_period"] = (df["month_dt"] >= TOBRFV_START).astype(int)

    df = df.drop(columns=["month_dt"])
    df.to_csv(PANEL_PATH, index=False)

    print(f"\nSaved updated panel with 3 new columns to {PANEL_PATH}", flush=True)
    print(f"covid_disruption: {df['covid_disruption'].sum()} rows flagged", flush=True)
    print(f"tobrfv_period: {df['tobrfv_period'].sum()} rows flagged", flush=True)
    print(f"ontario_min_wage range: ${df['ontario_min_wage'].min():.2f} - ${df['ontario_min_wage'].max():.2f}", flush=True)


if __name__ == "__main__":
    main()

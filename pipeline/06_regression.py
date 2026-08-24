"""
06_regression.py

Runs the core regression: what drives wholesale price for greenhouse
vegetables? Follows the same methodology as the PG enrolment project --
OLS with HC3 robust standard errors, VIF-based multicollinearity
filtering, and a written summary saved alongside the numeric output.

DV: avg_price (monthly average wholesale price, market x commodity x month)
IVs (candidate set, pre-VIF-filtering):
  - tmax_c_mean, tmin_c_mean, precip_mm_sum, sunshine_hours_sum  (weather)
  - henry_hub_gas_price_usd_mmbtu                                (energy)
  - usd_cad_mean, usd_mxn_mean                                   (currency)
  - us_cpi_food                                                  (demand/inflation)
  - annual_production, annual_area_harvested                     (supply)
  - month dummies (seasonality)
  - commodity dummies (Tomatoes/Peppers/Cucumbers baseline differences)
  - market dummies (Boston/New York/Chicago/Detroit fixed effects -- controls
    for systematic price-level differences between markets, e.g. shipping
    cost, local demand, that would otherwise be absorbed into the error
    term and suppress R^2)

Input: processed_data/monthly_panel.csv
Output:
  processed_data/regression_summary.txt  -- full statsmodels summary, VIF table
  processed_data/regression_results.csv  -- coefficients/p-values as a table
"""

import os
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
INPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")
SUMMARY_PATH = os.path.join(PROCESSED_DATA_DIR, "regression_summary.txt")
RESULTS_CSV_PATH = os.path.join(PROCESSED_DATA_DIR, "regression_results.csv")

CANDIDATE_NUMERIC_IVS = [
    "tmax_c_mean", "tmin_c_mean", "precip_mm_sum", "sunshine_hours_sum",
    "total_gas_cost_usd_mmbtu",  # combined Henry Hub + carbon tax, see 05e
    "usd_cad_mean", "usd_mxn_mean",
    "us_cpi_food", "annual_production", "annual_area_harvested",
    "ontario_min_wage",
    "drought_severity_pct", "consumer_sentiment",
    "diesel_price_usd_gal", "foodservice_sales",
    # Deliberately non-trending variables (volatility/counts, not levels) --
    # see 05g_add_volatility_extremes.py and 05h_add_florida_weather.py
    "usd_cad_volatility", "extreme_heat_days", "extreme_rain_days",
    "fl_precip_sum", "fl_storm_days",
    # Genuinely new mechanisms -- see 04f_fetch_oni.py and 04g_fetch_mexico_weather.py
    "oni", "mx_freeze_days", "mx_precip_sum",
    # Labor AVAILABILITY, distinct from labor COST (ontario_min_wage) --
    # see 04h_fetch_labor_market.py
    "canada_unemployment_rate",
]

# Dummy/binary variables added by 05b_add_shock_variables.py -- kept
# separate from CANDIDATE_NUMERIC_IVS since they're already 0/1 and
# shouldn't go through VIF filtering the same way as continuous IVs
# (a dummy's VIF is naturally different in character from a continuous
# variable's; these are cheap, low-collinearity-risk additions and are
# always included rather than filtered).
SHOCK_DUMMIES = ["covid_disruption", "tobrfv_period"]

VIF_THRESHOLD = 10.0


def build_design_matrix(df):
    """Numeric IVs + month dummies + commodity dummies, all in one matrix."""
    df = df.copy()
    df["month_dt"] = pd.to_datetime(df["month"])
    df["month_num"] = df["month_dt"].dt.month

    available_ivs = [c for c in CANDIDATE_NUMERIC_IVS if c in df.columns]
    numeric = df[available_ivs].copy()

    # Rescale annual_production: raw values are on the order of 10^7-10^8
    # (kg of production), while every other variable is single/double
    # digits or a 0/1 dummy. That scale mismatch -- not genuine
    # collinearity -- is what was producing the huge condition number
    # (1.1e10) and the rank-deficiency warning on the constraint-covariance
    # matrix (confirmed: the aux-R^2 collinearity check found nothing above
    # 0.98, ruling out a real redundant variable). Rescaling to millions of
    # kg brings it in line with the other variables' magnitudes and fixes
    # the numerical conditioning without changing what the model estimates
    # (only the coefficient's units change, from $/kg to $/million-kg).
    if "annual_production" in numeric.columns:
        numeric["annual_production"] = numeric["annual_production"] / 1_000_000

    month_dummies = pd.get_dummies(df["month_num"], prefix="month", drop_first=True)
    commodity_dummies = pd.get_dummies(df["commodity"], prefix="commodity", drop_first=True)
    market_dummies = pd.get_dummies(df["market"], prefix="market", drop_first=True)
    shocks = df[SHOCK_DUMMIES].copy()

    X = pd.concat([numeric, shocks, month_dummies, commodity_dummies, market_dummies], axis=1)
    X = X.astype(float)
    return X


def drop_high_vif(X, threshold=VIF_THRESHOLD):
    """Iteratively drop the highest-VIF numeric column until all are under
    threshold. Only applies to the original numeric IVs -- dummy variables
    are expected to show elevated VIF by construction and are left alone."""
    numeric_cols = [c for c in CANDIDATE_NUMERIC_IVS if c in X.columns]
    dropped = []

    while True:
        X_numeric = X[numeric_cols]
        vifs = pd.Series(
            [variance_inflation_factor(X_numeric.values, i) for i in range(X_numeric.shape[1])],
            index=numeric_cols,
        )
        worst = vifs.idxmax()
        if vifs[worst] < threshold or len(numeric_cols) <= 1:
            break
        dropped.append((worst, vifs[worst]))
        numeric_cols.remove(worst)

    final_vifs = pd.Series(
        [variance_inflation_factor(X[numeric_cols].values, i) for i in range(len(numeric_cols))],
        index=numeric_cols,
    )
    kept_cols = numeric_cols + [c for c in X.columns if c not in CANDIDATE_NUMERIC_IVS]
    return X[kept_cols], dropped, final_vifs


def main():
    print("Loading processed panel...", flush=True)
    df = pd.read_csv(INPUT_PATH)
    available_ivs = [c for c in CANDIDATE_NUMERIC_IVS if c in df.columns]
    missing_ivs = [c for c in CANDIDATE_NUMERIC_IVS if c not in df.columns]
    if missing_ivs:
        print(f"  NOTE: these candidate IVs aren't in the panel yet, skipping: {missing_ivs}", flush=True)

    df = df.dropna(subset=["avg_price"] + available_ivs + SHOCK_DUMMIES)
    print(f"  {len(df)} complete rows after dropping any row missing an IV or the DV", flush=True)
    print(f"  Commodity counts in complete rows:\n{df['commodity'].value_counts()}", flush=True)

    y = df["avg_price"]
    X_full = build_design_matrix(df)

    print("Running VIF-based multicollinearity filtering...", flush=True)
    X_filtered, dropped, final_vifs = drop_high_vif(X_full)

    if dropped:
        print("  Dropped for high VIF:", flush=True)
        for col, vif in dropped:
            print(f"    {col}: VIF={vif:.1f}", flush=True)
    else:
        print("  Nothing dropped -- all numeric IVs under VIF threshold", flush=True)

    X_with_const = sm.add_constant(X_filtered)

    # Diagnostic: find near-collinear columns via auxiliary regression
    # (each column regressed on all the others). Not gated behind
    # np.linalg.matrix_rank -- that check uses a looser numerical tolerance
    # than statsmodels' internal one, so it can report "full rank" even
    # when statsmodels still flags a near-singular constraint matrix.
    # Always run this so near-perfect (not just exact) collinearity surfaces.
    print("\n  Checking for near-collinear columns (aux R^2 against all others)...", flush=True)
    near_collinear = []
    for col in X_with_const.columns:
        if col == "const":
            continue
        others = X_with_const.drop(columns=[col])
        aux_model = sm.OLS(X_with_const[col], others).fit()
        if aux_model.rsquared > 0.98:
            near_collinear.append((col, aux_model.rsquared))
    if near_collinear:
        for col, r2 in sorted(near_collinear, key=lambda x: -x[1]):
            print(f"    {col}: aux R^2={r2:.6f} against all other columns", flush=True)
    else:
        print("    None found above 0.98 aux R^2 threshold", flush=True)

    model = sm.OLS(y, X_with_const).fit(cov_type="HC3")

    print("\n" + "=" * 70, flush=True)
    print(model.summary(), flush=True)
    print("=" * 70, flush=True)

    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    with open(SUMMARY_PATH, "w") as f:
        f.write("REGRESSION SUMMARY -- Greenhouse Vegetable Wholesale Price Drivers\n")
        f.write(f"N = {len(df)}, R-squared = {model.rsquared:.4f}\n\n")
        f.write("VIF-DROPPED VARIABLES (multicollinearity):\n")
        for col, vif in dropped:
            f.write(f"  {col}: VIF={vif:.1f} (dropped)\n")
        f.write("\nFINAL VIF VALUES (kept numeric IVs):\n")
        f.write(final_vifs.to_string())
        f.write("\n\n" + str(model.summary()))

    results_df = pd.DataFrame({
        "coefficient": model.params,
        "std_err": model.bse,
        "p_value": model.pvalues,
        "significant_at_05": model.pvalues < 0.05,
    })
    results_df.to_csv(RESULTS_CSV_PATH)

    print(f"\nSaved full summary to {SUMMARY_PATH}", flush=True)
    print(f"Saved results table to {RESULTS_CSV_PATH}", flush=True)


if __name__ == "__main__":
    main()
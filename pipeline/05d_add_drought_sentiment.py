"""
05d_add_drought_sentiment.py

Merges drought (California, weekly -> monthly average) and consumer
sentiment (already monthly) into the panel. Run AFTER 04b/04c fetch
scripts and 05c_add_carbon_tax.py, BEFORE 06_regression.py.

NOTE ON DROUGHT COLUMN NAMES: the exact column names in drought_raw.csv
depend on the live API response, which wasn't verified in this session
(see 04b_fetch_drought.py). This script prints the actual columns it
finds and tries common candidates (D0-D4 severity percentages) rather
than assuming -- if it can't find a usable numeric column, it prints a
warning and skips drought rather than crashing or silently adding zeros.

Input:  processed_data/monthly_panel.csv, raw_data/drought_raw.csv,
        raw_data/sentiment_raw.csv
Output: processed_data/monthly_panel.csv (overwritten with new columns)
"""

import os
import pandas as pd

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "processed_data")
PANEL_PATH = os.path.join(PROCESSED_DATA_DIR, "monthly_panel.csv")
DROUGHT_PATH = os.path.join(RAW_DATA_DIR, "drought_raw.csv")
SENTIMENT_PATH = os.path.join(RAW_DATA_DIR, "sentiment_raw.csv")


def load_drought():
    if not os.path.exists(DROUGHT_PATH):
        print("drought_raw.csv not found -- skipping drought (run 04b_fetch_drought.py first)", flush=True)
        return None

    df = pd.read_csv(DROUGHT_PATH)
    print(f"Drought raw columns: {list(df.columns)}", flush=True)

    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    # D2-D4 = severe/extreme/exceptional drought; a reasonable single
    # summary severity measure. Try common USDM column name patterns.
    severity_candidates = [c for c in df.columns if any(x in c.upper() for x in ["D2", "D3", "D4"])]

    if not date_col or not severity_candidates:
        print(
            "WARNING: couldn't auto-detect date/severity columns in drought data. "
            "Inspect the columns printed above and adjust this script manually. "
            "Skipping drought for now.",
            flush=True,
        )
        return None

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df["month"] = df[date_col].dt.to_period("M").dt.to_timestamp()

    for c in severity_candidates:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    monthly = df.groupby("month")[severity_candidates].mean().reset_index()
    monthly["drought_severity_pct"] = monthly[severity_candidates].sum(axis=1)
    return monthly[["month", "drought_severity_pct"]]


def load_sentiment():
    if not os.path.exists(SENTIMENT_PATH):
        print("sentiment_raw.csv not found -- skipping (run 04c_fetch_sentiment.py first)", flush=True)
        return None
    df = pd.read_csv(SENTIMENT_PATH, parse_dates=["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df[["month", "consumer_sentiment"]].drop_duplicates(subset="month")


def main():
    panel = pd.read_csv(PANEL_PATH)
    panel["month"] = pd.to_datetime(panel["month"])

    drought = load_drought()
    if drought is not None:
        panel = panel.merge(drought, on="month", how="left")
        print(f"Merged drought -- missing after merge: {panel['drought_severity_pct'].isna().sum()}", flush=True)

    sentiment = load_sentiment()
    if sentiment is not None:
        panel = panel.merge(sentiment, on="month", how="left")
        print(f"Merged sentiment -- missing after merge: {panel['consumer_sentiment'].isna().sum()}", flush=True)

    panel.to_csv(PANEL_PATH, index=False)
    print(f"\nSaved updated panel to {PANEL_PATH}", flush=True)
    print(f"Columns: {list(panel.columns)}", flush=True)


if __name__ == "__main__":
    main()

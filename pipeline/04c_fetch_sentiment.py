"""
04c_fetch_sentiment.py

Pulls the University of Michigan Consumer Sentiment Index via FRED --
a demand-side proxy, distinct from CPI (which already got VIF-dropped).
Sentiment reflects discretionary spending mood, which can affect demand
for premium/specialty produce differently than a pure price-level index.

Reuses the FRED_API_KEY already set up for scripts 02 and 03.

Output: raw_data/sentiment_raw.csv
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "sentiment_raw.csv")

SERIES_ID = "UMCSENT"  # University of Michigan Consumer Sentiment Index, monthly
DATE_START = "2001-01-01"
DATE_END = "2025-12-31"


def get_client():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        print("ERROR: FRED_API_KEY not found in .env")
        sys.exit(1)
    return Fred(api_key=key)


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    fred = get_client()

    print(f"Fetching {SERIES_ID} (Consumer Sentiment Index)...", flush=True)
    series = fred.get_series(SERIES_ID, observation_start=DATE_START, observation_end=DATE_END)

    df = series.reset_index()
    df.columns = ["date", "consumer_sentiment"]
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df)} rows to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()

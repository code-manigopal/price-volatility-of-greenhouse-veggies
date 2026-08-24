"""
00_fetch_prices_usda.py

Pulls historical wholesale/terminal-market price line-items for tomatoes,
bell peppers, and cucumbers (including Canadian/Ontario greenhouse
listings) from the USDA AMS MyMarketNews (MARS) API.

ENDPOINT NOTES (learned the hard way -- read before changing this):
- /reports/{slug} alone returns report-level METADATA ONLY (weather notes,
  publish times) -- no price data at all.
- /reports/{slug}?...&allSections=true returns the ENTIRE day's report
  (every commodity, every section: header, details, volumes...) nested
  inside a single 'results' blob. Looping this per-commodity re-downloads
  the same multi-megabyte blob 3x per date (once per commodity query) --
  this is what produced a 1.17 GB file from a few years of data.
- The fix: hit the /Details sub-endpoint directly, which returns only
  itemized price line-items, and keep only the columns this thesis
  actually needs instead of every raw field.

    /reports/{slug}/Details?q=commodity=<Commodity>;report_begin_date=START:END

Each request is capped at ~180 days of historical data, so this script
loops through the full date range in 180-day windows per market per
commodity.

IDEMPOTENT / RESUMABLE: tracks which (region, commodity, date-window)
combinations have already been fetched in a manifest file
(raw_data/.fetch_manifest.csv). Safe to stop and rerun -- only fetches
and appends what's missing, never re-pulls or duplicates data.

SETUP REQUIRED BEFORE RUNNING:
1. Register for a free account at https://mymarketnews.ams.usda.gov
2. Log in -> click your name -> "Show API key" -> copy it
3. Copy .env.example to .env (in the project root) and paste your key in:
       USDA_MARS_API_KEY=your_key_here
   .env is gitignored, so it never gets committed.

Docs: https://mymarketnews.ams.usda.gov/mymarketnews-api

Output: raw_data/usda_prices_raw.csv (appended to, not overwritten)
Manifest: raw_data/.fetch_manifest.csv (tracks completed windows)
"""

import os
import sys
import time
import datetime
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://marsapi.ams.usda.gov/services/v1.2"
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "usda_prices_raw.csv")
MANIFEST_PATH = os.path.join(RAW_DATA_DIR, ".fetch_manifest.csv")

# NOTE: "Peppers" alone returns ZERO results from USDA's API -- there is no
# generic Peppers category. Peppers are split into sub-types (PEPPERS, BELL
# TYPE / MIXED MINI SWEET TYPES / POBLANO / THAI CHILI HOTS, etc). "Peppers,
# Bell Type" matches what Mastronardi actually grows and is confirmed
# present in sample reports across all four markets. This was a silent
# failure -- the fetch script ran successfully and logged every window as
# "done" with 0 rows each time, no error thrown.
COMMODITIES = ["Tomatoes", "Peppers, Bell Type", "Cucumbers"]

REGION_SLUGS = {
    "boston": "BH_FV020",
    "new_york": "NX_FV020",
    "chicago": "HX_FV020",
    "detroit": "DU_FV020",
}

DATE_START = datetime.date(2001, 1, 1)
DATE_END = datetime.date(2025, 12, 31)
WINDOW_DAYS = 175

# Confirmed against a live test pull (Boston/Tomatoes, Jan-Mar 2024, 745 rows).
# 'environment' is the field that flags greenhouse vs. field-grown -- important
# for isolating genuinely greenhouse-grown listings in the analysis.
KEEP_FIELDS = [
    "report_date", "report_begin_date", "report_end_date",
    "commodity", "variety", "origin", "district",
    "package", "grade", "item_size", "environment",
    "organic", "crop", "condition", "quality", "appearance",
    "low_price", "high_price", "mostly_low", "mostly_high",
    "unit_sales", "market_tone",
]


def get_api_key():
    key = os.environ.get("USDA_MARS_API_KEY")
    if not key:
        print(
            "ERROR: USDA_MARS_API_KEY not found.\n"
            "Register at https://mymarketnews.ams.usda.gov, grab your API key, then:\n"
            "  1. Copy .env.example to .env in the project root\n"
            "  2. Set USDA_MARS_API_KEY=your_key_here inside .env"
        )
        sys.exit(1)
    return key


def date_windows(start, end, window_days):
    current = start
    while current <= end:
        window_end = min(current + datetime.timedelta(days=window_days), end)
        yield current, window_end
        current = window_end + datetime.timedelta(days=1)


def load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return set()
    df = pd.read_csv(MANIFEST_PATH)
    return set(zip(df["region"], df["commodity"], df["window_start"], df["window_end"]))


def append_manifest(region, commodity, win_start, win_end, row_count):
    row = pd.DataFrame([{
        "region": region,
        "commodity": commodity,
        "window_start": win_start.isoformat(),
        "window_end": win_end.isoformat(),
        "rows_fetched": row_count,
        "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }])
    header_needed = not os.path.exists(MANIFEST_PATH)
    row.to_csv(MANIFEST_PATH, mode="a", header=header_needed, index=False)


def append_data(df):
    header_needed = not os.path.exists(OUTPUT_PATH)
    df.to_csv(OUTPUT_PATH, mode="a", header=header_needed, index=False)


def fetch_details(slug, commodity, start_date, end_date, api_key):
    """Hit the 'report details' sub-endpoint -- itemized price rows only,
    no full-report nesting. CONFIRMED WORKING: section name is literally
    two words, lowercase, with a space -- test pull returned 745 real
    price rows for Boston/Tomatoes over a 2-month window.

    Commodity values containing a comma (e.g. "Peppers, Bell Type") are
    quoted, per USDA's own documented query syntax for multi-word/
    punctuated values (their docs show location="Atlanta,+Georgia" as an
    example) -- unquoted, the comma likely gets parsed as a value
    separator instead of part of the commodity name, silently matching
    nothing (0 rows, no error) rather than failing loudly."""
    url = f"{API_BASE}/reports/{slug}/report details"
    date_str = f"{start_date.strftime('%m/%d/%Y')}:{end_date.strftime('%m/%d/%Y')}"
    commodity_value = f'"{commodity}"' if "," in commodity else commodity
    params = {"q": f"commodity={commodity_value};report_begin_date={date_str}"}
    resp = requests.get(url, auth=(api_key, ""), params=params, timeout=15)
    print(f"    URL: {resp.url}", flush=True)
    if resp.status_code == 400:
        print(f"  400 body: {resp.text[:500]}")
    resp.raise_for_status()
    data = resp.json()
    stats = data.get("stats", {}) if isinstance(data, dict) else {}
    print(f"    -> status={resp.status_code}, returnedRows={stats.get('returnedRows')}, totalRows={stats.get('totalRows')}", flush=True)
    return data


def slim_dataframe(results, region, commodity):
    """Flatten results and keep only the columns this thesis needs."""
    df = pd.json_normalize(results)
    available = [c for c in KEEP_FIELDS if c in df.columns]
    df = df[available].copy()
    df["region"] = region
    df["commodity_query"] = commodity
    return df


def main():
    api_key = get_api_key()
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    done = load_manifest()

    total_planned = total_skipped = total_fetched = total_rows = 0

    for region_name, slug in REGION_SLUGS.items():
        for commodity in COMMODITIES:
            for win_start, win_end in date_windows(DATE_START, DATE_END, WINDOW_DAYS):
                total_planned += 1
                key = (region_name, commodity, win_start.isoformat(), win_end.isoformat())
                if key in done:
                    total_skipped += 1
                    continue

                print(f"Fetching {region_name} / {commodity} / {win_start} to {win_end}...")
                try:
                    data = fetch_details(slug, commodity, win_start, win_end, api_key)
                except requests.HTTPError as e:
                    print(f"  Skipped (error, will retry next run): {e}")
                    time.sleep(1)
                    continue

                results = data.get("results", data) if isinstance(data, dict) else data
                row_count = len(results) if results else 0

                if results:
                    df = slim_dataframe(results, region_name, commodity)
                    append_data(df)
                    total_rows += row_count

                append_manifest(region_name, commodity, win_start, win_end, row_count)
                total_fetched += 1
                time.sleep(0.5)

    print(
        f"\nDone. {total_planned} windows total, {total_skipped} already done "
        f"(skipped), {total_fetched} fetched this run, {total_rows} new rows "
        f"appended to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
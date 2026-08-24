"""
01_fetch_weather.py

Pulls daily weather (max/min temperature, precipitation, sunshine) for the
growing regions relevant to Mastronardi's network -- NOT the terminal
market cities. Weather affects the SUPPLY side (greenhouse heating needs,
outdoor competitor yields), so it needs to be measured where the
vegetables are actually grown, not where they're sold.

USES OPEN-METEO (not NOAA -- NOAA's CDO API works but is slow/paginated;
see git history / earlier notes if curious). Open-Meteo's Historical
Weather API needs no key, has no meaningful rate limit, and returns the
full 25-year range in ONE request per region.
Docs: https://open-meteo.com/en/docs/historical-weather-api

Uses Open-Meteo's official client library (with built-in caching + retry)
rather than raw requests, per their documented usage pattern:
    pip install openmeteo-requests requests-cache retry-requests numpy pandas

IDEMPOTENT / RESUMABLE: tracks completed regions in
raw_data/.weather_manifest.csv -- coarse-grained here since each region is
one request, not many.

Output: raw_data/weather_raw.csv (appended to, not overwritten)
"""

import os
import sys
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")
OUTPUT_PATH = os.path.join(RAW_DATA_DIR, "weather_raw.csv")
MANIFEST_PATH = os.path.join(RAW_DATA_DIR, ".weather_manifest.csv")

API_URL = "https://archive-api.open-meteo.com/v1/archive"

# Growing regions relevant to Mastronardi's actual network -- NOT terminal
# market cities. Weather affects supply (greenhouse heating, outdoor
# competitor yields), not demand, so it's measured where produce is grown.
GROWING_REGIONS = {
    "ontario_leamington": {"lat": 42.05, "lon": -82.60},   # Leamington/Kingsville cluster
    "maine_backyard_farms": {"lat": 44.75, "lon": -69.87},  # Madison, ME
    "kentucky_appharvest": {"lat": 38.18, "lon": -83.43},   # Morehead, KY
}

DAILY_FIELDS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "sunshine_duration"]
DATE_START = "2001-01-01"
DATE_END = "2025-12-31"


def make_client():
    """Per Open-Meteo's docs: cache responses locally, retry on failure with backoff."""
    cache_session = requests_cache.CachedSession(
        os.path.join(RAW_DATA_DIR, ".open_meteo_cache"), expire_after=-1
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)


def load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return set()
    df = pd.read_csv(MANIFEST_PATH)
    return set(df["region"])


def append_manifest(region, row_count):
    row = pd.DataFrame([{"region": region, "rows_fetched": row_count}])
    header_needed = not os.path.exists(MANIFEST_PATH)
    row.to_csv(MANIFEST_PATH, mode="a", header=header_needed, index=False)


def append_data(df):
    header_needed = not os.path.exists(OUTPUT_PATH)
    df.to_csv(OUTPUT_PATH, mode="a", header=header_needed, index=False)


def fetch_region(client, lat, lon):
    """One request covers the entire date range -- no pagination needed."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": DATE_START,
        "end_date": DATE_END,
        "daily": DAILY_FIELDS,
        "timezone": "auto",
    }
    responses = client.weather_api(API_URL, params=params)
    response = responses[0]  # one location requested -> one response
    daily = response.Daily()

    dates = pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left",
    )

    df = pd.DataFrame({
        "date": dates,
        "tmax_c": daily.Variables(0).ValuesAsNumpy(),
        "tmin_c": daily.Variables(1).ValuesAsNumpy(),
        "precip_mm": daily.Variables(2).ValuesAsNumpy(),
        "sunshine_seconds": daily.Variables(3).ValuesAsNumpy(),
    })
    return df


def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    done = load_manifest()
    client = make_client()

    total_rows = 0
    for region, coords in GROWING_REGIONS.items():
        if region in done:
            print(f"Skipping {region} -- already fetched", flush=True)
            continue

        print(f"Fetching {region} ({coords['lat']}, {coords['lon']})...", flush=True)
        try:
            df = fetch_region(client, coords["lat"], coords["lon"])
        except Exception as e:
            print(f"  Skipped (error, will retry next run): {e}", flush=True)
            continue

        df["region"] = region
        append_data(df)
        append_manifest(region, len(df))
        total_rows += len(df)
        print(f"  {len(df)} rows saved for {region}", flush=True)

    print(f"\nDone. {total_rows} new rows appended to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
# Greenhouse Price Drivers

Modeling the determinants of wholesale price volatility in greenhouse-grown
vegetables (tomatoes, peppers, cucumbers) across Mastronardi Produce's
North American growing regions, using public weather, energy, currency,
and production data.

## Project structure

```
raw_data/         raw pulled data, one file per source, untouched
processed_data/   cleaned/merged panel data, ready for modeling
pipeline/         numbered scripts run in order (00_ -> 01_ -> 02_ ...)
webapp/           Flask dashboard (built later, once model is finalized)
docs/             thesis writeup, notes
```

## Setup

1. `pip install -r requirements.txt`
2. Register for free API keys (all no-cost):
   - USDA MARS API: https://mymarketnews.ams.usda.gov (needed for price data)
   - FRED API: https://fred.stlouisfed.org/docs/api/api_key.html (needed for CPI, USD/MXN, some energy series)
   - EIA API: https://www.eia.gov/opendata/register.php (needed for natural gas/diesel prices)
3. Set them as environment variables (never commit these):
   ```
   export USDA_MARS_API_KEY="..."
   export FRED_API_KEY="..."
   export EIA_API_KEY="..."
   ```
4. Bank of Canada (USD/CAD), StatCan, and NOAA/ECCC weather data don't require keys.

## Pipeline order

- `00_fetch_prices_usda.py` — wholesale tomato/pepper/cucumber prices (DV)
- `01_fetch_weather.py` — NOAA + ECCC weather by region *(not yet built)*
- `02_fetch_energy.py` — EIA natural gas/diesel/electricity *(not yet built)*
- `03_fetch_fx_cpi.py` — Bank of Canada FX + FRED CPI/USD-MXN *(not yet built)*
- `04_fetch_production.py` — StatCan + USDA NASS acreage/production *(not yet built)*
- `05_merge_and_process.py` — join everything into one panel, add lags/dummies *(not yet built)*
- `06_regression.py` — OLS with VIF filtering, robust SEs *(not yet built)*

## Known gaps / limitations

- Competitor production volume (Village Farms, Mucci Farms, Pure Flavor)
  has no clean public API — proxy with regional StatCan/USDA totals instead.
- Tariff/trade-policy periods must be hand-coded as dummy variables from
  known announcement dates, not pulled from an API.
- The Chicago terminal market report slug in `00_fetch_prices_usda.py` is
  a placeholder — confirm the exact slug name via a `/reports` search
  before running.

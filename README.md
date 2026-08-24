# Greenhouse Price Drivers

Modeling the determinants of wholesale price volatility in greenhouse-grown
vegetables (tomatoes, peppers, cucumbers) across Mastronardi Produce's
North American growing regions, using public weather, energy, currency,
and production data. Built as a portfolio project targeting a Data
Analytics Engineer role at Mastronardi Produce (Sunset Farms).

**Final model:** N=2,664, R²=0.352, F=66.16 (p<0.001). Core finding: energy
cost (natural gas + carbon tax) passes through measurably into wholesale
price; seasonality is the single largest driver (winter premium, summer
trough); the ToBRFV tomato virus (2019-) carries the largest individual
coefficient in the model.

## Project structure (as it actually exists in this repo)

```
pipeline/         all scripts, run roughly in numeric order
processed_data/   monthly_panel.csv, regression_results.csv, regression_summary.txt
raw_data/         one file per source, plus .fetch_manifest.csv / .weather_manifest.csv
                   (resumability logs) and .open_meteo_cache.sqlite
.env / .env.example, .gitignore, README.md, requirements.txt
```

Reports (layman writeup, business report, interview reference card,
project journey narrative) and the standalone `dashboard.html` were built
and shared separately as downloads during this project -- they are **not
yet inside this repo folder**. If you want them versioned alongside the
code, create `docs/` and `webapp/` folders and move them in manually.

## Market selection

Terminal markets were chosen by manually checking sample USDA reports for
how often "CANADA ONTARIO greenhouse" actually appears against tomatoes,
peppers, and cucumbers.

- **Chicago, Detroit** -- strong, consistent Ontario-greenhouse presence
  (geographically closest US terminal markets to Leamington/Kingsville)
- **Boston, New York** -- moderate Ontario presence; kept because this is
  where Backyard Farms (Mastronardi's Northeast subsidiary) ships
- **LA -- dropped.** Dominated by Mexican/Californian produce; minimal
  Ontario signal.

## Setup

1. `pip install -r requirements.txt`
2. Register for free API keys (no-cost):
   - USDA MARS API: https://mymarketnews.ams.usda.gov (price data)
   - FRED API: https://fred.stlouisfed.org/docs/api/api_key.html (gas
     price, currency, CPI, sentiment, diesel, foodservice, unemployment --
     FRED covers all of these, no separate EIA key was ever needed)
3. Copy `.env.example` to `.env` and paste keys in:
   ```
   USDA_MARS_API_KEY=...
   FRED_API_KEY=...
   ```
   `.env` is gitignored, loaded automatically via `python-dotenv`.
4. No key needed at all for: Open-Meteo (weather), StatCan (production),
   NOAA/CPC (drought).

## Pipeline order (matches this repo's actual file list)

- **`00_fetch_prices_usda.py`** -- wholesale price DV. Resumable via
  `raw_data/.fetch_manifest.csv`. Two hard-won fixes baked in:
  1. Uses the `/reports/{slug}/report details` endpoint (literally two
     words with a space, lowercase -- not `/Details`), which returns
     itemized price rows only. The plain `/reports/{slug}` endpoint only
     returns weather-note metadata, not prices -- a silent trap early on.
  2. **Peppers must be queried as `"Peppers, Bell Type"`, not `"Peppers"`**
     -- USDA has no generic Peppers category, so the plain name silently
     returns zero rows for every window, no error. The comma in the value
     also needs to be quoted in the query string, or it silently returns
     zero rows again.
- **`dedupe_raw.py`** -- one-off cleanup for exact duplicate price rows
  (can happen if a fetch run is interrupted between saving data and
  marking a window done in the manifest). Already applied to the current
  `usda_prices_raw.csv`, but safe to rerun after any future interrupted pull.
- **`diagnose_peppers.py`** -- the diagnostic script that found Peppers
  had zero rows in the panel entirely (root cause of the bug above).
  Kept for reference, not part of the regular run sequence.
- **`clear_peppers_manifest.py`** -- one-off: removed stale manifest
  entries so the fixed fetch script would actually retry the windows that
  previously returned 0 rows for Peppers. Already applied; no need to
  rerun unless the same class of bug recurs for a different commodity.
- **`test_peppers_query.py`** -- minimal standalone script used to verify
  the quoted-commodity-value fix against the live API before trusting a
  full rerun. Diagnostic only, not part of the pipeline.
- **`01_fetch_weather.py`** -- daily weather for the **growing regions**
  (Ontario/Leamington, Maine/Backyard Farms, Kentucky/AppHarvest), not the
  terminal markets. Uses **Open-Meteo**, not NOAA -- NOAA's CDO API works
  but is slow/paginated; Open-Meteo needs no key and returns the full
  25-year range in one request per region. `.open_meteo_cache.sqlite` is
  its response cache (safe to delete, will just re-fetch).
- **`02_fetch_energy.py`** -- Henry Hub natural gas spot price (monthly)
  via FRED, which already re-publishes this EIA series.
- **`03_fetch_fx_cpi.py`** -- USD/CAD, USD/MXN, US Food CPI, all via FRED
  (not Bank of Canada directly -- their exchange rate series has a real
  methodology break in 2017 that FRED's continuous DEXCAUS series avoids).
- **`04_fetch_production.py`** -- Ontario greenhouse production via
  StatCan's direct CSV download (Table 32-10-0456-01), no API key.
- **`04b_fetch_drought.py`** -- California drought severity via NOAA/NDMC.
  Note: the `aoi` parameter needs the state's **FIPS code** ("06"), not
  the postal abbreviation ("CA") -- the postal code silently returns an
  empty response.
- **`04c_fetch_sentiment.py`** -- US Consumer Sentiment Index via FRED.
- **`04d_fetch_diesel_foodservice.py`** -- diesel price and foodservice
  sales via FRED. Both were **ultimately dropped by VIF filtering** in
  the final model -- a documented negative result, not a bug.
- **`04e_fetch_labor_market.py`** -- Canada unemployment rate as a
  labor-availability proxy via FRED. Survived VIF filtering but was
  **not statistically significant** (p=0.212) -- see limitations below.
- **`05_merge_and_process.py`** -- joins the core five sources into one
  **monthly** panel. StatCan production is annual, spread evenly across
  each year's 12 months as a documented proxy.
- **`05b_add_shock_variables.py`** -- adds Ontario minimum wage
  (hand-coded history; 2001-2008 portion not independently verified),
  COVID-19 disruption dummy (Mar 2020-Jun 2021), and the ToBRFV tomato
  virus dummy (2019-) into the panel.
- **`05c_add_carbon_tax.py`** -- adds Canada's federal carbon charge on
  natural gas (CAD $/GJ), verified schedule including the April 2025 repeal.
- **`05d_add_drought_sentiment.py`** -- merges the drought and sentiment
  data fetched above into the panel.
- **`05e_combine_gas_cost.py`** -- combines Henry Hub + carbon tax into
  one `total_gas_cost_usd_mmbtu` variable (unit-converted to match). Built
  after discovering the two separate variables were splitting credit for
  the same effect when tested side by side in the regression -- **this is
  part of the settled methodology**, not an optional extra.
- **`05f_add_diesel_foodservice.py`** -- merges diesel/foodservice into
  the panel (see note above -- both later dropped by VIF).
- **`05g_add_labor_market.py`** -- merges the unemployment rate into the
  panel (see note above -- not significant).
- **`06_regression.py`** -- OLS, HC3 robust SE, VIF-based multicollinearity
  filtering (threshold 10), month/commodity/market fixed effects. Includes
  a near-collinearity diagnostic (auxiliary regression check) that catches
  cases `np.linalg.matrix_rank` misses due to looser numerical tolerance.
- **`test_final_data.py`**, **`test_greenhouse.py`**, **`test_weather.py`**,
  **`test.py`** -- ad hoc inspection scripts used during development to
  sanity-check specific data slices (StatCan commodity/date coverage,
  greenhouse-vs-field split, weather ranges). Not part of the regular
  pipeline; kept for reference.

## To reproduce the final reported model

Run in this exact order: `00` → `dedupe_raw` → `01` → `02` → `03` → `04`
→ `04b` → `04c` → `04d` → `04e` → `05` → `05b` → `05c` → `05d` → `05e` →
`05f` → `05g` → `06`. This matches the state your `processed_data/` and
`regression_summary.txt` currently reflect.

## Known gaps / limitations

- Competitor production volume (Village Farms, Mucci Farms, Pure Flavor)
  has no clean public API.
- Regional electricity price was never built; diesel was tested and
  dropped for collinearity (see `04d`/`05f` above).
- StatCan's greenhouse production and area-harvested figures are
  suppressed for confidentiality in early years for some commodities
  (2001-2006) -- confirmed real suppression pattern via `diagnose_peppers.py`-
  style investigation, not a bug.
- `ontario_min_wage`'s 2001-2008 rates were compiled from general
  knowledge, not independently verified against Ontario's official ESA
  history in this session -- moot for the final model since this variable
  gets VIF-dropped every time it's tested, but worth knowing if reused
  elsewhere.
- Labor availability was tested only via a broad national unemployment
  proxy (not significant, p=0.212). A Seasonal Agricultural Worker
  Program (SAWP) permit-count variable would be a more precise test of
  the actual hypothesized mechanism, but IRCC only publishes this as
  static annual CSVs, not a queryable API -- a real gap, not built.
- Several additional candidate variables (Florida hurricane weather,
  Mexican freeze days, El Nino/ONI index, currency volatility, extreme
  weather day-counts, USDA per-capita consumption trends) were discussed
  and partially designed during this project but **never fetched or
  merged into this repo** -- they exist only as file downloads shared
  during the working session, not as code here. Treat any results
  referencing them as provisional/not run, not part of the reported model.

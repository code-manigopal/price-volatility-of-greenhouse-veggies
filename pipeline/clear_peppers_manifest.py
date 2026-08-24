"""
clear_peppers_manifest.py

One-off cleanup: removes manifest entries for any commodity containing
"Pepper" -- covers both the old wrong "Peppers" and the newer "Peppers,
Bell Type" if either was logged done with 0 rows before the query-quoting
fix in 00_fetch_prices_usda.py. Uses a contains-match (not exact equality)
to be resistant to whitespace or exact-string mismatches.
"""

import os
import pandas as pd

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "raw_data", ".fetch_manifest.csv")

df = pd.read_csv(MANIFEST_PATH)
print(f"Commodities currently in manifest: {df['commodity'].unique().tolist()}")
before = len(df)

mask = df["commodity"].str.contains("Pepper", case=False, na=False)
print(f"Rows matching 'Pepper': {mask.sum()}")

df = df[~mask]
after = len(df)

df.to_csv(MANIFEST_PATH, index=False)
print(f"Removed {before - after} Pepper-related manifest entries ({after} remain)")
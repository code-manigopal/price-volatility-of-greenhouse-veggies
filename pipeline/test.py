import pandas as pd
df = pd.read_csv('raw_data/usda_prices_raw.csv', low_memory=False)
print(len(df))
dupes = df.duplicated(subset=[
    'report_date','region','commodity_query','origin','district',
    'variety','package','item_size','low_price','high_price'
]).sum()
print(f"duplicate rows: {dupes}")
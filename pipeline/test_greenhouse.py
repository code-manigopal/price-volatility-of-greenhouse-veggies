import pandas as pd
df = pd.read_csv('raw_data/statcan_greenhouse_production_raw.csv')
print(df['Commodity'].unique())
print(df['Production and value'].unique())
print(df['REF_DATE'].min(), df['REF_DATE'].max())
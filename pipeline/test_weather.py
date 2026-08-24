import pandas as pd
df = pd.read_csv('raw_data/weather_raw.csv')
print(df.shape)
print(df.groupby('region')[['tmax_c','tmin_c','precip_mm','sunshine_seconds']].describe().T)
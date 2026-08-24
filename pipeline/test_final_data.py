import pandas as pd
df = pd.read_csv('processed_data/monthly_panel.csv')
missing_area = df[df['annual_area_harvested'].isna()]
print(missing_area.groupby(['commodity', df['month'].str[:4]]).size())
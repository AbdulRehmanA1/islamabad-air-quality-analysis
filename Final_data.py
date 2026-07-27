import pandas as pd
import glob
import re

# Load all CSV files 
all_files = glob.glob("*.csv")
all_files = [f for f in glob.glob("*.csv") if f != 'islamabad_air_quality_cleaned.csv']
dfs = []

for file in all_files:
    df = pd.read_csv(file)
    year_match = re.search(r'(20\d\d)', file)
    df['source_year'] = int(year_match.group(1)) if year_match else None
    df['source_file'] = file
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)

# Fixed the naming mistake of the file having 202022 in its name

combined.loc[combined['source_file'] == 'AQR20augsut202022.csv', 'source_year'] = 2022

# Data Cleaning

# Normalize date strings: remove dashes, embedded years, and extra spaces
combined['Date'] = combined['Date'].str.replace('-', '', regex=False)
combined['Date'] = combined['Date'].str.replace(r'20\d\d', '', regex=True).str.strip()
combined['Date'] = combined['Date'].str.replace(r'\s+', ' ', regex=True)

# Extract day and month from the cleaned date string
extracted = combined['Date'].str.extract(r'(\d{1,2})\s*([A-Za-z]+)')
extracted.columns = ['day', 'month']
combined = pd.concat([combined, extracted], axis=1)

# Build a proper datetime using extracted day/month + source_year
combined['full_date'] = pd.to_datetime(
    combined['day'] + ' ' + combined['month'] + ' ' + combined['source_year'].astype(str),
    format='%d %b %Y', errors='coerce'
)

combined = combined.sort_values('full_date').reset_index(drop=True)
combined = combined.drop(columns=['Date', 'day', 'month', 'source_year'])

# Drop duplicate dates (some months exist in more than one file), keep first occurrence
combined = combined.drop_duplicates(subset='full_date', keep='first').reset_index(drop=True)

# Fill the 2 missing Temperature/Humidity values with column median
combined['Temperature'] = combined['Temperature'].fillna(combined['Temperature'].median())
combined['Humidity'] = combined['Humidity'].fillna(combined['Humidity'].median())

#Feature Engineering 
combined['month'] = combined['full_date'].dt.month
combined['year'] = combined['full_date'].dt.year
combined['day_of_week'] = combined['full_date'].dt.day_name()
combined['season'] = combined['month'].apply(lambda m: 'Winter' if m in [11, 12, 1, 2] else 'Summer')
combined['is_weekend'] = combined['day_of_week'].isin(['Saturday', 'Sunday'])

# Save cleaned dataset
combined.to_csv('islamabad_air_quality_cleaned.csv', index=False)

# Data Analysis
print("Average PM2.5 by month:\n", combined.groupby('month')['PM2.5'].mean().sort_values(ascending=False))
print("\nAverage PM2.5 by season:\n", combined.groupby('season')['PM2.5'].mean())
print("\nAverage PM2.5 weekday vs weekend:\n", combined.groupby('is_weekend')['PM2.5'].mean())
print("\nAverage PM2.5 by year:\n", combined.groupby('year')['PM2.5'].mean())

# Data Visualization
import matplotlib.pyplot as plt
import seaborn as sns

plt.figure()
sns.barplot(x=combined.groupby('month')['PM2.5'].mean().index,
            y=combined.groupby('month')['PM2.5'].mean().values)
plt.title('Average PM2.5 by Month - Islamabad')
plt.xlabel('Month')
plt.ylabel('PM2.5')
plt.savefig('monthly_pm25.png', bbox_inches='tight')

plt.figure()
yearly = combined.groupby('year')['PM2.5'].mean()
sns.lineplot(x=yearly.index, y=yearly.values, marker='o')
plt.title('PM2.5 Trend Over Years')
plt.savefig('yearly_trend.png', bbox_inches='tight')

plt.figure()
pivot = combined.pivot_table(index='year', columns='month', values='PM2.5', aggfunc='mean')
sns.heatmap(pivot, annot=True, fmt='.0f', cmap='Reds')
plt.title('PM2.5 Heatmap: Year vs Month')
plt.savefig('heatmap.png', bbox_inches='tight')
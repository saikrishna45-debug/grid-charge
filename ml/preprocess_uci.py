import pandas as pd
from pathlib import Path

# -----------------------------------------
# 1. File paths
# -----------------------------------------

INPUT_FILE = Path("data/raw/uci/household_power_consumption.txt")
OUTPUT_FILE = Path("data/processed/building_demand.csv")

# -----------------------------------------
# 2. Load the raw UCI dataset
# -----------------------------------------

print("Loading UCI dataset...")

df = pd.read_csv(
    INPUT_FILE,
    sep=";",
    na_values="?",
    low_memory=False
)

print("Raw dataset loaded.")
print(f"Rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")

# -----------------------------------------
# 3. Combine Date + Time
# -----------------------------------------

df["timestamp"] = pd.to_datetime(
    df["Date"] + " " + df["Time"],
    dayfirst=True
)

# -----------------------------------------
# 4. Keep building demand
# -----------------------------------------

df["building_demand_kw"] = pd.to_numeric(
    df["Global_active_power"],
    errors="coerce"
)

# -----------------------------------------
# 5. Remove invalid/missing values
# -----------------------------------------

df = df[["timestamp", "building_demand_kw"]].dropna()

# -----------------------------------------
# 6. Sort by time
# -----------------------------------------

df = df.sort_values("timestamp")

# -----------------------------------------
# 7. Convert 1-minute data → 15-minute data
# -----------------------------------------

df = (
    df.set_index("timestamp")
      .resample("15min")
      .mean()
      .dropna()
      .reset_index()
)

# -----------------------------------------
# 8. Save processed dataset
# -----------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUTPUT_FILE, index=False)

# -----------------------------------------
# 9. Show results
# -----------------------------------------

print("\nProcessing complete!")
print(f"Processed rows: {len(df):,}")
print(f"Saved to: {OUTPUT_FILE}")

print("\nFirst 10 rows:")
print(df.head(10))

print("\nStatistics:")
print(df["building_demand_kw"].describe())
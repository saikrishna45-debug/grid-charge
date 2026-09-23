import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ============================================
# 1. File path
# ============================================

INPUT_FILE = Path("data/processed/building_demand.csv")

# ============================================
# 2. Load processed data
# ============================================

print("Loading building demand data...")

df = pd.read_csv(INPUT_FILE)

# Convert timestamp back to datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])

print("\nDataset loaded successfully!")

# ============================================
# 3. Basic information
# ============================================

print("\n========== DATASET INFO ==========")

print(f"Number of rows: {len(df):,}")
print(f"Number of columns: {len(df.columns)}")

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())

# ============================================
# 4. Missing values
# ============================================

print("\n========== MISSING VALUES ==========")

print(df.isnull().sum())

# ============================================
# 5. Duplicate timestamps
# ============================================

print("\n========== DUPLICATES ==========")

duplicate_count = df["timestamp"].duplicated().sum()

print(f"Duplicate timestamps: {duplicate_count}")

# ============================================
# 6. Demand statistics
# ============================================

print("\n========== DEMAND STATISTICS ==========")

print(df["building_demand_kw"].describe())

# ============================================
# 7. Add useful time features
# ============================================

df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.dayofweek
df["date"] = df["timestamp"].dt.date

# ============================================
# 8. Peak demand
# ============================================

peak_row = df.loc[df["building_demand_kw"].idxmax()]

print("\n========== PEAK DEMAND ==========")

print(f"Peak demand: {peak_row['building_demand_kw']:.3f} kW")
print(f"Peak timestamp: {peak_row['timestamp']}")

# ============================================
# 9. Average demand by hour
# ============================================

hourly_demand = (
    df.groupby("hour")["building_demand_kw"]
    .mean()
)

print("\n========== AVERAGE DEMAND BY HOUR ==========")

print(hourly_demand)

# ============================================
# 10. Plot complete demand history
# ============================================

plt.figure(figsize=(14, 5))

plt.plot(
    df["timestamp"],
    df["building_demand_kw"]
)

plt.title("Building Electricity Demand Over Time")
plt.xlabel("Time")
plt.ylabel("Demand (kW)")

plt.tight_layout()
plt.show()

# ============================================
# 11. Plot average demand by hour
# ============================================

plt.figure(figsize=(10, 5))

plt.plot(
    hourly_demand.index,
    hourly_demand.values,
    marker="o"
)

plt.title("Average Building Demand by Hour")
plt.xlabel("Hour of Day")
plt.ylabel("Average Demand (kW)")
plt.xticks(range(24))

plt.tight_layout()
plt.show()

# ============================================
# 12. Daily average demand
# ============================================

daily_demand = (
    df.groupby("date")["building_demand_kw"]
    .mean()
)

plt.figure(figsize=(14, 5))

plt.plot(
    daily_demand.index,
    daily_demand.values
)

plt.title("Daily Average Building Demand")
plt.xlabel("Date")
plt.ylabel("Average Demand (kW)")

plt.tight_layout()
plt.show()

print("\n========== EDA COMPLETE ==========")

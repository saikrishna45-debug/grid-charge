import pandas as pd
from pathlib import Path

# ============================================
# 1. File paths
# ============================================

INPUT_FILE = Path("data/processed/building_demand.csv")

# ============================================
# 2. Load data
# ============================================

print("Loading building demand data...")

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

# Sort chronologically
df = df.sort_values("timestamp").reset_index(drop=True)

print(f"Loaded {len(df):,} rows")

# ============================================
# 3. Create lag features
# ============================================

print("\nCreating ML features...")

# Because our data is 15-minute intervals:
# lag 1 = 15 minutes ago
# lag 2 = 30 minutes ago
# lag 3 = 45 minutes ago
# lag 4 = 1 hour ago

df["demand_lag_1"] = df["building_demand_kw"].shift(1)
df["demand_lag_2"] = df["building_demand_kw"].shift(2)
df["demand_lag_3"] = df["building_demand_kw"].shift(3)
df["demand_lag_4"] = df["building_demand_kw"].shift(4)

# ============================================
# 4. Create time features
# ============================================

df["hour"] = df["timestamp"].dt.hour

df["minute"] = df["timestamp"].dt.minute

df["day_of_week"] = df["timestamp"].dt.dayofweek

df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)

# ============================================
# 5. Create prediction target
# ============================================

# The target is the demand 15 minutes in the future.

df["target_demand_kw"] = (
    df["building_demand_kw"].shift(-1)
)

# ============================================
# 6. Remove rows with missing values
# ============================================

df = df.dropna().reset_index(drop=True)

print(f"Rows after feature creation: {len(df):,}")

# ============================================
# 7. Select features
# ============================================

features = [
    "building_demand_kw",
    "demand_lag_1",
    "demand_lag_2",
    "demand_lag_3",
    "demand_lag_4",
    "hour",
    "minute",
    "day_of_week",
    "is_weekend"
]

target = "target_demand_kw"

X = df[features]
y = df[target]

# ============================================
# 8. Time-based train/test split
# ============================================

split_index = int(len(df) * 0.80)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

print("\n========== TRAIN / TEST SPLIT ==========")

print(f"Training rows: {len(X_train):,}")
print(f"Testing rows:  {len(X_test):,}")

print(
    f"\nTraining period: "
    f"{df['timestamp'].iloc[0]} → "
    f"{df['timestamp'].iloc[split_index - 1]}"
)

print(
    f"Testing period: "
    f"{df['timestamp'].iloc[split_index]} → "
    f"{df['timestamp'].iloc[-1]}"
)

# ============================================
# 9. Save ML-ready dataset
# ============================================

OUTPUT_FILE = Path(
    "data/processed/building_demand_ml.csv"
)

ml_columns = [
    "timestamp",
    *features,
    target
]

df[ml_columns].to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nML dataset saved to: {OUTPUT_FILE}"
)

print("\n========== FEATURE CREATION COMPLETE ==========")

print("\nFeatures used by the model:")

for feature in features:
    print(f"  - {feature}")

print(f"\nTarget:")
print(f"  - {target}")
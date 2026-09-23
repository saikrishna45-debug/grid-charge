import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


# ============================================
# 1. Paths
# ============================================

INPUT_FILE = Path(
    "data/processed/building_demand_ml.csv"
)

MODEL_FILE = Path(
    "models/building_demand_random_forest.joblib"
)


# ============================================
# 2. Load ML dataset
# ============================================

print("Loading ML dataset...")

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

print(f"Rows loaded: {len(df):,}")


# ============================================
# 3. Define features and target
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
# 4. Time-based train/test split
# ============================================

split_index = int(len(df) * 0.80)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


print("\n========== DATA SPLIT ==========")

print(f"Training samples: {len(X_train):,}")
print(f"Testing samples:  {len(X_test):,}")


# ============================================
# 5. Train Random Forest
# ============================================

print("\nTraining Random Forest...")

model = RandomForestRegressor(
    n_estimators=100,
    max_depth=15,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

print("Training complete!")


# ============================================
# 6. Make predictions
# ============================================

print("\nGenerating predictions...")

predictions = model.predict(X_test)


# ============================================
# 7. Evaluate model
# ============================================

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        predictions
    )
)

r2 = r2_score(
    y_test,
    predictions
)


print("\n========== MODEL PERFORMANCE ==========")

print(f"MAE  : {mae:.4f} kW")
print(f"RMSE : {rmse:.4f} kW")
print(f"R²   : {r2:.4f}")


# ============================================
# 8. Baseline comparison
# ============================================

baseline_predictions = X_test[
    "building_demand_kw"
]

baseline_mae = mean_absolute_error(
    y_test,
    baseline_predictions
)

print("\n========== BASELINE ==========")

print(
    f"Naive baseline MAE: "
    f"{baseline_mae:.4f} kW"
)

print(
    f"Random Forest MAE: "
    f"{mae:.4f} kW"
)


# ============================================
# 9. Feature importance
# ============================================

importance = pd.Series(
    model.feature_importances_,
    index=features
).sort_values(
    ascending=False
)

print("\n========== FEATURE IMPORTANCE ==========")

print(importance)


# ============================================
# 10. Save model
# ============================================

MODEL_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

joblib.dump(
    model,
    MODEL_FILE
)

print(
    f"\nModel saved to: {MODEL_FILE}"
)


# ============================================
# 11. Actual vs Predicted graph
# ============================================

results = pd.DataFrame({
    "timestamp": df["timestamp"].iloc[split_index:],
    "actual": y_test.values,
    "predicted": predictions
})

# Show only the first 500 test points
plot_data = results.iloc[:500]

plt.figure(figsize=(14, 5))

plt.plot(
    plot_data["timestamp"],
    plot_data["actual"],
    label="Actual"
)

plt.plot(
    plot_data["timestamp"],
    plot_data["predicted"],
    label="Predicted"
)

plt.title(
    "Building Demand: Actual vs Predicted"
)

plt.xlabel("Time")
plt.ylabel("Demand (kW)")

plt.legend()

plt.tight_layout()

plt.show()


print("\n========== ML TRAINING COMPLETE ==========")
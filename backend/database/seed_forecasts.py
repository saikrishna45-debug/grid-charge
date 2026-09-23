from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from backend.database.database import SessionLocal
from backend.database.models import Forecast


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_FILE = (
    PROJECT_ROOT
    / "models"
    / "building_demand_xgboost.joblib"
)

FEATURE_FILE = (
    PROJECT_ROOT
    / "models"
    / "building_demand_features.joblib"
)

BUILDING_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "building_demand.csv"
)


def load_model():
    """Load the trained XGBoost model."""

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Forecast model not found: {MODEL_FILE}"
        )

    return joblib.load(MODEL_FILE)


def load_feature_names():
    """Load the exact feature list used during training."""

    if not FEATURE_FILE.exists():
        raise FileNotFoundError(
            f"Feature file not found: {FEATURE_FILE}"
        )

    features = joblib.load(FEATURE_FILE)

    if not isinstance(features, (list, tuple)):
        raise ValueError(
            "Forecast feature file does not contain a valid feature list."
        )

    return list(features)


def load_building_data():
    """Load the processed 15-minute building-demand dataset."""

    if not BUILDING_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Building demand dataset not found: {BUILDING_DATA_FILE}"
        )

    df = pd.read_csv(BUILDING_DATA_FILE)

    if df.empty:
        raise ValueError(
            "Building demand dataset contains no records."
        )

    required_columns = [
        "timestamp",
        "building_demand_kw",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Building dataset is missing columns: {missing_columns}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["building_demand_kw"] = pd.to_numeric(
        df["building_demand_kw"],
        errors="coerce",
    )

    df = (
        df.dropna(
            subset=[
                "timestamp",
                "building_demand_kw",
            ]
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    return df


def create_features(df):
    """
    Recreate the exact 23 features used during XGBoost training.
    """

    df = df.copy()

    # Time features
    df["hour"] = df["timestamp"].dt.hour
    df["minute"] = df["timestamp"].dt.minute
    df["day_of_week"] = df["timestamp"].dt.dayofweek

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    # Cyclic time features
    minutes_since_midnight = (
        df["hour"] * 60
        + df["minute"]
    )

    df["time_sin"] = np.sin(
        2 * np.pi
        * minutes_since_midnight
        / 1440
    )

    df["time_cos"] = np.cos(
        2 * np.pi
        * minutes_since_midnight
        / 1440
    )

    df["week_sin"] = np.sin(
        2 * np.pi
        * df["day_of_week"]
        / 7
    )

    df["week_cos"] = np.cos(
        2 * np.pi
        * df["day_of_week"]
        / 7
    )

    # Demand lags
    df["demand_lag_1"] = (
        df["building_demand_kw"].shift(1)
    )

    df["demand_lag_2"] = (
        df["building_demand_kw"].shift(2)
    )

    df["demand_lag_3"] = (
        df["building_demand_kw"].shift(3)
    )

    df["demand_lag_4"] = (
        df["building_demand_kw"].shift(4)
    )

    # Same time yesterday
    df["demand_same_time_yesterday"] = (
        df["building_demand_kw"].shift(96)
    )

    # Same time last week
    df["demand_same_time_last_week"] = (
        df["building_demand_kw"].shift(672)
    )

    # Rolling demand statistics
    shifted_demand = (
        df["building_demand_kw"].shift(1)
    )

    df["rolling_mean_1h"] = (
        shifted_demand
        .rolling(window=4)
        .mean()
    )

    df["rolling_mean_3h"] = (
        shifted_demand
        .rolling(window=12)
        .mean()
    )

    df["rolling_mean_6h"] = (
        shifted_demand
        .rolling(window=24)
        .mean()
    )

    # Demand-change features
    df["demand_change_15m"] = (
        df["building_demand_kw"]
        - df["building_demand_kw"].shift(1)
    )

    df["demand_change_30m"] = (
        df["building_demand_kw"]
        - df["building_demand_kw"].shift(2)
    )

    df["demand_change_1h"] = (
        df["building_demand_kw"]
        - df["building_demand_kw"].shift(4)
    )

    # Rolling volatility
    df["rolling_std_1h"] = (
        shifted_demand
        .rolling(window=4)
        .std()
    )

    df["rolling_std_3h"] = (
        shifted_demand
        .rolling(window=12)
        .std()
    )

    return df


def seed_forecasts():
    """Generate and store 15-minute-ahead building-demand forecasts."""

    print("Loading XGBoost forecasting model...")

    model = load_model()
    features = load_feature_names()

    print(f"Model: {type(model).__name__}")
    print(f"Feature count: {len(features)}")

    print("Loading building-demand data...")

    df = load_building_data()

    print(f"Building records: {len(df)}")

    print("Creating forecasting features...")

    df = create_features(df)

    # Keep only rows where every model feature exists.
    forecast_df = df.dropna(
        subset=features
    ).copy()

    if forecast_df.empty:
        raise ValueError(
            "No rows contain all required forecasting features."
        )

    X = forecast_df[features]

    print(
        f"Rows available for prediction: {len(X)}"
    )

    print("Generating 15-minute-ahead predictions...")

    predictions = model.predict(X)

    predictions = np.maximum(
        predictions,
        0.0,
    )

    forecast_df["predicted_demand_kw"] = predictions

    # The model predicts the NEXT 15-minute interval.
    forecast_df["forecast_timestamp"] = (
        forecast_df["timestamp"]
        + pd.Timedelta(minutes=15)
    )

    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        for _, row in forecast_df.iterrows():

            forecast_timestamp = (
                row["forecast_timestamp"]
            )

            if pd.isna(forecast_timestamp):
                skipped += 1
                continue

            # Convert timezone-aware timestamps to
            # timezone-naive timestamps for SQLite.
            if getattr(
                forecast_timestamp,
                "tzinfo",
                None,
            ) is not None:
                forecast_timestamp = (
                    forecast_timestamp.tz_localize(None)
                )

            forecast_timestamp = (
                forecast_timestamp.to_pydatetime()
            )

            existing_forecast = (
                db.query(Forecast)
                .filter(
                    Forecast.timestamp
                    == forecast_timestamp
                )
                .first()
            )

            if existing_forecast:
                skipped += 1
                continue

            predicted_demand = float(
                row["predicted_demand_kw"]
            )

            forecast = Forecast(
                timestamp=forecast_timestamp,
                predicted_demand_kw=predicted_demand,
                model="XGBoost",
                forecast_horizon="15 minutes",
            )

            db.add(forecast)
            inserted += 1

        db.commit()

        print("=" * 60)
        print("FORECAST DATABASE SEEDING COMPLETED")
        print("=" * 60)
        print(f"Predictions generated: {len(forecast_df)}")
        print(f"Inserted forecasts:    {inserted}")
        print(f"Skipped forecasts:     {skipped}")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_forecasts()
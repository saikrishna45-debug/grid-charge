from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_FILE = PROJECT_ROOT / "models" / "building_demand_xgboost.joblib"
FEATURE_FILE = PROJECT_ROOT / "models" / "building_demand_features.joblib"
BUILDING_DATA_FILE = PROJECT_ROOT / "data" / "processed" / "building_demand.csv"


# ============================================================
# CONFIGURATION
# ============================================================

FORECAST_HORIZON_MINUTES = 15

MIN_REFERENCE_DEMAND_KW = 0.25
MAX_SCALING_RATIO = 3.0
MIN_SITE_DEMAND_KW = 0.0
SAFE_RATIO_FALLBACK = 1.0


# ============================================================
# FORECAST ADAPTER
# ============================================================


class SiteDemandForecaster:
    """
    Translate the historical UCI household demand series into a time-varying
    15-minute site-demand forecast for the EV charging prototype.

    Architecture:

        UCI historical reference series
                ↓
        XGBoost model prediction on 23 engineered features
                ↓
        reference demand change ratio
                ↓
        simulated site scaling transfer
                ↓
        look-ahead site demand forecast

    This is a simulated site-demand transfer, not a live 2026 forecast on
    actual calendar data. The actual current building demand remains the hard
    safety signal used by the real-time controller.
    """

    def __init__(
        self,
        model_file=MODEL_FILE,
        feature_file=FEATURE_FILE,
        building_data_file=BUILDING_DATA_FILE,
    ):
        self.model_file = Path(model_file)
        self.feature_file = Path(feature_file)
        self.building_data_file = Path(building_data_file)

        self._validate_files()

        self.model = joblib.load(self.model_file)
        self.feature_columns = joblib.load(self.feature_file)

        if not isinstance(self.feature_columns, list):
            self.feature_columns = list(self.feature_columns)

        self.building_df = self._load_building_data()
        self._validate_model_features()

        self.reference_time_index = self._build_reference_time_lookup()

        print("SITE DEMAND FORECASTER")
        print("-" * 60)
        print(f"Model: {self.model_file}")
        print(f"Feature file: {self.feature_file}")
        print(f"Building data: {self.building_data_file}")
        print(f"Model loaded: {type(self.model).__name__}")
        print(f"Feature count: {len(self.feature_columns)}")
        print(f"Building history records: {len(self.building_df)}")
        print("-" * 60)

    def _validate_files(self):
        """Verify the required model/data files exist."""

        required_files = [
            self.model_file,
            self.feature_file,
            self.building_data_file,
        ]

        missing_files = [
            str(path)
            for path in required_files
            if not path.exists()
        ]

        if missing_files:
            raise FileNotFoundError(
                "Required forecast files are missing:\n"
                + "\n".join(f"- {path}" for path in missing_files)
            )

    def _validate_model_features(self):
        """Verify the feature schema matches the trained model."""

        if len(self.feature_columns) != 23:
            raise ValueError(
                "Expected 23 XGBoost features, "
                f"but found {len(self.feature_columns)}."
            )

    def _load_building_data(self):
        """Load the processed UCI historical building-demand data."""

        df = pd.read_csv(self.building_data_file)

        required_columns = ["timestamp", "building_demand_kw"]
        missing = [column for column in required_columns if column not in df.columns]

        if missing:
            raise ValueError(
                "Building demand file is missing columns:\n"
                + "\n".join(f"- {column}" for column in missing)
            )

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["building_demand_kw"] = pd.to_numeric(
            df["building_demand_kw"],
            errors="coerce",
        )

        df = (
            df.dropna(subset=["timestamp", "building_demand_kw"])
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        if df.empty:
            raise ValueError("Building demand dataset contains no valid records.")

        return df

    def _build_reference_time_lookup(self):
        """
        Build a day-of-week and time-of-day bucket lookup so the simulated
        timestamps can be mapped onto the historical reference series without
        using future data.
        """

        ref = self.building_df.copy()
        ref["time_bucket"] = (
            ref["timestamp"].dt.dayofweek * 96
            + ((ref["timestamp"].dt.hour * 60 + ref["timestamp"].dt.minute) // 15)
        )
        return ref

    def _resolve_reference_index(self, timestamp=None):
        """
        Map a simulation timestamp to a comparable historical UCI reference row
        using calendar time-of-day and day-of-week slots.

        This is intentionally not a claim of live 2026 forecasting. It is a
        reference-pattern transfer from the historical load profile into the
        simulation scenario.
        """

        if timestamp is None:
            return len(self.building_df) - 1

        current_ts = pd.Timestamp(timestamp)
        target_bucket = (
            current_ts.dayofweek * 96
            + ((current_ts.hour * 60 + current_ts.minute) // 15)
        )

        matches = self.reference_time_index[
            self.reference_time_index["time_bucket"] == target_bucket
        ]

        if not matches.empty:
            return int(matches.index[-1])

        return len(self.building_df) - 1

    def _build_feature_row_for_reference_index(self, reference_index):
        """
        Recreate the 23-feature row used during training using only information
        available on or before the reference timestamp.
        """

        history = self.building_df.iloc[: reference_index + 1].copy()

        if history.empty:
            raise ValueError("No historical demand data is available for a forecast.")

        history["hour"] = history["timestamp"].dt.hour
        history["minute"] = history["timestamp"].dt.minute
        history["day_of_week"] = history["timestamp"].dt.dayofweek
        history["is_weekend"] = (history["day_of_week"] >= 5).astype(int)

        minutes_of_day = history["hour"] * 60 + history["minute"]
        history["time_sin"] = np.sin(2.0 * np.pi * minutes_of_day / (24.0 * 60.0))
        history["time_cos"] = np.cos(2.0 * np.pi * minutes_of_day / (24.0 * 60.0))
        history["week_sin"] = np.sin(
            2.0 * np.pi * (history["day_of_week"] * 24 + history["hour"]) / (7.0 * 24.0)
        )
        history["week_cos"] = np.cos(
            2.0 * np.pi * (history["day_of_week"] * 24 + history["hour"]) / (7.0 * 24.0)
        )

        for lag in range(1, 5):
            history[f"demand_lag_{lag}"] = history["building_demand_kw"].shift(lag)

        history["demand_same_time_yesterday"] = history["building_demand_kw"].shift(96)
        history["demand_same_time_last_week"] = history["building_demand_kw"].shift(672)

        shifted_demand = history["building_demand_kw"].shift(1)
        history["rolling_mean_1h"] = shifted_demand.rolling(window=4).mean()
        history["rolling_mean_3h"] = shifted_demand.rolling(window=12).mean()
        history["rolling_mean_6h"] = shifted_demand.rolling(window=24).mean()

        history["demand_change_15m"] = history["building_demand_kw"] - history["building_demand_kw"].shift(1)
        history["demand_change_30m"] = history["building_demand_kw"] - history["building_demand_kw"].shift(2)
        history["demand_change_1h"] = history["building_demand_kw"] - history["building_demand_kw"].shift(4)

        history["rolling_std_1h"] = shifted_demand.rolling(window=4).std()
        history["rolling_std_3h"] = shifted_demand.rolling(window=12).std()

        feature_frame = history[self.feature_columns].copy()
        feature_frame = feature_frame.dropna()

        if feature_frame.empty:
            raise ValueError(
                "Not enough historical data to construct feature rows for the reference forecast."
            )

        latest_row = feature_frame.iloc[-1]
        values = {feature: float(latest_row[feature]) for feature in self.feature_columns}
        return pd.DataFrame([values], columns=self.feature_columns)

    def _reference_forecast_record(self, reference_index, timestamp=None):
        """Generate an XGBoost-based 15-minute reference prediction for one historical index."""

        if reference_index < 0 or reference_index >= len(self.building_df):
            raise IndexError(f"Reference index {reference_index} is out of bounds for the building demand history.")

        reference_row = self.building_df.iloc[reference_index]
        reference_timestamp = pd.Timestamp(reference_row["timestamp"])
        reference_current = float(reference_row["building_demand_kw"])

        features = self._build_feature_row_for_reference_index(reference_index)
        prediction = self.model.predict(features)

        if prediction.size == 0 or not np.isfinite(prediction[0]):
            predicted_value = reference_current
        else:
            predicted_value = max(0.0, float(prediction[0]))

        forecast_timestamp = reference_timestamp + pd.Timedelta(minutes=FORECAST_HORIZON_MINUTES)

        return {
            "reference_source_timestamp": reference_timestamp.isoformat(),
            "reference_current_demand_kw": round(reference_current, 6),
            "reference_predicted_demand_kw": round(predicted_value, 6),
            "reference_forecast_timestamp": forecast_timestamp.isoformat(),
            "forecast_timestamp": (
                (pd.Timestamp(timestamp) + pd.Timedelta(minutes=FORECAST_HORIZON_MINUTES)).isoformat()
                if timestamp is not None
                else forecast_timestamp.isoformat()
            ),
            "forecast_horizon_minutes": FORECAST_HORIZON_MINUTES,
            "forecast_model": type(self.model).__name__,
            "forecast_role": "look-ahead planning",
            "hard_grid_safety_input": "actual current building demand",
            "reference_timestamp": reference_timestamp.isoformat(),
        }

    def forecast_reference_demand(self, timestamp=None):
        """
        Produce the XGBoost 15-minute reference forecast for a specific point in
        the simulation timeline.

        This uses historical demand as a reference temporal pattern, then
        transfers the short-term demand movement into the simulated site profile.
        """

        reference_index = self._resolve_reference_index(timestamp)
        return self._reference_forecast_record(reference_index, timestamp=timestamp)

    def _safe_scaling_ratio(self, reference_current, reference_prediction):
        """Calculate a bounded ratio while preventing division-by-zero and invalid values."""

        if not np.isfinite(reference_current) or reference_current <= 1e-9:
            return SAFE_RATIO_FALLBACK

        if not np.isfinite(reference_prediction):
            return SAFE_RATIO_FALLBACK

        ratio = float(reference_prediction / reference_current)

        if not np.isfinite(ratio):
            return SAFE_RATIO_FALLBACK

        return float(np.clip(ratio, 0.0, MAX_SCALING_RATIO))

    def forecast_site_demand(
        self,
        current_site_demand_kw,
        timestamp=None,
        site_peak_demand_kw=None,
    ):
        """
        Convert the historical XGBoost prediction into a site-scale look-ahead
        demand forecast.

        Formula:
            predicted_site_demand = current_site_demand * (predicted_reference / current_reference)

        The ratio is clipped to avoid unrealistic growth, and near-zero reference
        values use a safe fallback. This remains a look-ahead planning signal; the
        actual current building demand remains the safety input for grid control.
        """

        current_site_demand_kw = max(0.0, float(current_site_demand_kw))
        timestamp = pd.Timestamp(timestamp) if timestamp is not None else None

        reference = self.forecast_reference_demand(timestamp)
        reference_current = float(reference["reference_current_demand_kw"])
        reference_prediction = float(reference["reference_predicted_demand_kw"])

        scaling_ratio = self._safe_scaling_ratio(
            reference_current=reference_current,
            reference_prediction=reference_prediction,
        )

        predicted_site_demand = current_site_demand_kw * scaling_ratio
        predicted_site_demand = max(MIN_SITE_DEMAND_KW, predicted_site_demand)

        if site_peak_demand_kw is not None:
            site_peak_demand_kw = max(0.0, float(site_peak_demand_kw))
            predicted_site_demand = min(predicted_site_demand, site_peak_demand_kw)

        output = {
            "timestamp": timestamp.isoformat() if timestamp is not None else reference["reference_source_timestamp"],
            "forecast_timestamp": (
                timestamp + pd.Timedelta(minutes=FORECAST_HORIZON_MINUTES)
            ).isoformat() if timestamp is not None else reference["forecast_timestamp"],
            "reference_source_timestamp": reference["reference_source_timestamp"],
            "reference_current_demand_kw": round(reference_current, 6),
            "reference_predicted_demand_kw": round(reference_prediction, 6),
            "reference_change_ratio": round(scaling_ratio, 6),
            "scaling_ratio": round(scaling_ratio, 6),
            "current_site_demand_kw": round(current_site_demand_kw, 6),
            "predicted_site_demand_kw": round(predicted_site_demand, 6),
            "forecast_horizon_minutes": FORECAST_HORIZON_MINUTES,
            "forecast_model": type(self.model).__name__,
            "forecast_role": "look-ahead planning",
            "scaling_method": (
                "UCI reference demand change transferred to simulated site demand using the "
                "current site demand and safe bounded scaling"
            ),
            "site_scaling_factor": round(scaling_ratio, 6),
            "hard_grid_safety_input": "actual current building demand",
        }

        return output

    def forecast_site_demand_profile(self, site_df, site_peak_demand_kw=None):
        """Generate a time-varying 15-minute site-demand forecast for a whole site timeline."""

        if site_df is None or site_df.empty:
            raise ValueError("A non-empty site demand profile is required for profile forecasting.")

        if isinstance(site_df, pd.DataFrame):
            df = site_df.copy()
        else:
            df = pd.DataFrame(site_df)

        if "timestamp" not in df.columns:
            raise ValueError("Site forecast profile requires a 'timestamp' column.")

        if "building_demand_kw" not in df.columns and "current_site_demand_kw" not in df.columns:
            raise ValueError(
                "Site forecast profile requires either 'building_demand_kw' or 'current_site_demand_kw'."
            )

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).reset_index(drop=True)

        if df.empty:
            raise ValueError("The site timeline contains no valid timestamps.")

        results = []
        for _, row in df.iterrows():
            current_site_demand = row.get("building_demand_kw", row.get("current_site_demand_kw", 0.0))
            current_site_demand = float(current_site_demand)
            result = self.forecast_site_demand(
                current_site_demand_kw=current_site_demand,
                timestamp=row["timestamp"],
                site_peak_demand_kw=site_peak_demand_kw,
            )
            results.append(result)

        profile = pd.DataFrame(results)
        if "timestamp" in profile.columns:
            profile["timestamp"] = pd.to_datetime(profile["timestamp"], errors="coerce")
            profile["forecast_timestamp"] = pd.to_datetime(profile["forecast_timestamp"], errors="coerce")
            profile["forecast_interval_minutes"] = (profile["forecast_timestamp"] - profile["timestamp"]).dt.total_seconds() / 60.0
        return profile


def main():
    """Demonstrate the time-varying reference-to-site forecast with a small profile."""

    print()
    print("=" * 70)
    print("XGBOOST SITE DEMAND FORECAST TEST")
    print("=" * 70)

    forecaster = SiteDemandForecaster()

    timestamps = pd.date_range("2026-01-01 00:00", "2026-01-01 23:45", freq="15min")
    site_profile = pd.DataFrame(
        {
            "timestamp": timestamps,
            "building_demand_kw": [120.0 + 5.0 * np.sin(i / 4.0) + (i % 12) * 0.75 for i in range(len(timestamps))],
        }
    )

    profile = forecaster.forecast_site_demand_profile(site_profile)

    print(f"Forecast records: {len(profile)}")
    print("First few predictions:")
    print(
        profile[
            [
                "timestamp",
                "current_site_demand_kw",
                "predicted_site_demand_kw",
                "reference_current_demand_kw",
                "reference_predicted_demand_kw",
            ]
        ]
        .head()
        .to_string(index=False)
    )

    predictions = profile["predicted_site_demand_kw"].astype(float)
    print("\nForecast statistics:")
    print(f"Minimum predicted site demand: {predictions.min():.3f} kW")
    print(f"Maximum predicted site demand: {predictions.max():.3f} kW")
    print(f"Mean predicted site demand: {predictions.mean():.3f} kW")
    print(f"Std predicted site demand: {predictions.std():.3f} kW")
    print(f"Number of unique forecast values: {predictions.nunique()}")

    print()
    print("=" * 70)
    print("SITE DEMAND FORECAST TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
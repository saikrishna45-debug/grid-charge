from pathlib import Path
from datetime import datetime

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = PROJECT_ROOT / "data" / "smart_ev.db"

MODEL_FILE = PROJECT_ROOT / "models" / "building_demand_xgboost.joblib"
FEATURE_FILE = PROJECT_ROOT / "models" / "building_demand_features.joblib"

BUILDING_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "building_demand.csv"
)


# ============================================================
# REAL-TIME CONTROLLER
# ============================================================

class RealtimeController:
    """
    Simulated real-time controller for the Smart EV Charging
    & Local Grid Management system.

    Current responsibilities:

    1. Read EV state from SQLite.
    2. Read current grid state.
    3. Read site configuration.
    4. Load the XGBoost building-demand model.
    5. Generate a 15-minute building-demand forecast.
    6. Scale the forecast from the UCI household level
       to the configured site demand level.
    7. Calculate expected EV charging capacity.
    8. Check grid safety.

    Later this controller will also:

    9. Run the V3 EV optimizer.
    10. Allocate charging power.
    11. Update EV states.
    12. Store optimization decisions in SQLite.
    13. Run continuously in a simulated 15-minute loop.
    """

    def __init__(
        self,
        database_file=DATABASE_FILE,
        model_file=MODEL_FILE,
        feature_file=FEATURE_FILE,
        building_data_file=BUILDING_DATA_FILE,
    ):
        self.database_file = Path(database_file)
        self.model_file = Path(model_file)
        self.feature_file = Path(feature_file)
        self.building_data_file = Path(building_data_file)

        # ----------------------------------------------------
        # Validate required files
        # ----------------------------------------------------

        if not self.database_file.exists():
            raise FileNotFoundError(
                f"Database not found: {self.database_file}"
            )

        if not self.model_file.exists():
            raise FileNotFoundError(
                f"XGBoost model not found: {self.model_file}"
            )

        if not self.feature_file.exists():
            raise FileNotFoundError(
                f"Feature file not found: {self.feature_file}"
            )

        if not self.building_data_file.exists():
            raise FileNotFoundError(
                f"Building demand data not found: "
                f"{self.building_data_file}"
            )

        # ----------------------------------------------------
        # Load XGBoost model
        # ----------------------------------------------------

        self.model = joblib.load(self.model_file)

        # ----------------------------------------------------
        # Load feature list
        # ----------------------------------------------------

        self.feature_columns = joblib.load(self.feature_file)

        if not isinstance(self.feature_columns, list):
            self.feature_columns = list(self.feature_columns)

        # ----------------------------------------------------
        # Load building demand history
        # ----------------------------------------------------

        self.building_data = self.load_building_demand_data()

        # ----------------------------------------------------
        # Validate model features
        # ----------------------------------------------------

        if len(self.feature_columns) != 23:
            raise ValueError(
                "Unexpected feature count. "
                f"Expected 23 features, found "
                f"{len(self.feature_columns)}."
            )

        print("=" * 60)
        print("SMART EV REAL-TIME CONTROLLER")
        print("=" * 60)

        print(f"Database:       {self.database_file}")
        print(f"XGBoost model:  {self.model_file}")
        print(f"Feature file:   {self.feature_file}")
        print(f"Building data:  {self.building_data_file}")

        print()
        print(
            f"Model loaded successfully: "
            f"{type(self.model).__name__}"
        )

        print(
            f"Forecast features loaded: "
            f"{len(self.feature_columns)}"
        )

        print(
            f"Building history records: "
            f"{len(self.building_data)}"
        )

        print("Controller initialized successfully.")
        print("=" * 60)

    # ========================================================
    # LOAD BUILDING DEMAND DATA
    # ========================================================

    def load_building_demand_data(self):
        """
        Load the processed UCI building-demand time series.

        Expected columns:

            timestamp
            building_demand_kw
        """

        df = pd.read_csv(self.building_data_file)

        required_columns = {
            "timestamp",
            "building_demand_kw",
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                "Building demand data is missing columns: "
                f"{sorted(missing_columns)}"
            )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

        df["building_demand_kw"] = pd.to_numeric(
            df["building_demand_kw"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "timestamp",
                "building_demand_kw",
            ]
        )

        df = df.sort_values("timestamp").reset_index(drop=True)

        if df.empty:
            raise ValueError(
                "Building demand dataset contains no valid records."
            )

        return df

    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    def get_connection(self):
        """
        Create a SQLite database connection.
        """

        import sqlite3

        return sqlite3.connect(self.database_file)

    # ========================================================
    # READ EV STATE
    # ========================================================

    def get_ev_state(self):
        """
        Read the current EV state from SQLite.
        """

        query = """
            SELECT
                ev_id,
                battery_capacity_kwh,
                current_soc_percent,
                target_soc_percent,
                arrival_time,
                departure_time,
                max_charging_power_kw,
                charging_status
            FROM evs
            ORDER BY ev_id
        """

        connection = self.get_connection()

        try:
            df = pd.read_sql_query(query, connection)
        finally:
            connection.close()

        return df

    # ========================================================
    # READ GRID STATE
    # ========================================================

    def get_latest_grid_state(self):
        """
        Read the latest available grid measurement.
        """

        query = """
            SELECT
                timestamp,
                building_demand_kw,
                solar_generation_kw,
                grid_limit_kw,
                ev_charging_power_kw,
                grid_utilization_percent,
                overload_kw
            FROM grid_measurements
            ORDER BY timestamp DESC
            LIMIT 1
        """

        connection = self.get_connection()

        try:
            df = pd.read_sql_query(query, connection)
        finally:
            connection.close()

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    # ========================================================
    # READ SITE CONFIGURATION
    # ========================================================

    def get_site_configuration(self):
        """
        Read the configured site information.
        """

        query = """
            SELECT
                site_id,
                site_type,
                grid_capacity_kw,
                building_peak_demand_kw,
                solar_capacity_kw,
                charger_count
            FROM site_configurations
            ORDER BY id
            LIMIT 1
        """

        connection = self.get_connection()

        try:
            df = pd.read_sql_query(query, connection)
        finally:
            connection.close()

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    # ========================================================
    # BUILD FORECAST FEATURES
    # ========================================================

    def build_forecast_features(self, timestamp):
        """
        Reproduce the exact 23 features used when training
        the XGBoost building-demand forecasting model.
        """

        timestamp = pd.Timestamp(timestamp)

        history = self.building_data[
            self.building_data["timestamp"] <= timestamp
        ].copy()

        if history.empty:
            raise ValueError(
                f"No building demand history available up to "
                f"{timestamp}."
            )

        history = history.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        # ----------------------------------------------------
        # Time features
        # ----------------------------------------------------

        history["hour"] = history["timestamp"].dt.hour

        history["minute"] = history["timestamp"].dt.minute

        history["day_of_week"] = (
            history["timestamp"].dt.dayofweek
        )

        history["is_weekend"] = (
            history["day_of_week"] >= 5
        ).astype(int)

        # ----------------------------------------------------
        # Cyclic time features
        # ----------------------------------------------------

        minutes_of_day = (
            history["hour"] * 60
            + history["minute"]
        )

        history["time_sin"] = np.sin(
            2 * np.pi * minutes_of_day / 1440
        )

        history["time_cos"] = np.cos(
            2 * np.pi * minutes_of_day / 1440
        )

        history["week_sin"] = np.sin(
            2
            * np.pi
            * history["day_of_week"]
            / 7
        )

        history["week_cos"] = np.cos(
            2
            * np.pi
            * history["day_of_week"]
            / 7
        )

        # ----------------------------------------------------
        # Lag features
        # ----------------------------------------------------

        history["demand_lag_1"] = (
            history["building_demand_kw"].shift(1)
        )

        history["demand_lag_2"] = (
            history["building_demand_kw"].shift(2)
        )

        history["demand_lag_3"] = (
            history["building_demand_kw"].shift(3)
        )

        history["demand_lag_4"] = (
            history["building_demand_kw"].shift(4)
        )

        # ----------------------------------------------------
        # Same time yesterday
        # ----------------------------------------------------

        history["demand_same_time_yesterday"] = (
            history["building_demand_kw"].shift(96)
        )

        # ----------------------------------------------------
        # Same time last week
        # ----------------------------------------------------

        history["demand_same_time_last_week"] = (
            history["building_demand_kw"].shift(672)
        )

        # ----------------------------------------------------
        # Rolling demand features
        # ----------------------------------------------------

        shifted_demand = (
            history["building_demand_kw"].shift(1)
        )

        history["rolling_mean_1h"] = (
            shifted_demand
            .rolling(window=4)
            .mean()
        )

        history["rolling_mean_3h"] = (
            shifted_demand
            .rolling(window=12)
            .mean()
        )

        history["rolling_mean_6h"] = (
            shifted_demand
            .rolling(window=24)
            .mean()
        )

        # ----------------------------------------------------
        # Demand change features
        # ----------------------------------------------------

        history["demand_change_15m"] = (
            history["building_demand_kw"]
            - history["building_demand_kw"].shift(1)
        )

        history["demand_change_30m"] = (
            history["building_demand_kw"]
            - history["building_demand_kw"].shift(2)
        )

        history["demand_change_1h"] = (
            history["building_demand_kw"]
            - history["building_demand_kw"].shift(4)
        )

        # ----------------------------------------------------
        # Rolling volatility features
        # ----------------------------------------------------

        history["rolling_std_1h"] = (
            shifted_demand
            .rolling(window=4)
            .std()
        )

        history["rolling_std_3h"] = (
            shifted_demand
            .rolling(window=12)
            .std()
        )

        # ----------------------------------------------------
        # Latest feature row
        # ----------------------------------------------------

        feature_row = history.iloc[-1]

        features = {}

        for feature in self.feature_columns:

            if feature not in history.columns:
                raise ValueError(
                    f"Required model feature "
                    f"'{feature}' was not generated."
                )

            features[feature] = feature_row[feature]

        feature_df = pd.DataFrame(
            [features],
            columns=self.feature_columns,
        )

        # ----------------------------------------------------
        # Validate missing values
        # ----------------------------------------------------

        if feature_df.isna().any().any():

            missing_features = (
                feature_df.columns[
                    feature_df.isna().iloc[0]
                ].tolist()
            )

            raise ValueError(
                "Unable to create complete forecast features. "
                f"Missing values in: {missing_features}"
            )

        return feature_df

    # ========================================================
    # RAW XGBOOST FORECAST
    # ========================================================

    def forecast_reference_demand(self, timestamp=None):
        """
        Generate the raw XGBoost prediction using the UCI
        household-demand scale.

        This is NOT yet the site-level forecast.
        """

        if timestamp is None:
            timestamp = self.building_data[
                "timestamp"
            ].iloc[-1]

        timestamp = pd.Timestamp(timestamp)

        features = self.build_forecast_features(
            timestamp
        )

        prediction = self.model.predict(features)

        predicted_demand = max(
            0.0,
            float(prediction[0]),
        )

        current_row = self.building_data[
            self.building_data["timestamp"] == timestamp
        ]

        if current_row.empty:
            current_demand = float(
                self.building_data.iloc[-1][
                    "building_demand_kw"
                ]
            )
        else:
            current_demand = float(
                current_row.iloc[-1][
                    "building_demand_kw"
                ]
            )

        forecast_timestamp = (
            timestamp + pd.Timedelta(minutes=15)
        )

        return {
            "latest_observed_timestamp": (
                timestamp.isoformat()
            ),
            "forecast_timestamp": (
                forecast_timestamp.isoformat()
            ),
            "current_reference_demand_kw": round(
                current_demand,
                3,
            ),
            "predicted_reference_demand_kw": round(
                predicted_demand,
                3,
            ),
            "forecast_horizon": "15 minutes",
            "model": type(self.model).__name__,
        }

    # ========================================================
    # SITE-SCALE FORECAST
    # ========================================================

    def forecast_site_building_demand(
        self,
        current_site_demand_kw,
        timestamp=None,
    ):
        """
        Convert the UCI-scale XGBoost prediction into a
        site-scale building-demand forecast.

        Scaling method:

            Site Forecast
            =
            Current Site Demand
            ×
            (XGBoost Predicted Reference Demand
             / Current Reference Demand)

        This transfers the learned short-term demand movement
        from the reference household dataset to the configured
        site's current demand level.
        """

        reference_forecast = (
            self.forecast_reference_demand(timestamp)
        )

        current_reference = float(
            reference_forecast[
                "current_reference_demand_kw"
            ]
        )

        predicted_reference = float(
            reference_forecast[
                "predicted_reference_demand_kw"
            ]
        )

        current_site_demand_kw = max(
            0.0,
            float(current_site_demand_kw),
        )

        # ----------------------------------------------------
        # Prevent division by zero
        # ----------------------------------------------------

        if current_reference <= 1e-9:

            site_forecast = current_site_demand_kw

            scaling_ratio = 1.0

        else:

            scaling_ratio = (
                predicted_reference
                / current_reference
            )

            site_forecast = (
                current_site_demand_kw
                * scaling_ratio
            )

        # ----------------------------------------------------
        # Prevent unrealistic negative values
        # ----------------------------------------------------

        site_forecast = max(
            0.0,
            site_forecast,
        )

        return {
            "latest_observed_timestamp": (
                reference_forecast[
                    "latest_observed_timestamp"
                ]
            ),
            "forecast_timestamp": (
                reference_forecast[
                    "forecast_timestamp"
                ]
            ),
            "current_reference_demand_kw": round(
                current_reference,
                3,
            ),
            "predicted_reference_demand_kw": round(
                predicted_reference,
                3,
            ),
            "reference_scaling_ratio": round(
                scaling_ratio,
                4,
            ),
            "current_site_demand_kw": round(
                current_site_demand_kw,
                3,
            ),
            "predicted_site_demand_kw": round(
                site_forecast,
                3,
            ),
            "forecast_horizon": "15 minutes",
            "model": type(self.model).__name__,
            "scaling_method": (
                "Current-site demand proportional transfer "
                "from UCI/XGBoost reference forecast"
            ),
        }

    # ========================================================
    # CALCULATE AVAILABLE EV CAPACITY
    # ========================================================

    def calculate_available_ev_capacity(
        self,
        building_demand_kw,
        solar_generation_kw,
        grid_limit_kw,
    ):
        """
        Calculate the power currently available for EV charging.

        Formula:

            Available EV Capacity =
                Grid Limit
                - Building Demand
                + Solar Generation
        """

        available_capacity = (
            grid_limit_kw
            - building_demand_kw
            + solar_generation_kw
        )

        return max(
            0.0,
            available_capacity,
        )

    # ========================================================
    # GRID SAFETY CHECK
    # ========================================================

    def check_grid_safety(
        self,
        building_demand_kw,
        ev_charging_kw,
        solar_generation_kw,
        grid_limit_kw,
    ):
        """
        Check whether the current system state violates
        the configured grid limit.

        Constraint:

            Building Demand
            + EV Charging
            - Solar
            <= Grid Limit
        """

        controlled_site_demand = (
            building_demand_kw
            + ev_charging_kw
            - solar_generation_kw
        )

        overload = max(
            0.0,
            controlled_site_demand
            - grid_limit_kw,
        )

        return {
            "controlled_site_demand_kw": (
                controlled_site_demand
            ),
            "overload_kw": overload,
            "grid_safe": overload <= 1e-9,
        }

    # ========================================================
    # CURRENT SYSTEM SNAPSHOT
    # ========================================================

    def get_system_snapshot(self):
        """
        Collect current EV, grid, site and forecast state.
        """

        ev_df = self.get_ev_state()

        grid_state = self.get_latest_grid_state()

        site_config = self.get_site_configuration()

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "ev_count": len(ev_df),
            "ev_state": ev_df,
            "grid_state": grid_state,
            "site_configuration": site_config,
        }

        # ----------------------------------------------------
        # Current grid information
        # ----------------------------------------------------

        if grid_state is not None:

            building_demand = float(
                grid_state["building_demand_kw"]
            )

            solar_generation = float(
                grid_state["solar_generation_kw"]
            )

            grid_limit = float(
                grid_state["grid_limit_kw"]
            )

            # ------------------------------------------------
            # Current available EV capacity
            # ------------------------------------------------

            available_capacity = (
                self.calculate_available_ev_capacity(
                    building_demand_kw=building_demand,
                    solar_generation_kw=solar_generation,
                    grid_limit_kw=grid_limit,
                )
            )

            snapshot[
                "available_ev_capacity_kw"
            ] = available_capacity

            # ------------------------------------------------
            # Generate site-scale forecast
            # ------------------------------------------------

            latest_building_timestamp = (
                self.building_data[
                    "timestamp"
                ].iloc[-1]
            )

            forecast = (
                self.forecast_site_building_demand(
                    current_site_demand_kw=building_demand,
                    timestamp=latest_building_timestamp,
                )
            )

            snapshot["forecast"] = forecast

            # ------------------------------------------------
            # Forecast-based EV capacity
            # ------------------------------------------------

            predicted_demand = float(
                forecast[
                    "predicted_site_demand_kw"
                ]
            )

            predicted_ev_capacity = (
                self.calculate_available_ev_capacity(
                    building_demand_kw=predicted_demand,
                    solar_generation_kw=solar_generation,
                    grid_limit_kw=grid_limit,
                )
            )

            snapshot[
                "forecasted_available_ev_capacity_kw"
            ] = predicted_ev_capacity

        return snapshot

    # ========================================================
    # DISPLAY SNAPSHOT
    # ========================================================

    def print_snapshot(self, snapshot):
        """
        Display the current system state and forecast.
        """

        print()
        print("=" * 60)
        print("CURRENT SYSTEM SNAPSHOT")
        print("=" * 60)

        print(
            f"Controller time: "
            f"{snapshot['timestamp']}"
        )

        print(
            f"Total EVs:        "
            f"{snapshot['ev_count']}"
        )

        # ----------------------------------------------------
        # Grid state
        # ----------------------------------------------------

        if snapshot.get("grid_state") is not None:

            grid = snapshot["grid_state"]

            print()
            print("GRID STATE")
            print("-" * 60)

            print(
                f"Building demand:       "
                f"{float(grid['building_demand_kw']):.2f} kW"
            )

            print(
                f"Solar generation:      "
                f"{float(grid['solar_generation_kw']):.2f} kW"
            )

            print(
                f"Grid limit:            "
                f"{float(grid['grid_limit_kw']):.2f} kW"
            )

            print(
                f"EV charging:           "
                f"{float(grid['ev_charging_power_kw']):.2f} kW"
            )

            print(
                f"Grid utilization:      "
                f"{float(grid['grid_utilization_percent']):.2f}%"
            )

            print(
                f"Recorded overload:     "
                f"{float(grid['overload_kw']):.6f} kW"
            )

        # ----------------------------------------------------
        # Current capacity
        # ----------------------------------------------------

        if "available_ev_capacity_kw" in snapshot:

            print(
                f"Available EV capacity:"
                f" {snapshot['available_ev_capacity_kw']:.2f} kW"
            )

        # ----------------------------------------------------
        # Building forecast
        # ----------------------------------------------------

        if snapshot.get("forecast") is not None:

            forecast = snapshot["forecast"]

            print()
            print("BUILDING DEMAND FORECAST")
            print("-" * 60)

            print(
                f"Latest observed:       "
                f"{forecast['latest_observed_timestamp']}"
            )

            print(
                f"Forecast timestamp:    "
                f"{forecast['forecast_timestamp']}"
            )

            print(
                f"Reference current:     "
                f"{forecast['current_reference_demand_kw']:.3f} kW"
            )

            print(
                f"Reference prediction:  "
                f"{forecast['predicted_reference_demand_kw']:.3f} kW"
            )

            print(
                f"Scaling ratio:         "
                f"{forecast['reference_scaling_ratio']:.4f}"
            )

            print(
                f"Current site demand:   "
                f"{forecast['current_site_demand_kw']:.2f} kW"
            )

            print(
                f"Predicted site demand: "
                f"{forecast['predicted_site_demand_kw']:.2f} kW"
            )

            print(
                f"Forecast horizon:      "
                f"{forecast['forecast_horizon']}"
            )

            print(
                f"Forecast model:        "
                f"{forecast['model']}"
            )

            print(
                f"Scaling method:        "
                f"{forecast['scaling_method']}"
            )

        # ----------------------------------------------------
        # Forecasted EV capacity
        # ----------------------------------------------------

        if (
            "forecasted_available_ev_capacity_kw"
            in snapshot
        ):

            print(
                f"Forecasted EV capacity:"
                f" "
                f"{snapshot['forecasted_available_ev_capacity_kw']:.2f}"
                f" kW"
            )

        # ----------------------------------------------------
        # Site configuration
        # ----------------------------------------------------

        if snapshot.get("site_configuration") is not None:

            site = snapshot["site_configuration"]

            print()
            print("SITE CONFIGURATION")
            print("-" * 60)

            print(
                f"Site ID:              "
                f"{site['site_id']}"
            )

            print(
                f"Site type:            "
                f"{site['site_type']}"
            )

            print(
                f"Grid capacity:        "
                f"{float(site['grid_capacity_kw']):.2f} kW"
            )

            print(
                f"Building peak demand: "
                f"{float(site['building_peak_demand_kw']):.2f} kW"
            )

            print(
                f"Solar capacity:       "
                f"{float(site['solar_capacity_kw']):.2f} kW"
            )

            print(
                f"Charger count:        "
                f"{site['charger_count']}"
            )

        print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    controller = RealtimeController()

    snapshot = controller.get_system_snapshot()

    controller.print_snapshot(snapshot)
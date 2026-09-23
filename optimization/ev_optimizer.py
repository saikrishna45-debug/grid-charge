from pathlib import Path
import sys

import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Make the project root importable when this file is executed
# directly with:
#
#     python optimization\ev_optimizer.py
#
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# FORECAST IMPORT
# ============================================================

from simulation.site_demand_forecast import SiteDemandForecaster


# ============================================================
# FILE PATHS
# ============================================================

EV_SCENARIO_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ev_scenario_50_residential.csv"
)

SITE_SIMULATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "site_simulation_50ev_residential.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
)


# ============================================================
# SIMULATION CONFIGURATION
# ============================================================

INTERVAL_MINUTES = 15
INTERVAL_HOURS = INTERVAL_MINUTES / 60.0

# 32 × 15 minutes = 8 hours of look-ahead.
LOOKAHEAD_INTERVALS = 32


# ============================================================
# PRIORITY WEIGHTS
# ============================================================

SLACK_WEIGHT = 0.40
DEPARTURE_WEIGHT = 0.25
ENERGY_WEIGHT = 0.15
SOC_WEIGHT = 0.10
POWER_LIMIT_WEIGHT = 0.10

# ============================================================
# V5 PRIORITY WEIGHTS
# ============================================================

# Keep V3 concepts intact while adding a controlled forecast
# congestion/feasibility component. The total stays at 1.0.
V5_SLACK_WEIGHT = 0.30
V5_DEPARTURE_WEIGHT = 0.20
V5_ENERGY_WEIGHT = 0.15
V5_SOC_WEIGHT = 0.15
V5_POWER_LIMIT_WEIGHT = 0.10
V5_FORECAST_WEIGHT = 0.10


# ============================================================
# NUMERICAL CONSTANTS
# ============================================================

EPSILON = 1e-9


# ============================================================
# FORECAST CONFIGURATION
# ============================================================

# Site demand used for transferring the household XGBoost
# forecast into the configured site scenario.
#
# IMPORTANT:
# This forecast is used for LOOK-AHEAD planning.
#
# Actual current building demand is still used for the
# hard grid-safety constraint.
#
MAX_FORECAST_SCALING_RATIO = 3.0


# ============================================================
# LOAD EV SCENARIO
# ============================================================

def load_ev_scenario(filepath=EV_SCENARIO_FILE):
    """
    Load the synthetic EV scenario.

    Required fields:
        ev_id
        arrival_time
        departure_time
        battery_capacity_kwh
        current_soc
        target_soc
        max_charging_power_kw
    """

    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(
            f"EV scenario file not found:\n{path}"
        )

    df = pd.read_csv(path)

    # --------------------------------------------------------
    # Support ACN-style column names if they are present.
    # --------------------------------------------------------

    rename_map = {}

    if (
        "connectionTime" in df.columns
        and "arrival_time" not in df.columns
    ):
        rename_map["connectionTime"] = "arrival_time"

    if (
        "disconnectTime" in df.columns
        and "departure_time" not in df.columns
    ):
        rename_map["disconnectTime"] = "departure_time"

    if rename_map:
        df = df.rename(columns=rename_map)

    required = [
        "ev_id",
        "arrival_time",
        "departure_time",
        "battery_capacity_kwh",
        "current_soc",
        "target_soc",
        "max_charging_power_kw",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required EV columns:\n"
            + "\n".join(
                f"- {column}"
                for column in missing
            )
        )

    # --------------------------------------------------------
    # Convert timestamps.
    # --------------------------------------------------------

    df["arrival_time"] = pd.to_datetime(
        df["arrival_time"],
        errors="coerce",
        utc=True,
    )

    df["departure_time"] = pd.to_datetime(
        df["departure_time"],
        errors="coerce",
        utc=True,
    )

    # --------------------------------------------------------
    # Convert numeric fields.
    # --------------------------------------------------------

    numeric_columns = [
        "battery_capacity_kwh",
        "current_soc",
        "target_soc",
        "max_charging_power_kw",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[required].isnull().any().any():
        raise ValueError(
            "EV scenario contains missing or invalid "
            "required values."
        )

    # --------------------------------------------------------
    # Calculate initial energy required.
    # --------------------------------------------------------

    df["initial_energy_required_kwh"] = (
        df["battery_capacity_kwh"]
        * (
            df["target_soc"]
            - df["current_soc"]
        )
        / 100.0
    ).clip(lower=0.0)

    return df.reset_index(drop=True)


# ============================================================
# LOAD SITE SIMULATION
# ============================================================

def load_site_simulation(
    filepath=SITE_SIMULATION_FILE
):
    """
    Load the building + solar + grid simulation.
    """

    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(
            f"Site simulation file not found:\n{path}"
        )

    df = pd.read_csv(path)

    required = [
        "timestamp",
        "building_demand_kw",
        "solar_generation_kw",
        "grid_limit_kw",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required site simulation columns:\n"
            + "\n".join(
                f"- {column}"
                for column in missing
            )
        )

    # --------------------------------------------------------
    # Timestamp conversion.
    # --------------------------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    # --------------------------------------------------------
    # Numeric conversion.
    # --------------------------------------------------------

    for column in required[1:]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = (
        df
        .dropna(subset=required)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError(
            "Site simulation contains no valid records."
        )

    return df


# ============================================================
# EXTEND SITE TIMELINE
# ============================================================

def extend_site_timeline(
    site_df,
    final_departure,
):
    """
    Extend the 24-hour site profile if EV departures extend
    beyond the original simulation period.

    The original site's time-of-day profile is repeated.
    """

    site_df = site_df.copy()

    if site_df.empty:
        raise ValueError(
            "Site simulation is empty."
        )

    current_last = site_df["timestamp"].max()

    if final_departure <= current_last:
        return site_df

    original = site_df.copy()

    next_timestamp = (
        current_last
        + pd.Timedelta(
            minutes=INTERVAL_MINUTES
        )
    )

    rows = []

    while next_timestamp <= final_departure:

        key = next_timestamp.strftime("%H:%M")

        matches = original[
            original["timestamp"]
            .dt.strftime("%H:%M")
            == key
        ]

        if matches.empty:

            minutes = (
                original["timestamp"].dt.hour
                * 60
                + original["timestamp"].dt.minute
            )

            target = (
                next_timestamp.hour
                * 60
                + next_timestamp.minute
            )

            source = original.iloc[
                (
                    minutes - target
                )
                .abs()
                .argsort()
                .iloc[0]
            ]

        else:
            source = matches.iloc[0]

        rows.append(
            {
                "timestamp": next_timestamp,
                "building_demand_kw": float(
                    source["building_demand_kw"]
                ),
                "solar_generation_kw": float(
                    source["solar_generation_kw"]
                ),
                "grid_limit_kw": float(
                    source["grid_limit_kw"]
                ),
            }
        )

        next_timestamp += pd.Timedelta(
            minutes=INTERVAL_MINUTES
        )

    if rows:
        site_df = pd.concat(
            [
                site_df,
                pd.DataFrame(rows),
            ],
            ignore_index=True,
        )

    return site_df


# ============================================================
# INITIALIZE EV STATES
# ============================================================

def initialize_ev_states(ev_df):
    """
    Create a mutable state dictionary for every EV.
    """

    states = {}

    for _, row in ev_df.iterrows():

        ev_id = str(row["ev_id"])

        battery = float(
            row["battery_capacity_kwh"]
        )

        initial_soc = float(
            row["current_soc"]
        )

        target_soc = float(
            row["target_soc"]
        )

        energy = max(
            0.0,
            battery
            * (
                target_soc
                - initial_soc
            )
            / 100.0,
        )

        states[ev_id] = {
            "ev_id": ev_id,

            "arrival_time": row[
                "arrival_time"
            ],

            "departure_time": row[
                "departure_time"
            ],

            "battery_capacity_kwh": battery,

            "initial_soc_percent": initial_soc,

            "current_soc_percent": initial_soc,

            "target_soc_percent": target_soc,

            "initial_energy_required_kwh": energy,

            "remaining_energy_kwh": energy,

            "energy_delivered_kwh": 0.0,

            "max_charging_power_kw": max(
                0.0,
                float(
                    row[
                        "max_charging_power_kw"
                    ]
                ),
            ),

            "charging_complete": False,

            "deadline_missed": False,

            "physically_infeasible": False,

            "scheduler_constrained": False,

            "last_reason": "Waiting",
        }

    return states


# ============================================================
# CONNECTED EVs
# ============================================================

def get_connected_ev_states(
    states,
    timestamp,
):
    """
    Return EVs currently connected and not yet complete.
    """

    return [
        state
        for state in states.values()
        if (
            state["arrival_time"]
            <= timestamp
            < state["departure_time"]
            and not state["charging_complete"]
        )
    ]


# ============================================================
# AVAILABLE EV POWER
# ============================================================

def calculate_available_ev_power(
    building_demand_kw,
    solar_generation_kw,
    grid_limit_kw,
):
    """
    Calculate the current power available for EV charging.

    Formula:

        EV capacity =
        Grid limit
        - Building demand
        + Solar generation

    The result can never be negative.
    """

    return max(
        0.0,
        float(
            grid_limit_kw
            - building_demand_kw
            + solar_generation_kw
        ),
    )


# ============================================================
# FORECAST-AWARE FUTURE SITE PROFILE
# ============================================================

def build_forecasted_future_site_rows(
    site_df,
    current_index,
    forecaster,
):
    """
    Create the look-ahead site profile using the XGBoost
    building-demand forecast.

    Architecture:

        Current site demand
                ↓
        XGBoost reference forecast
                ↓
          Scaling ratio
                ↓
        Future site demand
                ↓
        Future EV capacity

    IMPORTANT:

    The forecast is only used for future planning.

    The current interval's actual building demand is still
    used by the hard grid-safety constraint.
    """

    current_row = site_df.iloc[current_index]

    current_building = float(
        current_row["building_demand_kw"]
    )

    # --------------------------------------------------------
    # Generate site-scale forecast.
    # --------------------------------------------------------

    forecast_result = (
        forecaster.forecast_site_demand(
            current_site_demand_kw=current_building,
        )
    )

    forecast_result["predicted_site_demand_kw"] = float(
        forecast_result.get(
            "predicted_site_demand_kw",
            current_building * float(forecast_result.get("scaling_ratio", 1.0)),
        )
    )

    forecast_result["scaling_ratio"] = float(
        forecast_result.get("scaling_ratio", 1.0)
    )

    forecast_result["forecast_horizon"] = int(
        forecast_result.get(
            "forecast_horizon_minutes",
            forecast_result.get("forecast_horizon", 15),
        )
    )

    forecast_result["model"] = (
        forecast_result.get(
            "forecast_model",
            forecast_result.get("model", "XGBRegressor"),
        )
    )

    reference_current = max(
        EPSILON,
        float(
            forecast_result[
                "reference_current_demand_kw"
            ]
        ),
    )

    reference_prediction = max(
        0.0,
        float(
            forecast_result[
                "reference_predicted_demand_kw"
            ]
        ),
    )

    scaling_ratio = (
        reference_prediction
        / reference_current
    )

    scaling_ratio = float(
        np.clip(
            scaling_ratio,
            0.0,
            MAX_FORECAST_SCALING_RATIO,
        )
    )

    # --------------------------------------------------------
    # Build future rows.
    # --------------------------------------------------------

    future_end = min(
        len(site_df),
        current_index
        + LOOKAHEAD_INTERVALS
        + 1,
    )

    future_rows = []

    for future_index in range(
        current_index,
        future_end,
    ):

        source = site_df.iloc[future_index]

        source_building = float(
            source["building_demand_kw"]
        )

        source_solar = float(
            source["solar_generation_kw"]
        )

        source_grid = float(
            source["grid_limit_kw"]
        )

        # ----------------------------------------------------
        # Current interval:
        #
        # KEEP ACTUAL BUILDING DEMAND.
        #
        # This protects grid safety from forecast error.
        # ----------------------------------------------------

        if future_index == current_index:

            forecasted_building = source_building

        else:

            forecasted_building = (
                source_building
                * scaling_ratio
            )

        # ----------------------------------------------------
        # Keep future building demand non-negative.
        # ----------------------------------------------------

        forecasted_building = max(
            0.0,
            forecasted_building,
        )

        future_rows.append(
            {
                "timestamp": source["timestamp"],

                "building_demand_kw": (
                    forecasted_building
                ),

                "actual_building_demand_kw": (
                    source_building
                ),

                "solar_generation_kw": (
                    source_solar
                ),

                "grid_limit_kw": (
                    source_grid
                ),
            }
        )

    return (
        future_rows,
        forecast_result,
    )


# ============================================================
# EV FEASIBILITY
# ============================================================

def calculate_ev_feasibility(
    state,
    timestamp,
    future_site_rows,
):
    """
    Estimate whether an EV can still receive its remaining
    energy before departure.

    Future capacity is calculated using the forecast-aware
    site profile.
    """

    remaining = max(
        0.0,
        state["remaining_energy_kwh"],
    )

    if remaining <= EPSILON:

        return {
            "required_average_power_kw": 0.0,
            "required_charging_hours": 0.0,
            "available_hours": 0.0,
            "slack_hours": 999.0,
            "future_energy_capacity_kwh": 0.0,
            "feasibility_ratio": 0.0,
            "physically_infeasible": False,
        }

    departure = state["departure_time"]

    available_hours = max(
        0.0,
        (
            departure - timestamp
        ).total_seconds()
        / 3600.0,
    )

    max_power = max(
        0.0,
        state["max_charging_power_kw"],
    )

    if max_power <= EPSILON:

        return {
            "required_average_power_kw": float("inf"),
            "required_charging_hours": float("inf"),
            "available_hours": available_hours,
            "slack_hours": -float("inf"),
            "future_energy_capacity_kwh": 0.0,
            "feasibility_ratio": float("inf"),
            "physically_infeasible": True,
        }

    required_avg = (
        remaining
        / max(
            available_hours,
            INTERVAL_HOURS,
        )
    )

    required_hours = remaining / max_power

    slack = available_hours - required_hours

    # --------------------------------------------------------
    # Estimate future charging capacity.
    # --------------------------------------------------------

    future_capacity = 0.0

    for row in future_site_rows:

        future_time = pd.Timestamp(
            row["timestamp"]
        )

        if future_time >= departure:
            break

        available = calculate_available_ev_power(
            float(
                row["building_demand_kw"]
            ),
            float(
                row["solar_generation_kw"]
            ),
            float(
                row["grid_limit_kw"]
            ),
        )

        future_capacity += (
            min(
                max_power,
                available,
            )
            * INTERVAL_HOURS
        )

    ratio = (
        remaining
        / max(
            future_capacity,
            EPSILON,
        )
    )

    physically_infeasible = (
        required_hours
        > available_hours + EPSILON
    )

    return {
        "required_average_power_kw": required_avg,

        "required_charging_hours": required_hours,

        "available_hours": available_hours,

        "slack_hours": slack,

        "future_energy_capacity_kwh": (
            future_capacity
        ),

        "feasibility_ratio": ratio,

        "physically_infeasible": (
            physically_infeasible
        ),
    }


# ============================================================
# PRIORITY CALCULATION
# ============================================================

def calculate_priority(
    state,
    feasibility,
):
    """
    Calculate dynamic EV charging priority.

    Priority considers:

        1. Deadline slack
        2. Departure time
        3. Remaining energy
        4. SOC urgency
        5. Required charging power
        6. Physical infeasibility
        7. Future feasibility
    """

    available_hours = feasibility[
        "available_hours"
    ]

    slack_hours = feasibility[
        "slack_hours"
    ]

    remaining = state[
        "remaining_energy_kwh"
    ]

    battery = max(
        state["battery_capacity_kwh"],
        EPSILON,
    )

    current_soc = state[
        "current_soc_percent"
    ]

    target_soc = state[
        "target_soc_percent"
    ]

    max_power = max(
        state["max_charging_power_kw"],
        EPSILON,
    )

    required_avg = feasibility[
        "required_average_power_kw"
    ]

    # --------------------------------------------------------
    # Deadline urgency.
    # --------------------------------------------------------

    slack_urgency = (
        1.0
        if slack_hours <= 0
        else 1.0 / (
            1.0 + slack_hours
        )
    )

    # --------------------------------------------------------
    # Departure urgency.
    # --------------------------------------------------------

    departure_urgency = (
        1.0
        / (
            1.0
            + max(
                available_hours,
                0.0,
            )
        )
    )

    # --------------------------------------------------------
    # Energy urgency.
    # --------------------------------------------------------

    energy_urgency = float(
        np.clip(
            remaining / battery,
            0.0,
            1.0,
        )
    )

    # --------------------------------------------------------
    # SOC urgency.
    # --------------------------------------------------------

    soc_urgency = float(
        np.clip(
            (
                target_soc
                - current_soc
            )
            / max(
                target_soc,
                EPSILON,
            ),
            0.0,
            1.0,
        )
    )

    # --------------------------------------------------------
    # Power limitation.
    # --------------------------------------------------------

    power_ratio = (
        required_avg / max_power
        if np.isfinite(required_avg)
        else 1.0
    )

    power_limitation = float(
        np.clip(
            power_ratio,
            0.0,
            1.0,
        )
    )

    # --------------------------------------------------------
    # Weighted priority.
    # --------------------------------------------------------

    priority = (
        SLACK_WEIGHT
        * slack_urgency

        + DEPARTURE_WEIGHT
        * departure_urgency

        + ENERGY_WEIGHT
        * energy_urgency

        + SOC_WEIGHT
        * soc_urgency

        + POWER_LIMIT_WEIGHT
        * power_limitation
    )

    # --------------------------------------------------------
    # Physical infeasibility boost.
    # --------------------------------------------------------

    if feasibility[
        "physically_infeasible"
    ]:
        priority += 0.35

    # --------------------------------------------------------
    # Future feasibility boost.
    # --------------------------------------------------------

    future_ratio = feasibility[
        "feasibility_ratio"
    ]

    if future_ratio > 0.75:
        priority += 0.20

    if future_ratio > 1.0:
        priority += 0.30

    return float(priority)


# ============================================================
# REQUIRED POWER RESERVATION
# ============================================================

def calculate_required_reservation(
    state,
    feasibility,
    current_available_power_kw,
):
    """
    Estimate the minimum current charging power that should
    be considered for a critical EV.

    Reservation increases only when an EV becomes critical.
    """

    remaining = state[
        "remaining_energy_kwh"
    ]

    if remaining <= EPSILON:
        return 0.0

    max_power = state[
        "max_charging_power_kw"
    ]

    if max_power <= EPSILON:
        return 0.0

    required_avg = feasibility[
        "required_average_power_kw"
    ]

    slack_hours = feasibility[
        "slack_hours"
    ]

    feasibility_ratio = feasibility.get(
        "feasibility_ratio",
        feasibility.get(
            "forecast_feasibility_ratio",
            0.0,
        ),
    )

    reservation = 0.0

    # --------------------------------------------------------
    # Critical EV.
    # --------------------------------------------------------

    if (
        slack_hours <= 0.50
        or feasibility_ratio >= 0.90
    ):

        reservation = min(
            max_power,
            max(
                required_avg,
                0.0,
            ),
        )

    # --------------------------------------------------------
    # Highly critical EV.
    # --------------------------------------------------------

    if (
        slack_hours <= 0.25
        or feasibility_ratio >= 1.00
    ):

        reservation = min(
            max_power,
            max(
                required_avg,
                max_power * 0.50,
            ),
        )

    # --------------------------------------------------------
    # Physically infeasible EV.
    # --------------------------------------------------------

    if feasibility[
        "physically_infeasible"
    ]:

        reservation = max_power

    return float(
        min(
            reservation,
            current_available_power_kw,
        )
    )


# ============================================================
# V5 FUTURE SITE PROFILE
# ============================================================

def build_v5_forecast_profile(
    site_df,
    forecaster,
):
    """
    Build the time-varying forecast profile once for the V5 timeline.

    Each timestamp is forecast at most once. The optimizer later performs
    timestamp lookups while building each EV look-ahead horizon.
    """

    profile = {}

    for index, source in site_df.iterrows():

        timestamp = pd.Timestamp(source["timestamp"])
        actual_building = float(source["building_demand_kw"])
        actual_solar = float(source["solar_generation_kw"])
        grid_limit = float(source["grid_limit_kw"])

        if index == 0:
            forecasted_building = actual_building
            scaling_ratio = 1.0
            forecast_model = "actual_current_demand"
        else:
            forecast_result = forecaster.forecast_site_demand(
                current_site_demand_kw=actual_building,
                timestamp=timestamp,
            )
            forecasted_building = max(
                0.0,
                float(forecast_result["predicted_site_demand_kw"]),
            )
            scaling_ratio = float(
                forecast_result.get("scaling_ratio", 1.0)
            )
            forecast_model = forecast_result.get(
                "forecast_model",
                "XGBRegressor",
            )

        profile[timestamp] = {
            "timestamp": timestamp,
            "actual_building_demand_kw": actual_building,
            "forecast_building_demand_kw": forecasted_building,
            "forecast_available_capacity_kw": max(
                0.0,
                grid_limit - forecasted_building + actual_solar,
            ),
            "solar_generation_kw": actual_solar,
            "grid_limit_kw": grid_limit,
            "forecast_scaling_ratio": scaling_ratio,
            "forecast_model": forecast_model,
        }

    return profile


def validate_v5_forecast_profile(
    site_df,
    forecast_profile,
):
    """Validate cached forecast values and every required look-ahead lookup."""

    timestamps = pd.to_datetime(site_df["timestamp"], errors="coerce")
    profile_timestamps = pd.DatetimeIndex(forecast_profile.keys())
    predicted_values = np.asarray(
        [
            row["forecast_building_demand_kw"]
            for row in forecast_profile.values()
        ],
        dtype=float,
    )

    intervals = timestamps.sort_values().diff().dropna().dt.total_seconds() / 60.0
    missing_lookups = []

    for current_index in range(len(site_df)):
        future_end = min(
            len(site_df),
            current_index + LOOKAHEAD_INTERVALS + 1,
        )
        for future_index in range(current_index, future_end):
            timestamp = pd.Timestamp(site_df.iloc[future_index]["timestamp"])
            if timestamp not in forecast_profile:
                missing_lookups.append(timestamp)

    report = {
        "forecast_records": len(forecast_profile),
        "unique_predicted_values": int(np.unique(predicted_values).size),
        "timestamps_15_minutes_apart": bool(
            not intervals.empty and np.allclose(intervals, INTERVAL_MINUTES)
        ),
        "no_nan": bool(np.isfinite(predicted_values).all()),
        "no_infinity": bool(np.isfinite(predicted_values).all()),
        "no_negative_predicted_demand": bool((predicted_values >= 0.0).all()),
        "all_horizon_lookups_succeeded": not missing_lookups,
        "missing_horizon_lookups": len(missing_lookups),
        "profile_timestamps_match_timeline": bool(
            len(profile_timestamps) == len(timestamps)
            and set(profile_timestamps) == set(timestamps)
        ),
    }

    if not all(
        [
            report["timestamps_15_minutes_apart"],
            report["no_nan"],
            report["no_infinity"],
            report["no_negative_predicted_demand"],
            report["all_horizon_lookups_succeeded"],
            report["profile_timestamps_match_timeline"],
        ]
    ):
        raise ValueError(
            "V5 forecast profile validation failed: "
            f"{report}"
        )

    return report


def build_time_varying_future_site_rows(
    site_df,
    current_index,
    forecast_profile,
):
    """
    Build a forecast-aware future site profile for the V5 look-ahead scheduler.

    Each future interval is read from the validated, timestamp-indexed V5
    forecast profile so that future building demand is time-varying without
    invoking the model inside the optimization loop.
    """

    future_end = min(
        len(site_df),
        current_index + LOOKAHEAD_INTERVALS + 1,
    )

    future_rows = []

    for future_index in range(
        current_index,
        future_end,
    ):

        source = site_df.iloc[future_index]

        source_timestamp = pd.Timestamp(
            source["timestamp"]
        )

        cached_row = forecast_profile[source_timestamp]

        if future_index == current_index:
            future_rows.append(
                {
                    **cached_row,
                    "forecast_building_demand_kw": float(
                        source["building_demand_kw"]
                    ),
                    "forecast_available_capacity_kw": max(
                        0.0,
                        float(source["grid_limit_kw"])
                        - float(source["building_demand_kw"])
                        + float(source["solar_generation_kw"]),
                    ),
                    "forecast_scaling_ratio": 1.0,
                    "forecast_model": "actual_current_demand",
                }
            )
        else:
            future_rows.append(cached_row)

    return future_rows


def calculate_future_competition_signal(
    connected_states,
    future_timestamp,
    ev_id_to_exclude=None,
):
    """
    Estimate the aggregate charging demand of EVs competing for capacity at
    a future interval, excluding the EV whose feasibility is being evaluated.
    """

    competing_demand = 0.0

    for state in connected_states:

        if ev_id_to_exclude is not None and state["ev_id"] == ev_id_to_exclude:
            continue

        if (
            state["arrival_time"] <= future_timestamp
            < state["departure_time"]
            and not state["charging_complete"]
        ):
            energy_need = max(
                0.0,
                state["remaining_energy_kwh"],
            )

            desired_power = min(
                state["max_charging_power_kw"],
                energy_need / max(INTERVAL_HOURS, EPSILON),
            )

            competing_demand += max(0.0, desired_power)

    return float(competing_demand)


def calculate_ev_feasibility_v5(
    state,
    timestamp,
    future_site_rows,
    connected_states,
):
    """
    V5 feasibility: combine the V3 time-based feasibility with forecast-aware
    future grid congestion and future available charger capacity.
    """

    remaining = max(
        0.0,
        state["remaining_energy_kwh"],
    )

    if remaining <= EPSILON:

        return {
            "required_average_power_kw": 0.0,
            "required_charging_hours": 0.0,
            "available_hours": 0.0,
            "slack_hours": 999.0,
            "future_energy_capacity_kwh": 0.0,
            "future_available_capacity_kw": 0.0,
            "forecast_competing_ev_demand_kw": 0.0,
            "forecast_congestion_ratio": 0.0,
            "forecast_feasibility_ratio": 0.0,
            "forecast_urgency_score": 0.0,
            "forecast_constrained": False,
            "physically_infeasible": False,
            "forecast_influenced_decision": False,
        }

    departure = state["departure_time"]

    available_hours = max(
        0.0,
        (departure - timestamp).total_seconds() / 3600.0,
    )

    max_power = max(
        0.0,
        state["max_charging_power_kw"],
    )

    if max_power <= EPSILON:

        return {
            "required_average_power_kw": float("inf"),
            "required_charging_hours": float("inf"),
            "available_hours": available_hours,
            "slack_hours": -float("inf"),
            "future_energy_capacity_kwh": 0.0,
            "future_available_capacity_kw": 0.0,
            "forecast_competing_ev_demand_kw": 0.0,
            "forecast_congestion_ratio": 0.0,
            "forecast_feasibility_ratio": float("inf"),
            "forecast_urgency_score": 1.0,
            "forecast_constrained": True,
            "physically_infeasible": True,
            "forecast_influenced_decision": False,
        }

    required_avg = remaining / max(available_hours, INTERVAL_HOURS)
    required_hours = remaining / max_power
    slack = available_hours - required_hours

    future_energy_capacity = 0.0
    forecast_available_capacity_values = []
    congestion_values = []
    competing_demand_values = []

    for row in future_site_rows:

        future_time = pd.Timestamp(row["timestamp"])

        if future_time >= departure:
            break

        future_available_capacity = max(
            0.0,
            float(row["forecast_available_capacity_kw"]),
        )

        future_competing_demand = calculate_future_competition_signal(
            connected_states,
            future_time,
            ev_id_to_exclude=state["ev_id"],
        )

        if future_available_capacity > 0.0:
            congestion_ratio = (
                future_competing_demand
                / max(future_available_capacity, EPSILON)
            )
        else:
            congestion_ratio = (
                float("inf") if future_competing_demand > EPSILON else 0.0
            )

        future_energy_capacity += min(
            max_power,
            future_available_capacity,
        ) * INTERVAL_HOURS

        forecast_available_capacity_values.append(future_available_capacity)
        competing_demand_values.append(future_competing_demand)
        congestion_values.append(congestion_ratio)

    future_available_capacity_kw = (
        sum(forecast_available_capacity_values)
        / max(len(forecast_available_capacity_values), 1)
    )

    forecast_competing_ev_demand_kw = (
        sum(competing_demand_values)
        / max(len(competing_demand_values), 1)
    )

    if congestion_values:
        numeric_values = pd.to_numeric(
            congestion_values,
            errors="coerce",
        )
        finite_values = numeric_values[np.isfinite(numeric_values)]
        if finite_values.size == 0:
            forecast_congestion_ratio = 0.0
        else:
            forecast_congestion_ratio = float(finite_values.mean())
    else:
        forecast_congestion_ratio = 0.0

    forecast_feasibility_ratio = (
        remaining / max(future_energy_capacity, EPSILON)
    )

    forecast_urgency_score = float(
        np.clip(
            (
                0.5 * min(1.0, max(0.0, forecast_feasibility_ratio - 1.0))
                + 0.5 * min(1.0, max(0.0, forecast_congestion_ratio))
            ),
            0.0,
            1.0,
        )
    )

    physically_infeasible = required_hours > available_hours + EPSILON
    forecast_constrained = (
        forecast_feasibility_ratio > 1.0
        or forecast_congestion_ratio > 1.0
        or future_available_capacity_kw <= 0.0
    )

    return {
        "required_average_power_kw": required_avg,
        "required_charging_hours": required_hours,
        "available_hours": available_hours,
        "slack_hours": slack,
        "future_energy_capacity_kwh": future_energy_capacity,
        "future_available_capacity_kw": future_available_capacity_kw,
        "forecast_competing_ev_demand_kw": forecast_competing_ev_demand_kw,
        "forecast_congestion_ratio": float(forecast_congestion_ratio),
        "forecast_feasibility_ratio": float(forecast_feasibility_ratio),
        "forecast_urgency_score": float(forecast_urgency_score),
        "forecast_constrained": bool(forecast_constrained),
        "physically_infeasible": bool(physically_infeasible),
        "forecast_influenced_decision": False,
    }


def calculate_priority_v5(
    state,
    feasibility,
):
    """
    V5 priority retains the V3 urgency structure and adds a controlled
    forecast-congestion component.
    """

    available_hours = feasibility["available_hours"]
    slack_hours = feasibility["slack_hours"]
    remaining = state["remaining_energy_kwh"]
    battery = max(state["battery_capacity_kwh"], EPSILON)
    current_soc = state["current_soc_percent"]
    target_soc = state["target_soc_percent"]
    max_power = max(state["max_charging_power_kw"], EPSILON)
    required_avg = feasibility["required_average_power_kw"]

    slack_urgency = (
        1.0 if slack_hours <= 0 else 1.0 / (1.0 + slack_hours)
    )

    departure_urgency = 1.0 / (1.0 + max(available_hours, 0.0))

    energy_urgency = float(
        np.clip(remaining / battery, 0.0, 1.0)
    )

    soc_urgency = float(
        np.clip(
            (target_soc - current_soc) / max(target_soc, EPSILON),
            0.0,
            1.0,
        )
    )

    power_ratio = (
        required_avg / max_power if np.isfinite(required_avg) else 1.0
    )
    power_limitation = float(np.clip(power_ratio, 0.0, 1.0))

    forecast_urgency = float(
        np.clip(
            feasibility.get("forecast_urgency_score", 0.0),
            0.0,
            1.0,
        )
    )

    priority = (
        V5_SLACK_WEIGHT * slack_urgency
        + V5_DEPARTURE_WEIGHT * departure_urgency
        + V5_ENERGY_WEIGHT * energy_urgency
        + V5_SOC_WEIGHT * soc_urgency
        + V5_POWER_LIMIT_WEIGHT * power_limitation
        + V5_FORECAST_WEIGHT * forecast_urgency
    )

    if feasibility["physically_infeasible"]:
        priority += 0.35

    future_ratio = feasibility["forecast_feasibility_ratio"]
    if future_ratio > 0.75:
        priority += 0.20
    if future_ratio > 1.0:
        priority += 0.30

    return float(priority)


def determine_decision_reason_v5(
    state,
    feasibility,
    allocated_power_kw,
    available_power_kw,
):
    """
    Build a data-driven decision reason using the calculated V5 feasibility
    metrics rather than generic scheduler wording.
    """

    if state["charging_complete"]:
        return "Target SOC reached"

    if allocated_power_kw <= EPSILON:

        if available_power_kw <= EPSILON:
            return "Charging paused because the actual current grid capacity is fully constrained"

        if feasibility["forecast_constrained"]:
            return (
                "Charging paused because forecasted future capacity falls to "
                f"{feasibility['future_available_capacity_kw']:.1f} kW while "
                f"{feasibility['forecast_competing_ev_demand_kw']:.1f} kW of "
                "competing EV demand is expected."
            )

        if feasibility["physically_infeasible"]:
            return (
                "Waiting while higher-priority EVs are protected by the current "
                "deadline and future-capacity constraints"
            )

        return (
            "Charging paused to preserve future deadline feasibility under the "
            "forecasted site profile"
        )

    if feasibility["physically_infeasible"]:
        return (
            "Charging at maximum available rate because the EV is physically "
            "time-constrained before departure"
        )

    if feasibility["forecast_constrained"]:
        return (
            "EV prioritized because predicted future capacity falls to "
            f"{feasibility['future_available_capacity_kw']:.1f} kW while "
            f"{feasibility['forecast_competing_ev_demand_kw']:.1f} kW of "
            "competing EV demand is expected."
        )

    if feasibility["forecast_feasibility_ratio"] >= 1.0:
        return (
            "High priority: forecasted future capacity is insufficient to meet "
            "remaining energy before departure"
        )

    if feasibility["slack_hours"] <= 0.50:
        return (
            "High priority: departure deadline is approaching with "
            f"{feasibility['slack_hours']:.2f} hours remaining"
        )

    if (
        allocated_power_kw
        < state["max_charging_power_kw"] - 0.01
    ):
        return (
            "Power reduced because multiple EVs are competing for limited grid "
            "capacity and forecasted future capacity is constrained"
        )

    return "Charging according to dynamic priority and future forecast constraints"


# ============================================================
# SMART POWER ALLOCATION
# ============================================================

def allocate_power(
    connected_states,
    feasibility_map,
    priority_map,
    available_power_kw,
):
    """
    Allocate current EV charging capacity.

    PASS 1:
        Critical reservations.

    PASS 2:
        Remaining capacity according to priority.

    PASS 3:
        Final safety clipping.
    """

    allocations = {
        state["ev_id"]: 0.0
        for state in connected_states
    }

    if not connected_states:
        return allocations

    remaining_capacity = max(
        0.0,
        float(
            available_power_kw
        ),
    )

    # --------------------------------------------------------
    # PASS 1 — Critical reservations.
    # --------------------------------------------------------

    reservation_items = []

    for state in connected_states:

        ev_id = state["ev_id"]

        reservation = (
            calculate_required_reservation(
                state,
                feasibility_map[ev_id],
                remaining_capacity,
            )
        )

        if reservation > EPSILON:

            reservation_items.append(
                (
                    ev_id,
                    reservation,
                )
            )

    reservation_items.sort(
        key=lambda item:
        priority_map[item[0]],
        reverse=True,
    )

    state_map = {
        state["ev_id"]: state
        for state in connected_states
    }

    for ev_id, reservation in reservation_items:

        if remaining_capacity <= EPSILON:
            break

        state = state_map[ev_id]

        max_energy_power = (
            state["remaining_energy_kwh"]
            / INTERVAL_HOURS
        )

        power = min(
            reservation,
            state["max_charging_power_kw"],
            max_energy_power,
            remaining_capacity,
        )

        power = max(
            0.0,
            power,
        )

        allocations[ev_id] += power

        remaining_capacity -= power

    # --------------------------------------------------------
    # PASS 2 — Priority allocation.
    # --------------------------------------------------------

    sorted_states = sorted(
        connected_states,
        key=lambda state:
        priority_map[state["ev_id"]],
        reverse=True,
    )

    for state in sorted_states:

        if remaining_capacity <= EPSILON:
            break

        ev_id = state["ev_id"]

        max_energy_power = (
            state["remaining_energy_kwh"]
            / INTERVAL_HOURS
        )

        additional = min(
            (
                state["max_charging_power_kw"]
                - allocations[ev_id]
            ),
            (
                max_energy_power
                - allocations[ev_id]
            ),
            remaining_capacity,
        )

        additional = max(
            0.0,
            additional,
        )

        allocations[ev_id] += additional

        remaining_capacity -= additional

    # --------------------------------------------------------
    # PASS 3 — Final clipping.
    # --------------------------------------------------------

    for state in connected_states:

        ev_id = state["ev_id"]

        allocations[ev_id] = float(
            np.clip(
                allocations[ev_id],
                0.0,
                state["max_charging_power_kw"],
            )
        )

    return allocations


# ============================================================
# UPDATE EV STATE
# ============================================================

def update_ev_state(
    state,
    charging_power_kw,
):
    """
    Apply one 15-minute charging interval.
    """

    power = max(
        0.0,
        float(
            charging_power_kw
        ),
    )

    energy = min(
        power * INTERVAL_HOURS,
        state["remaining_energy_kwh"],
    )

    state["remaining_energy_kwh"] = max(
        0.0,
        state["remaining_energy_kwh"] - energy,
    )

    state["energy_delivered_kwh"] += energy

    battery = max(
        state["battery_capacity_kwh"],
        EPSILON,
    )

    state["current_soc_percent"] = min(
        state["target_soc_percent"],
        state["initial_soc_percent"]
        + (
            state["energy_delivered_kwh"]
            / battery
            * 100.0
        ),
    )

    if (
        state["remaining_energy_kwh"]
        <= EPSILON
    ):

        state["remaining_energy_kwh"] = 0.0

        state["current_soc_percent"] = (
            state["target_soc_percent"]
        )

        state["charging_complete"] = True

    return float(energy)


# ============================================================
# DECISION EXPLANATION
# ============================================================

def determine_decision_reason(
    state,
    feasibility,
    allocated_power_kw,
    available_power_kw,
):
    """
    Generate an explainable reason for the charging decision.
    """

    if state["charging_complete"]:

        return "Target SOC reached"

    if allocated_power_kw <= EPSILON:

        if available_power_kw <= EPSILON:

            return (
                "Charging paused because "
                "grid capacity is fully constrained"
            )

        if feasibility["physically_infeasible"]:

            return (
                "Waiting while critical capacity "
                "is allocated to higher-priority EVs"
            )

        return (
            "Charging paused to preserve "
            "future deadline feasibility"
        )

    if feasibility["physically_infeasible"]:

        return (
            "Charging at maximum available rate "
            "because the EV is physically time-constrained"
        )

    if feasibility["feasibility_ratio"] >= 1.0:

        return (
            "High priority: future capacity is "
            "insufficient to meet remaining energy"
        )

    if feasibility["slack_hours"] <= 0.50:

        return (
            "High priority: departure deadline "
            "is approaching"
        )

    if (
        allocated_power_kw
        < state["max_charging_power_kw"] - 0.01
    ):

        return (
            "Power reduced because multiple EVs "
            "are competing for limited grid capacity"
        )

    return "Charging according to dynamic priority"


# ============================================================
# MAIN V4 OPTIMIZATION
# ============================================================

def simulate_optimization(
    ev_df,
    site_df,
):
    """
    Main V4 optimization simulation.

    V4 adds XGBoost building-demand forecasting to the
    existing V3 look-ahead scheduler.

    IMPORTANT SAFETY DESIGN:

        Actual current building demand
                    ↓
              HARD SAFETY LIMIT

        XGBoost forecast
                    ↓
            LOOK-AHEAD PLANNING
    """

    print("\n" + "=" * 70)

    print(
        "LOOK-AHEAD SMART EV CHARGING "
        "OPTIMIZATION V4"
    )

    print("=" * 70)

    print()

    print(
        "Initializing XGBoost site-demand forecaster..."
    )

    forecaster = SiteDemandForecaster()

    print()

    states = initialize_ev_states(ev_df)

    final_departure = ev_df["departure_time"].max()

    site_df = (
        extend_site_timeline(
            site_df,
            final_departure,
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    timeline_rows = []
    decision_rows = []
    forecast_rows = []

    # ========================================================
    # SIMULATION LOOP
    # ========================================================

    for index, site_row in site_df.iterrows():

        timestamp = site_row["timestamp"]

        # ----------------------------------------------------
        # ACTUAL CURRENT SITE VALUES
        # ----------------------------------------------------

        actual_building_demand = float(
            site_row["building_demand_kw"]
        )

        solar_generation = float(
            site_row["solar_generation_kw"]
        )

        grid_limit = float(
            site_row["grid_limit_kw"]
        )

        # ----------------------------------------------------
        # HARD SAFETY CAPACITY
        #
        # This ALWAYS uses the actual current building
        # demand, never the ML forecast.
        # ----------------------------------------------------

        available_ev_capacity = (
            calculate_available_ev_power(
                actual_building_demand,
                solar_generation,
                grid_limit,
            )
        )

        # ----------------------------------------------------
        # FORECAST-AWARE LOOK-AHEAD
        # ----------------------------------------------------

        (
            future_site_rows,
            forecast_result,
        ) = build_forecasted_future_site_rows(
            site_df,
            index,
            forecaster,
        )

        forecasted_current_site_demand = float(
            forecast_result[
                "predicted_site_demand_kw"
            ]
        )

        forecast_scaling_ratio = float(
            forecast_result["scaling_ratio"]
        )

        forecast_rows.append(
            {
                "timestamp": timestamp,

                "actual_building_demand_kw": (
                    actual_building_demand
                ),

                "forecasted_site_demand_kw": (
                    forecasted_current_site_demand
                ),

                "reference_current_demand_kw": (
                    forecast_result[
                        "reference_current_demand_kw"
                    ]
                ),

                "reference_predicted_demand_kw": (
                    forecast_result[
                        "reference_predicted_demand_kw"
                    ]
                ),

                "forecast_scaling_ratio": (
                    forecast_scaling_ratio
                ),

                "forecast_horizon": (
                    forecast_result[
                        "forecast_horizon"
                    ]
                ),

                "forecast_model": (
                    forecast_result["model"]
                ),
            }
        )

        # ----------------------------------------------------
        # CURRENT CONNECTED EVs
        # ----------------------------------------------------

        connected_states = get_connected_ev_states(
            states,
            timestamp,
        )

        # ----------------------------------------------------
        # FEASIBILITY + PRIORITY
        # ----------------------------------------------------

        feasibility_map = {}
        priority_map = {}

        for state in connected_states:

            ev_id = state["ev_id"]

            feasibility = calculate_ev_feasibility(
                state,
                timestamp,
                future_site_rows,
            )

            priority = calculate_priority(
                state,
                feasibility,
            )

            feasibility_map[ev_id] = feasibility
            priority_map[ev_id] = priority

            if feasibility["physically_infeasible"]:

                state["physically_infeasible"] = True

        # ----------------------------------------------------
        # UNCONTROLLED CHARGING
        # ----------------------------------------------------

        uncontrolled_requested = sum(
            min(
                state["max_charging_power_kw"],
                (
                    state["remaining_energy_kwh"]
                    / INTERVAL_HOURS
                ),
            )
            for state in connected_states
        )

        uncontrolled_site = (
            actual_building_demand
            + uncontrolled_requested
            - solar_generation
        )

        uncontrolled_overload = max(
            0.0,
            uncontrolled_site - grid_limit,
        )

        # ----------------------------------------------------
        # SMART OPTIMIZATION
        #
        # Uses ACTUAL current capacity.
        # ----------------------------------------------------

        allocations = allocate_power(
            connected_states,
            feasibility_map,
            priority_map,
            available_ev_capacity,
        )

        optimized_power = sum(
            allocations.values()
        )

        interval_energy = 0.0

        # ----------------------------------------------------
        # APPLY EV CHARGING
        # ----------------------------------------------------

        for state in connected_states:

            ev_id = state["ev_id"]

            charging_power = allocations[ev_id]

            energy = update_ev_state(
                state,
                charging_power,
            )

            interval_energy += energy

            feasibility = feasibility_map[ev_id]

            reason = determine_decision_reason(
                state,
                feasibility,
                charging_power,
                available_ev_capacity,
            )

            state["last_reason"] = reason

            # ------------------------------------------------
            # Scheduler constraint detection.
            # ------------------------------------------------

            if (
                charging_power > EPSILON
                and charging_power
                < (
                    state[
                        "max_charging_power_kw"
                    ]
                    - 0.01
                )
            ):

                state["scheduler_constrained"] = True

            # ------------------------------------------------
            # Decision log.
            # ------------------------------------------------

            decision_rows.append(
                {
                    "timestamp": timestamp,

                    "ev_id": ev_id,

                    "current_soc_percent": (
                        state["current_soc_percent"]
                    ),

                    "remaining_energy_kwh": (
                        state["remaining_energy_kwh"]
                    ),

                    "max_charging_power_kw": (
                        state["max_charging_power_kw"]
                    ),

                    "required_average_power_kw": (
                        feasibility[
                            "required_average_power_kw"
                        ]
                    ),

                    "slack_hours": (
                        feasibility["slack_hours"]
                    ),

                    "future_energy_capacity_kwh": (
                        feasibility[
                            "future_energy_capacity_kwh"
                        ]
                    ),

                    "feasibility_ratio": (
                        feasibility["feasibility_ratio"]
                    ),

                    "physically_infeasible": (
                        feasibility[
                            "physically_infeasible"
                        ]
                    ),

                    "priority_score": (
                        priority_map[ev_id]
                    ),

                    "allocated_charging_power_kw": (
                        charging_power
                    ),

                    "energy_delivered_kwh": energy,

                    "decision_reason": reason,
                }
            )

        # ----------------------------------------------------
        # CONTROLLED SITE DEMAND
        #
        # Again, ACTUAL building demand is used here.
        # ----------------------------------------------------

        controlled_site = (
            actual_building_demand
            + optimized_power
            - solar_generation
        )

        controlled_overload = max(
            0.0,
            controlled_site - grid_limit,
        )

        grid_utilization = (
            controlled_site
            / max(
                grid_limit,
                EPSILON,
            )
            * 100.0
        )

        uncontrolled_utilization = (
            uncontrolled_site
            / max(
                grid_limit,
                EPSILON,
            )
            * 100.0
        )

        # ----------------------------------------------------
        # Timeline row.
        # ----------------------------------------------------

        timeline_rows.append(
            {
                "timestamp": timestamp,

                # Actual demand.
                "building_demand_kw": (
                    actual_building_demand
                ),

                # ML forecast.
                "forecasted_site_demand_kw": (
                    forecasted_current_site_demand
                ),

                "forecast_scaling_ratio": (
                    forecast_scaling_ratio
                ),

                # Renewable energy.
                "solar_generation_kw": (
                    solar_generation
                ),

                # Grid.
                "grid_limit_kw": (
                    grid_limit
                ),

                # Current hard capacity.
                "available_ev_capacity_kw": (
                    available_ev_capacity
                ),

                "connected_ev_count": (
                    len(connected_states)
                ),

                # Uncontrolled.
                "uncontrolled_requested_ev_power_kw": (
                    uncontrolled_requested
                ),

                # Optimized.
                "optimized_ev_charging_kw": (
                    optimized_power
                ),

                "uncontrolled_site_demand_kw": (
                    uncontrolled_site
                ),

                "controlled_site_demand_kw": (
                    controlled_site
                ),

                "uncontrolled_overload_kw": (
                    uncontrolled_overload
                ),

                "controlled_overload_kw": (
                    controlled_overload
                ),

                "uncontrolled_grid_utilization_percent": (
                    uncontrolled_utilization
                ),

                "grid_utilization_percent": (
                    grid_utilization
                ),

                "remaining_grid_capacity_kw": max(
                    0.0,
                    grid_limit - controlled_site,
                ),

                "interval_energy_delivered_kwh": (
                    interval_energy
                ),
            }
        )

        # ----------------------------------------------------
        # Deadline check.
        # ----------------------------------------------------

        for state in states.values():

            if (
                timestamp >= state["departure_time"]
                and not state["charging_complete"]
            ):

                state["deadline_missed"] = True

    # ========================================================
    # FINAL EV RESULTS
    # ========================================================

    result_rows = []

    for state in states.values():

        initial = state[
            "initial_energy_required_kwh"
        ]

        delivered = state[
            "energy_delivered_kwh"
        ]

        unmet = max(
            0.0,
            initial - delivered,
        )

        completion = min(
            100.0,
            delivered
            / max(
                initial,
                EPSILON,
            )
            * 100.0,
        )

        result_rows.append(
            {
                "ev_id": state["ev_id"],

                "initial_soc_percent": (
                    state["initial_soc_percent"]
                ),

                "final_soc_percent": (
                    state["current_soc_percent"]
                ),

                "target_soc_percent": (
                    state["target_soc_percent"]
                ),

                "initial_energy_required_kwh": initial,

                "energy_delivered_kwh": delivered,

                "energy_unmet_kwh": unmet,

                "completion_percentage": completion,

                "max_charging_power_kw": (
                    state["max_charging_power_kw"]
                ),

                "charging_complete": (
                    state["charging_complete"]
                ),

                "deadline_missed": (
                    state["deadline_missed"]
                ),

                "physically_infeasible": (
                    state["physically_infeasible"]
                ),

                "scheduler_or_grid_constrained": (
                    state["scheduler_constrained"]
                ),
            }
        )

    return (
        pd.DataFrame(timeline_rows),
        pd.DataFrame(decision_rows),
        pd.DataFrame(result_rows),
        pd.DataFrame(forecast_rows),
    )


# ============================================================
# REAL-TIME OPTIMIZATION FUNCTION
# ============================================================

def optimize_current_ev_state(
    ev_df,
    current_timestamp,
    building_demand_kw,
    solar_generation_kw,
    grid_limit_kw,
    future_site_df=None,
    forecaster=None,
):
    """
    Run one real-time optimization cycle.

    This function is useful later for the FastAPI/WebSocket
    real-time controller.

    Forecast is used for look-ahead planning.

    Actual building demand is always used for the current
    grid-safety constraint.
    """

    current_timestamp = pd.Timestamp(
        current_timestamp
    )

    if current_timestamp.tzinfo is None:

        current_timestamp = (
            current_timestamp.tz_localize("UTC")
        )

    # --------------------------------------------------------
    # Create forecaster if not supplied.
    # --------------------------------------------------------

    if forecaster is None:

        forecaster = SiteDemandForecaster()

    # --------------------------------------------------------
    # Prepare EV dataframe.
    # --------------------------------------------------------

    ev_work = ev_df.copy()

    for column in [
        "arrival_time",
        "departure_time",
    ]:

        ev_work[column] = pd.to_datetime(
            ev_work[column],
            errors="coerce",
            utc=True,
        )

    # --------------------------------------------------------
    # Remaining energy.
    # --------------------------------------------------------

    if "remaining_energy_kwh" not in ev_work.columns:

        ev_work["remaining_energy_kwh"] = (
            ev_work["battery_capacity_kwh"]
            * (
                ev_work["target_soc"]
                - ev_work["current_soc"]
            )
            / 100.0
        )

    if "target_soc" not in ev_work.columns:

        ev_work["target_soc"] = 80.0

    # --------------------------------------------------------
    # Initialize temporary states.
    # --------------------------------------------------------

    states = initialize_ev_states(ev_work)

    for _, row in ev_work.iterrows():

        ev_id = str(row["ev_id"])

        state = states[ev_id]

        state["remaining_energy_kwh"] = max(
            0.0,
            float(
                row.get(
                    "remaining_energy_kwh",
                    state["remaining_energy_kwh"],
                )
            ),
        )

        state["initial_energy_required_kwh"] = max(
            state["remaining_energy_kwh"],
            float(
                row.get(
                    "initial_energy_required_kwh",
                    state["remaining_energy_kwh"],
                )
            ),
        )

        state["current_soc_percent"] = float(
            row["current_soc"]
        )

        state["initial_soc_percent"] = float(
            row["current_soc"]
        )

    # --------------------------------------------------------
    # Current connected EVs.
    # --------------------------------------------------------

    connected = get_connected_ev_states(
        states,
        current_timestamp,
    )

    # --------------------------------------------------------
    # Future site data.
    # --------------------------------------------------------

    if future_site_df is None:

        future_site_df = pd.DataFrame(
            [
                {
                    "timestamp": current_timestamp,

                    "building_demand_kw": (
                        building_demand_kw
                    ),

                    "solar_generation_kw": (
                        solar_generation_kw
                    ),

                    "grid_limit_kw": grid_limit_kw,
                }
            ]
        )

    else:

        future_site_df = future_site_df.copy()

        future_site_df["timestamp"] = pd.to_datetime(
            future_site_df["timestamp"],
            errors="coerce",
            utc=True,
        )

    # --------------------------------------------------------
    # Current hard safety capacity.
    # --------------------------------------------------------

    available = calculate_available_ev_power(
        building_demand_kw,
        solar_generation_kw,
        grid_limit_kw,
    )

    # --------------------------------------------------------
    # Forecast site demand.
    # --------------------------------------------------------

    forecast_result = (
        forecaster.forecast_site_demand(
            current_site_demand_kw=(
                building_demand_kw
            ),
        )
    )

    forecast_ratio = float(
        forecast_result["scaling_ratio"]
    )

    # --------------------------------------------------------
    # Forecast-aware future rows.
    # --------------------------------------------------------

    future_rows = []

    for _, row in (
        future_site_df
        .sort_values("timestamp")
        .head(LOOKAHEAD_INTERVALS)
        .iterrows()
    ):

        future_time = row["timestamp"]

        actual_building = float(
            row["building_demand_kw"]
        )

        if future_time == current_timestamp:

            forecasted_building = (
                actual_building
            )

        else:

            forecasted_building = (
                actual_building
                * forecast_ratio
            )

        future_rows.append(
            {
                "timestamp": future_time,

                "building_demand_kw": max(
                    0.0,
                    forecasted_building,
                ),

                "solar_generation_kw": float(
                    row["solar_generation_kw"]
                ),

                "grid_limit_kw": float(
                    row["grid_limit_kw"]
                ),
            }
        )

    # --------------------------------------------------------
    # Feasibility + priority.
    # --------------------------------------------------------

    feasibility_map = {}
    priority_map = {}

    for state in connected:

        ev_id = state["ev_id"]

        feasibility = calculate_ev_feasibility(
            state,
            current_timestamp,
            future_rows,
        )

        feasibility_map[ev_id] = feasibility

        priority_map[ev_id] = calculate_priority(
            state,
            feasibility,
        )

    # --------------------------------------------------------
    # Allocate current power.
    # --------------------------------------------------------

    allocations = allocate_power(
        connected,
        feasibility_map,
        priority_map,
        available,
    )

    optimized = sum(allocations.values())

    # --------------------------------------------------------
    # Current controlled site demand.
    # --------------------------------------------------------

    controlled = (
        float(building_demand_kw)
        + optimized
        - float(solar_generation_kw)
    )

    overload = max(
        0.0,
        controlled - float(grid_limit_kw),
    )

    return {
        "timestamp": current_timestamp.isoformat(),

        "allocations": allocations,

        "priorities": priority_map,

        "feasibility": feasibility_map,

        "reasons": {
            state["ev_id"]: determine_decision_reason(
                state,
                feasibility_map[state["ev_id"]],
                allocations[state["ev_id"]],
                available,
            )
            for state in connected
        },

        "available_ev_capacity_kw": available,

        "optimized_ev_charging_kw": optimized,

        "controlled_site_demand_kw": controlled,

        "controlled_overload_kw": overload,

        "grid_safe": overload <= EPSILON,

        "forecasted_site_demand_kw": (
            forecast_result[
                "predicted_site_demand_kw"
            ]
        ),

        "forecast_scaling_ratio": (
            forecast_result[
                "scaling_ratio"
            ]
        ),

        "forecast_horizon": (
            forecast_result[
                "forecast_horizon"
            ]
        ),

        "forecast_model": (
            forecast_result["model"]
        ),
    }


# ============================================================
# SAVE OUTPUTS
# ============================================================

def save_outputs(
    timeline_df,
    decisions_df,
    results_df,
    forecast_df,
    suffix="v4_50ev_residential",
):
    """
    Save V4 optimization outputs.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timeline_file = (
        OUTPUT_DIR
        / f"optimized_site_simulation_{suffix}.csv"
    )

    decisions_file = (
        OUTPUT_DIR
        / f"optimization_decisions_{suffix}.csv"
    )

    results_file = (
        OUTPUT_DIR
        / f"ev_optimization_results_{suffix}.csv"
    )

    forecast_file = (
        OUTPUT_DIR
        / f"site_demand_forecast_{suffix}.csv"
    )

    timeline_df.to_csv(
        timeline_file,
        index=False,
    )

    decisions_df.to_csv(
        decisions_file,
        index=False,
    )

    results_df.to_csv(
        results_file,
        index=False,
    )

    forecast_df.to_csv(
        forecast_file,
        index=False,
    )

    return (
        timeline_file,
        decisions_file,
        results_file,
        forecast_file,
    )


def print_summary(
    timeline_df,
    results_df,
    forecast_df,
):
    """
    Print V4 optimization summary.
    """

    total_required = float(
        results_df[
            "initial_energy_required_kwh"
        ].sum()
    )

    total_delivered = float(
        results_df[
            "energy_delivered_kwh"
        ].sum()
    )

    total_unmet = float(
        results_df[
            "energy_unmet_kwh"
        ].sum()
    )

    completed = int(
        results_df[
            "charging_complete"
        ].sum()
    )

    misses = int(
        results_df[
            "deadline_missed"
        ].sum()
    )

    infeasible = int(
        results_df[
            "physically_infeasible"
        ].sum()
    )

    controlled_overload = (
        pd.to_numeric(
            timeline_df[
                "controlled_overload_kw"
            ],
            errors="coerce",
        )
        .fillna(0.0)
    )

    uncontrolled_overload = (
        pd.to_numeric(
            timeline_df[
                "uncontrolled_overload_kw"
            ],
            errors="coerce",
        )
        .fillna(0.0)
    )

    peak_charging = float(
        timeline_df[
            "optimized_ev_charging_kw"
        ].max()
    )

    peak_controlled = float(
        timeline_df[
            "controlled_site_demand_kw"
        ].max()
    )

    peak_utilization = float(
        timeline_df[
            "grid_utilization_percent"
        ].max()
    )

    peak_forecast = float(
        forecast_df[
            "forecasted_site_demand_kw"
        ].max()
    )

    average_forecast_ratio = float(
        forecast_df[
            "forecast_scaling_ratio"
        ].mean()
    )

    print()
    print("=" * 70)

    print(
        "V4 OPTIMIZATION SUMMARY"
    )

    print("=" * 70)

    print(
        f"Simulation intervals: {len(timeline_df)}"
    )

    print(
        f"Number of EVs: {len(results_df)}"
    )

    print(
        f"Total energy required: {total_required:.2f} kWh"
    )

    print(
        f"Total energy delivered: {total_delivered:.2f} kWh"
    )

    print(
        f"Total unmet energy: {total_unmet:.2f} kWh"
    )

    print(
        f"Average EV completion: {results_df['completion_percentage'].mean():.2f}%"
    )

    print(
        f"EVs completed: {completed}/{len(results_df)}"
    )

    print(
        f"Deadline misses: {misses}"
    )

    print(
        f"Physically infeasible EVs: {infeasible}"
    )

    print(
        "Scheduler/grid constrained EVs: "
        f"{int(results_df['scheduler_or_grid_constrained'].sum())}"
    )

    print(
        f"Peak optimized EV charging: {peak_charging:.2f} kW"
    )

    print(
        f"Peak controlled site demand: {peak_controlled:.2f} kW"
    )

    print(
        f"Peak grid utilization: {peak_utilization:.2f}%"
    )

    print(
        f"Maximum controlled overload: {float(controlled_overload.max()):.4f} kW"
    )

    print(
        f"Grid-safe intervals: {int((controlled_overload <= EPSILON).sum())}/{len(timeline_df)}"
    )

    print(
        f"Uncontrolled overload intervals: {int((uncontrolled_overload > EPSILON).sum())}"
    )

    print(
        f"Controlled overload intervals: {int((controlled_overload > EPSILON).sum())}"
    )

    print(
        f"Maximum uncontrolled overload: {float(uncontrolled_overload.max()):.2f} kW"
    )

    print()
    print("FORECAST INTEGRATION")
    print("-" * 70)

    print(
        "Forecast model: XGBRegressor"
    )

    print(
        "Forecast horizon: 15 minutes"
    )

    print(
        f"Peak forecasted site demand: {peak_forecast:.2f} kW"
    )

    print(
        f"Average forecast scaling ratio: {average_forecast_ratio:.4f}"
    )

    print(
        "Forecast role: look-ahead planning"
    )

    print(
        "Hard grid-safety input: actual current building demand"
    )

    print()

    if bool((controlled_overload <= EPSILON).all()):
        print("GRID SAFETY: PASSED")
        print("The optimized schedule stayed within the configured grid limit.")
    else:
        print("GRID SAFETY: FAILED")
        print("The optimized schedule exceeded the configured grid limit.")

    print("=" * 70)


# ============================================================
# MAIN V5 OPTIMIZATION
# ============================================================

def simulate_optimization_v5(
    ev_df,
    site_df,
):
    """
    V5: preserve the V3 baseline and add forecast-aware look-ahead planning
    using the validated time-varying SiteDemandForecaster.

    Safety constraint remains actual current conditions only; forecast is used
    as a planning signal for future capacity and congestion.
    """

    print("\n" + "=" * 70)
    print("LOOK-AHEAD SMART EV CHARGING OPTIMIZATION V5")
    print("=" * 70)
    print()

    forecaster = SiteDemandForecaster()

    states = initialize_ev_states(ev_df)
    final_departure = ev_df["departure_time"].max()

    site_df = (
        extend_site_timeline(
            site_df,
            final_departure,
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    forecast_profile = build_v5_forecast_profile(
        site_df,
        forecaster,
    )
    forecast_validation = validate_v5_forecast_profile(
        site_df,
        forecast_profile,
    )

    timeline_rows = []
    decision_rows = []
    forecast_rows = []

    for index, site_row in site_df.iterrows():

        timestamp = site_row["timestamp"]

        actual_building_demand = float(site_row["building_demand_kw"])
        solar_generation = float(site_row["solar_generation_kw"])
        grid_limit = float(site_row["grid_limit_kw"])

        available_ev_capacity = calculate_available_ev_power(
            actual_building_demand,
            solar_generation,
            grid_limit,
        )

        future_site_rows = build_time_varying_future_site_rows(
            site_df,
            index,
            forecast_profile,
        )

        forecast_target_row = forecast_profile[timestamp]

        forecast_building_demand = float(
            forecast_target_row["forecast_building_demand_kw"]
        )
        forecast_available_capacity = float(
            forecast_target_row["forecast_available_capacity_kw"]
        )
        forecast_scaling_ratio = float(
            forecast_target_row["forecast_scaling_ratio"]
        )

        forecast_rows.append(
            {
                "timestamp": timestamp,
                "actual_building_demand_kw": actual_building_demand,
                "forecast_building_demand_kw": forecast_building_demand,
                "forecast_available_capacity_kw": forecast_available_capacity,
                "forecast_scaling_ratio": forecast_scaling_ratio,
                "forecast_model": forecast_target_row["forecast_model"],
                "forecast_records": forecast_validation["forecast_records"],
                "forecast_unique_values": forecast_validation["unique_predicted_values"],
            }
        )

        connected_states = get_connected_ev_states(states, timestamp)

        feasibility_map = {}
        priority_map = {}

        for state in connected_states:

            ev_id = state["ev_id"]

            feasibility = calculate_ev_feasibility_v5(
                state,
                timestamp,
                future_site_rows,
                connected_states,
            )

            priority = calculate_priority_v5(
                state,
                feasibility,
            )

            feasibility_map[ev_id] = feasibility
            priority_map[ev_id] = priority

            if feasibility["physically_infeasible"]:
                state["physically_infeasible"] = True

        uncontrolled_requested = sum(
            min(
                state["max_charging_power_kw"],
                state["remaining_energy_kwh"] / INTERVAL_HOURS,
            )
            for state in connected_states
        )

        uncontrolled_site = (
            actual_building_demand
            + uncontrolled_requested
            - solar_generation
        )

        uncontrolled_overload = max(0.0, uncontrolled_site - grid_limit)

        allocations = allocate_power(
            connected_states,
            feasibility_map,
            priority_map,
            available_ev_capacity,
        )

        optimized_power = sum(allocations.values())
        interval_energy = 0.0

        for state in connected_states:

            ev_id = state["ev_id"]
            charging_power = allocations[ev_id]
            energy = update_ev_state(state, charging_power)
            interval_energy += energy

            feasibility = feasibility_map[ev_id]
            reason = determine_decision_reason_v5(
                state,
                feasibility,
                charging_power,
                available_ev_capacity,
            )

            state["last_reason"] = reason

            if (
                charging_power > EPSILON
                and charging_power < state["max_charging_power_kw"] - 0.01
            ):
                state["scheduler_constrained"] = True

            if (
                feasibility["forecast_constrained"]
                or feasibility["forecast_urgency_score"] > 0.0
            ):
                feasibility["forecast_influenced_decision"] = True

            decision_rows.append(
                {
                    "timestamp": timestamp,
                    "ev_id": ev_id,
                    "current_soc_percent": state["current_soc_percent"],
                    "remaining_energy_kwh": state["remaining_energy_kwh"],
                    "max_charging_power_kw": state["max_charging_power_kw"],
                    "required_average_power_kw": feasibility["required_average_power_kw"],
                    "slack_hours": feasibility["slack_hours"],
                    "future_energy_capacity_kwh": feasibility["future_energy_capacity_kwh"],
                    "forecast_building_demand_kw": forecast_building_demand,
                    "forecast_available_capacity_kw": forecast_available_capacity,
                    "forecast_competing_ev_demand_kw": feasibility["forecast_competing_ev_demand_kw"],
                    "forecast_congestion_ratio": feasibility["forecast_congestion_ratio"],
                    "forecast_feasibility_ratio": feasibility["forecast_feasibility_ratio"],
                    "forecast_urgency_score": feasibility["forecast_urgency_score"],
                    "forecast_influenced_decision": feasibility["forecast_influenced_decision"],
                    "physically_infeasible": feasibility["physically_infeasible"],
                    "priority_score": priority_map[ev_id],
                    "allocated_charging_power_kw": charging_power,
                    "energy_delivered_kwh": energy,
                    "decision_reason": reason,
                }
            )

        controlled_site = (
            actual_building_demand
            + optimized_power
            - solar_generation
        )

        controlled_overload = max(0.0, controlled_site - grid_limit)
        grid_utilization = (controlled_site / max(grid_limit, EPSILON) * 100.0)
        uncontrolled_utilization = (uncontrolled_site / max(grid_limit, EPSILON) * 100.0)

        timeline_rows.append(
            {
                "timestamp": timestamp,
                "building_demand_kw": actual_building_demand,
                "forecast_building_demand_kw": forecast_building_demand,
                "forecast_available_capacity_kw": forecast_available_capacity,
                "forecast_scaling_ratio": forecast_scaling_ratio,
                "solar_generation_kw": solar_generation,
                "grid_limit_kw": grid_limit,
                "available_ev_capacity_kw": available_ev_capacity,
                "connected_ev_count": len(connected_states),
                "uncontrolled_requested_ev_power_kw": uncontrolled_requested,
                "optimized_ev_charging_kw": optimized_power,
                "uncontrolled_site_demand_kw": uncontrolled_site,
                "controlled_site_demand_kw": controlled_site,
                "uncontrolled_overload_kw": uncontrolled_overload,
                "controlled_overload_kw": controlled_overload,
                "uncontrolled_grid_utilization_percent": uncontrolled_utilization,
                "grid_utilization_percent": grid_utilization,
                "remaining_grid_capacity_kw": max(0.0, grid_limit - controlled_site),
                "interval_energy_delivered_kwh": interval_energy,
            }
        )

        for state in states.values():

            if (
                timestamp >= state["departure_time"]
                and not state["charging_complete"]
            ):
                state["deadline_missed"] = True

    result_rows = []
    for state in states.values():

        initial = state["initial_energy_required_kwh"]
        delivered = state["energy_delivered_kwh"]
        unmet = max(0.0, initial - delivered)
        completion = min(100.0, delivered / max(initial, EPSILON) * 100.0)

        result_rows.append(
            {
                "ev_id": state["ev_id"],
                "initial_soc_percent": state["initial_soc_percent"],
                "final_soc_percent": state["current_soc_percent"],
                "target_soc_percent": state["target_soc_percent"],
                "initial_energy_required_kwh": initial,
                "energy_delivered_kwh": delivered,
                "energy_unmet_kwh": unmet,
                "completion_percentage": completion,
                "max_charging_power_kw": state["max_charging_power_kw"],
                "charging_complete": state["charging_complete"],
                "deadline_missed": state["deadline_missed"],
                "physically_infeasible": state["physically_infeasible"],
                "scheduler_or_grid_constrained": state["scheduler_constrained"],
            }
        )

    return (
        pd.DataFrame(timeline_rows),
        pd.DataFrame(decision_rows),
        pd.DataFrame(result_rows),
        pd.DataFrame(forecast_rows),
    )


def save_outputs_v5(
    timeline_df,
    decisions_df,
    results_df,
    forecast_df,
    suffix="v5_50ev_residential",
):
    """Persist the V5 outputs separately from V3/V4 artifacts."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timeline_file = OUTPUT_DIR / f"optimized_site_simulation_{suffix}.csv"
    decisions_file = OUTPUT_DIR / f"optimization_decisions_{suffix}.csv"
    results_file = OUTPUT_DIR / f"ev_optimization_results_{suffix}.csv"
    forecast_file = OUTPUT_DIR / f"site_demand_forecast_{suffix}.csv"

    timeline_df.to_csv(timeline_file, index=False)
    decisions_df.to_csv(decisions_file, index=False)
    results_df.to_csv(results_file, index=False)
    forecast_df.to_csv(forecast_file, index=False)

    return (timeline_file, decisions_file, results_file, forecast_file)


def print_summary_v5(
    timeline_df,
    results_df,
    forecast_df,
):
    """Print a compact V5 summary with explicit forecast metrics."""

    total_required = float(results_df["initial_energy_required_kwh"].sum())
    total_delivered = float(results_df["energy_delivered_kwh"].sum())
    total_unmet = float(results_df["energy_unmet_kwh"].sum())
    completed = int(results_df["charging_complete"].sum())
    misses = int(results_df["deadline_missed"].sum())
    infeasible = int(results_df["physically_infeasible"].sum())

    controlled_overload = pd.to_numeric(
        timeline_df["controlled_overload_kw"],
        errors="coerce",
    ).fillna(0.0)
    peak_charging = float(timeline_df["optimized_ev_charging_kw"].max())
    peak_site = float(timeline_df["controlled_site_demand_kw"].max())
    peak_utilization = float(timeline_df["grid_utilization_percent"].max())

    print()
    print("=" * 70)
    print("V5 OPTIMIZATION SUMMARY")
    print("=" * 70)
    print(f"Simulation intervals: {len(timeline_df)}")
    print(f"Number of EVs: {len(results_df)}")
    print(f"Total energy required: {total_required:.2f} kWh")
    print(f"Total energy delivered: {total_delivered:.2f} kWh")
    print(f"Total unmet energy: {total_unmet:.2f} kWh")
    print(f"Average EV completion: {results_df['completion_percentage'].mean():.2f}%")
    print(f"EVs completed: {completed}/{len(results_df)}")
    print(f"Deadline misses: {misses}")
    print(f"Physically infeasible EVs: {infeasible}")
    print(f"Peak optimized EV charging: {peak_charging:.2f} kW")
    print(f"Peak controlled site demand: {peak_site:.2f} kW")
    print(f"Peak grid utilization: {peak_utilization:.2f}%")
    print(f"Maximum controlled overload: {float(controlled_overload.max()):.4f} kW")
    print(f"Grid-safe intervals: {int((controlled_overload <= 1e-9).sum())}/{len(timeline_df)}")
    print(f"Forecast records: {len(forecast_df)}")
    print(f"Peak forecasted site demand: {float(forecast_df['forecast_building_demand_kw'].max()):.2f} kW")
    print(f"Average forecast scaling ratio: {float(forecast_df['forecast_scaling_ratio'].mean()):.4f}")
    print("Forecast role: look-ahead planning")
    print("Hard grid-safety input: actual current building demand")
    print()

    if bool((controlled_overload <= 1e-9).all()):
        print("GRID SAFETY: PASSED")
    else:
        print("GRID SAFETY: FAILED")

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading EV scenario...")

    ev_df = load_ev_scenario()

    print(f"Loaded {len(ev_df)} EV sessions.")
    print()

    print("Loading site simulation...")

    site_df = load_site_simulation()

    print(f"Loaded {len(site_df)} site intervals.")

    (
        timeline_df,
        decisions_df,
        results_df,
        forecast_df,
    ) = simulate_optimization_v5(
        ev_df,
        site_df,
    )

    (
        timeline_file,
        decisions_file,
        results_file,
        forecast_file,
    ) = save_outputs_v5(
        timeline_df,
        decisions_df,
        results_df,
        forecast_df,
    )

    print_summary_v5(
        timeline_df,
        results_df,
        forecast_df,
    )

    print()
    print("OUTPUT FILES")
    print("-" * 70)
    print("Timeline:")
    print(timeline_file)

    print()
    print("Decision log:")
    print(decisions_file)

    print()
    print("EV results:")
    print(results_file)

    print()
    print("Forecast:")
    print(forecast_file)

    print()
    print("V5 optimization completed successfully.")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
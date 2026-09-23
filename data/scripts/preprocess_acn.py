from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "acn"
    / "evgrid_master_complete.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = OUTPUT_DIR / "ev_sessions_processed.csv"


# ============================================================
# Required columns
# ============================================================

REQUIRED_COLUMNS = [
    "sessionID",
    "stationID",
    "spaceID",
    "siteID",
    "clusterID",
    "connectionTime",
    "disconnectTime",
    "doneChargingTime",
    "kWhDelivered",
    "energy_delivered_kwh",
    "energy_needed_kwh",
    "ev_id",
    "battery_capacity_kwh",
    "current_soc",
    "target_soc",
    "max_charging_power_kw",
    "building_load_kw",
    "grid_capacity_kw",
    "solar_generation_kw",
]


# ============================================================
# Helper functions
# ============================================================

def calculate_energy_needed(
    battery_capacity_kwh: pd.Series,
    current_soc: pd.Series,
    target_soc: pd.Series,
) -> pd.Series:
    """
    Calculate remaining energy required to reach target SOC.

    Formula:

        Energy Required =
        Battery Capacity × (Target SOC - Current SOC) / 100

    Negative values are clipped to zero.
    """

    energy = (
        battery_capacity_kwh
        * (target_soc - current_soc)
        / 100.0
    )

    return energy.clip(lower=0)


def classify_provenance(value) -> str:
    """
    Convert the original data_source field into a clean
    provenance category.
    """

    value = str(value).strip().lower()

    if "synthetic" in value:
        return "synthetic"

    if "real" in value or "acn" in value:
        return "real_acn"

    return "unknown"


def print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# Main preprocessing
# ============================================================

def preprocess_acn():

    print_section("ACN EV DATA PREPROCESSING")

    # --------------------------------------------------------
    # Check input file
    # --------------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    print(f"Input file: {INPUT_FILE}")

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df = pd.read_csv(INPUT_FILE)

    print(f"Original rows: {len(df):,}")
    print(f"Original columns: {len(df.columns)}")

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "The following required columns are missing:\n"
            + "\n".join(missing_columns)
        )

    print("Required-column check: PASSED")

    # --------------------------------------------------------
    # Remove exact duplicate rows
    # --------------------------------------------------------

    duplicate_count = df.duplicated().sum()

    print(f"Duplicate rows found: {duplicate_count}")

    if duplicate_count > 0:
        df = df.drop_duplicates().reset_index(drop=True)

    # --------------------------------------------------------
    # Preserve original provenance BEFORE transformations
    # --------------------------------------------------------

    if "data_source" in df.columns:

        df["source_type"] = (
            df["data_source"]
            .astype(str)
            .str.strip()
        )

        df["data_provenance"] = (
            df["data_source"]
            .apply(classify_provenance)
        )

    else:

        df["source_type"] = "unknown"
        df["data_provenance"] = "unknown"

    # --------------------------------------------------------
    # Parse timestamps
    # --------------------------------------------------------

    timestamp_columns = [
        "connectionTime",
        "disconnectTime",
        "doneChargingTime",
    ]

    for column in timestamp_columns:

        df[column] = pd.to_datetime(
            df[column],
            errors="coerce",
            utc=True,
        )

    invalid_timestamps = (
        df[timestamp_columns]
        .isna()
        .any(axis=1)
        .sum()
    )

    print(
        f"Rows with invalid timestamps: "
        f"{invalid_timestamps}"
    )

    if invalid_timestamps > 0:

        df = df.dropna(
            subset=timestamp_columns
        ).reset_index(drop=True)

    # --------------------------------------------------------
    # Convert numeric columns
    # --------------------------------------------------------

    numeric_columns = [
        "kWhDelivered",
        "energy_delivered_kwh",
        "energy_needed_kwh",
        "battery_capacity_kwh",
        "current_soc",
        "target_soc",
        "max_charging_power_kw",
        "building_load_kw",
        "grid_capacity_kw",
        "solar_generation_kw",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    numeric_missing = (
        df[numeric_columns]
        .isna()
        .any(axis=1)
        .sum()
    )

    print(
        f"Rows with invalid numeric values: "
        f"{numeric_missing}"
    )

    if numeric_missing > 0:

        df = df.dropna(
            subset=numeric_columns
        ).reset_index(drop=True)

    # --------------------------------------------------------
    # Validate SOC ranges
    # --------------------------------------------------------

    invalid_current_soc = (
        (df["current_soc"] < 0)
        | (df["current_soc"] > 100)
    )

    invalid_target_soc = (
        (df["target_soc"] < 0)
        | (df["target_soc"] > 100)
    )

    invalid_soc = (
        invalid_current_soc
        | invalid_target_soc
    )

    invalid_soc_count = invalid_soc.sum()

    print(
        f"Rows with invalid SOC values: "
        f"{invalid_soc_count}"
    )

    if invalid_soc_count > 0:

        df = df[
            ~invalid_soc
        ].reset_index(drop=True)

    # --------------------------------------------------------
    # Validate battery capacity and charger power
    # --------------------------------------------------------

    invalid_battery = (
        df["battery_capacity_kwh"] <= 0
    )

    invalid_charger = (
        df["max_charging_power_kw"] <= 0
    )

    invalid_power = (
        invalid_battery
        | invalid_charger
    )

    invalid_power_count = invalid_power.sum()

    print(
        "Rows with invalid battery/charger values: "
        f"{invalid_power_count}"
    )

    if invalid_power_count > 0:

        df = df[
            ~invalid_power
        ].reset_index(drop=True)

    # --------------------------------------------------------
    # Validate connection/disconnection ordering
    # --------------------------------------------------------

    invalid_connection = (
        df["disconnectTime"]
        < df["connectionTime"]
    )

    invalid_connection_count = (
        invalid_connection.sum()
    )

    print(
        "Rows with disconnect before connection: "
        f"{invalid_connection_count}"
    )

    if invalid_connection_count > 0:

        df = df[
            ~invalid_connection
        ].reset_index(drop=True)

    # --------------------------------------------------------
    # Check charging completion against departure
    #
    # IMPORTANT:
    # We preserve the original condition separately.
    # We do NOT overwrite the original doneChargingTime.
    # --------------------------------------------------------

    completion_after_disconnect = (
        df["doneChargingTime"]
        > df["disconnectTime"]
    )

    completion_after_disconnect_count = (
        completion_after_disconnect.sum()
    )

    print(
        "Rows where doneChargingTime > disconnectTime: "
        f"{completion_after_disconnect_count}"
    )

    # Preserve the original condition for auditing.
    df["original_completion_after_departure"] = (
        completion_after_disconnect.astype(int)
    )

    df["original_completion_after_departure_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Create effective completion time
    #
    # The simulator should never allow charging after the EV
    # has disconnected.
    #
    # Therefore:
    #
    # effective completion =
    # minimum(done charging time, disconnect time)
    # --------------------------------------------------------

    df["effective_done_charging_time"] = (
        df[
            [
                "doneChargingTime",
                "disconnectTime",
            ]
        ].min(axis=1)
    )

    df["effective_done_charging_time_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Recalculate energy required
    # --------------------------------------------------------

    df["calculated_energy_needed_kwh"] = (
        calculate_energy_needed(
            df["battery_capacity_kwh"],
            df["current_soc"],
            df["target_soc"],
        )
    )

    df["calculated_energy_needed_kwh_origin"] = (
        "calculated"
    )

    # Difference between provided and calculated energy
    df["energy_needed_difference_kwh"] = (
        df["energy_needed_kwh"]
        - df["calculated_energy_needed_kwh"]
    )

    df["energy_needed_difference_kwh_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Calculate session duration
    # --------------------------------------------------------

    df["session_duration_hours_calculated"] = (
        (
            df["disconnectTime"]
            - df["connectionTime"]
        ).dt.total_seconds()
        / 3600.0
    )

    df["session_duration_hours_calculated_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Calculate charging duration
    # --------------------------------------------------------

    df["charging_duration_hours"] = (
        (
            df["effective_done_charging_time"]
            - df["connectionTime"]
        ).dt.total_seconds()
        / 3600.0
    )

    df["charging_duration_hours"] = (
        df["charging_duration_hours"]
        .clip(lower=0)
    )

    df["charging_duration_hours_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Calculate arrival/departure information
    # --------------------------------------------------------

    df["arrival_hour"] = (
        df["connectionTime"].dt.hour
    )

    df["arrival_minute"] = (
        df["connectionTime"].dt.minute
    )

    df["departure_hour"] = (
        df["disconnectTime"].dt.hour
    )

    df["departure_minute"] = (
        df["disconnectTime"].dt.minute
    )

    df["day_of_week"] = (
        df["connectionTime"].dt.dayofweek
    )

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    for column in [
        "arrival_hour",
        "arrival_minute",
        "departure_hour",
        "departure_minute",
        "day_of_week",
        "is_weekend",
    ]:
        df[f"{column}_origin"] = "calculated"

    # --------------------------------------------------------
    # Calculate average charging power
    # --------------------------------------------------------

    df["average_charging_power_kw"] = np.where(
        df["charging_duration_hours"] > 0,
        df["energy_delivered_kwh"]
        / df["charging_duration_hours"],
        0,
    )

    df["average_charging_power_kw_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Calculate available EV charging capacity
    #
    # Main grid constraint:
    #
    # Building Demand
    # + EV Charging
    # - Solar
    # <= Grid Limit
    #
    # Therefore:
    #
    # Available EV Capacity =
    # Grid Limit
    # - Building Demand
    # + Solar
    # --------------------------------------------------------

    df["available_ev_capacity_kw"] = (
        df["grid_capacity_kw"]
        - df["building_load_kw"]
        + df["solar_generation_kw"]
    )

    df["available_ev_capacity_kw"] = (
        df["available_ev_capacity_kw"]
        .clip(lower=0)
    )

    df["available_ev_capacity_kw_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Charging completion status
    #
    # This uses the ORIGINAL timestamps, not the corrected
    # effective timestamp.
    #
    # This preserves the actual data-quality condition.
    # --------------------------------------------------------

    df["charging_complete_before_departure"] = (
        df["doneChargingTime"]
        <= df["disconnectTime"]
    ).astype(int)

    df["charging_complete_before_departure_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Energy consistency check
    # --------------------------------------------------------

    df["energy_delivery_difference_kwh"] = (
        df["kWhDelivered"]
        - df["energy_delivered_kwh"]
    )

    df["energy_delivery_difference_kwh_origin"] = (
        "calculated"
    )

    # --------------------------------------------------------
    # Standardized column names
    # --------------------------------------------------------

    df["timestamp"] = df["connectionTime"]

    df["site_id"] = df["siteID"]

    df["cluster_id"] = df["clusterID"]

    df["station_id"] = df["stationID"]

    df["ev_id_standardized"] = df["ev_id"]

    df["arrival_time"] = df["connectionTime"]

    df["departure_time"] = df["disconnectTime"]

    df["battery_capacity"] = (
        df["battery_capacity_kwh"]
    )

    df["current_soc_percent"] = (
        df["current_soc"]
    )

    df["target_soc_percent"] = (
        df["target_soc"]
    )

    df["energy_required_kwh"] = (
        df["calculated_energy_needed_kwh"]
    )

    df["charger_max_power_kw"] = (
        df["max_charging_power_kw"]
    )

    df["building_demand_kw"] = (
        df["building_load_kw"]
    )

    df["solar_generation_kw_standardized"] = (
        df["solar_generation_kw"]
    )

    df["grid_limit_kw"] = (
        df["grid_capacity_kw"]
    )

    # --------------------------------------------------------
    # Standardized-column provenance
    # --------------------------------------------------------

    standardized_columns = [
        "timestamp",
        "site_id",
        "cluster_id",
        "station_id",
        "ev_id_standardized",
        "arrival_time",
        "departure_time",
        "battery_capacity",
        "current_soc_percent",
        "target_soc_percent",
        "energy_required_kwh",
        "charger_max_power_kw",
        "building_demand_kw",
        "solar_generation_kw_standardized",
        "grid_limit_kw",
    ]

    for column in standardized_columns:
        df[f"{column}_origin"] = (
            "source_or_calculated"
        )

    # --------------------------------------------------------
    # Dataset-level explanation
    #
    # This is useful when we later connect the data to the
    # dashboard and explain where values came from.
    # --------------------------------------------------------

    df["dataset_note"] = np.where(
        df["data_provenance"] == "real_acn",
        "Real ACN session data",
        np.where(
            df["data_provenance"] == "synthetic",
            "Synthetic EV/grid/energy scenario data",
            "Unknown source",
        ),
    )

    # --------------------------------------------------------
    # Sort by arrival time
    # --------------------------------------------------------

    df = df.sort_values(
        "connectionTime"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    print_section("FINAL VALIDATION")

    print(f"Final rows: {len(df):,}")
    print(f"Final columns: {len(df.columns)}")

    print(
        f"Missing values remaining: "
        f"{df.isna().sum().sum()}"
    )

    print(
        f"Duplicate rows remaining: "
        f"{df.duplicated().sum()}"
    )

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    print()
    print("Data provenance:")

    print(
        df["data_provenance"]
        .value_counts(dropna=False)
    )

    # --------------------------------------------------------
    # SOC statistics
    # --------------------------------------------------------

    print()
    print("SOC range:")

    print(
        f"Current SOC: "
        f"{df['current_soc'].min():.2f}% "
        f"→ "
        f"{df['current_soc'].max():.2f}%"
    )

    print(
        f"Target SOC: "
        f"{df['target_soc'].min():.2f}% "
        f"→ "
        f"{df['target_soc'].max():.2f}%"
    )

    # --------------------------------------------------------
    # Energy statistics
    # --------------------------------------------------------

    print()
    print("Energy required:")

    print(
        f"Minimum: "
        f"{df['energy_required_kwh'].min():.2f} kWh"
    )

    print(
        f"Maximum: "
        f"{df['energy_required_kwh'].max():.2f} kWh"
    )

    print(
        f"Mean: "
        f"{df['energy_required_kwh'].mean():.2f} kWh"
    )

    # --------------------------------------------------------
    # Grid capacity statistics
    # --------------------------------------------------------

    print()
    print("Available EV grid capacity:")

    print(
        f"Minimum: "
        f"{df['available_ev_capacity_kw'].min():.2f} kW"
    )

    print(
        f"Maximum: "
        f"{df['available_ev_capacity_kw'].max():.2f} kW"
    )

    # --------------------------------------------------------
    # Completion consistency
    # --------------------------------------------------------

    print()
    print("Charging completion consistency:")

    print(
        "Original sessions completed before departure: "
        f"{df['charging_complete_before_departure'].sum():,}"
        f" / {len(df):,}"
    )

    print(
        "Original sessions completed after departure: "
        f"{df['original_completion_after_departure'].sum():,}"
    )

    # --------------------------------------------------------
    # Real vs synthetic
    # --------------------------------------------------------

    print()
    print("Source summary:")

    for source, count in (
        df["data_provenance"]
        .value_counts()
        .items()
    ):
        print(
            f"  {source}: {count:,} rows"
        )

    # --------------------------------------------------------
    # Save processed dataset
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print_section("PREPROCESSING COMPLETE")

    print("Output file:")
    print(OUTPUT_FILE)

    print(
        f"Output size: "
        f"{OUTPUT_FILE.stat().st_size:,} bytes"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    preprocess_acn()
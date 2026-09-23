"""
EV Scenario Generator
=====================

Generates realistic EV charging scenarios for the Smart EV Charging
& Local Grid Management project.

The processed ACN-derived dataset is used as a REFERENCE dataset for
EV characteristics such as:

- Battery capacity
- Current SOC
- Target SOC
- Charger power
- Cluster information

The original ACN timestamps are NOT replayed directly.

Instead, this generator creates realistic site-specific arrival and
departure behavior.

Supported site types:

- residential
- office
- mall
- campus
- hotel

The generated scenario uses 15-minute time resolution.
"""

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ev_sessions_processed.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
)

RANDOM_SEED = 42

DEFAULT_NUM_EVS = 50

DEFAULT_SITE_TYPE = "residential"

DEFAULT_SCENARIO_DATE = "2026-01-01"


# ============================================================
# SITE PROFILES
# ============================================================

SITE_PROFILES = {

    # --------------------------------------------------------
    # RESIDENTIAL
    # --------------------------------------------------------
    "residential": {
        "arrival_weights": {
            6: 0.01,
            7: 0.02,
            8: 0.02,
            9: 0.03,
            10: 0.04,
            11: 0.05,
            12: 0.06,
            13: 0.07,
            14: 0.10,
            15: 0.14,
            16: 0.15,
            17: 0.14,
            18: 0.10,
            19: 0.06,
            20: 0.03,
            21: 0.02,
            22: 0.01,
        },

        "parking_duration_hours": {
            "min": 4.0,
            "max": 12.0,
            "mean": 7.0,
            "std": 1.8,
        },
    },

    # --------------------------------------------------------
    # OFFICE
    # --------------------------------------------------------
    "office": {
        "arrival_weights": {
            6: 0.01,
            7: 0.04,
            8: 0.18,
            9: 0.28,
            10: 0.18,
            11: 0.08,
            12: 0.05,
            13: 0.04,
            14: 0.03,
            15: 0.03,
            16: 0.02,
            17: 0.02,
            18: 0.01,
            19: 0.01,
            20: 0.01,
        },

        "parking_duration_hours": {
            "min": 5.0,
            "max": 10.0,
            "mean": 8.0,
            "std": 1.2,
        },
    },

    # --------------------------------------------------------
    # MALL
    # --------------------------------------------------------
    "mall": {
        "arrival_weights": {
            8: 0.01,
            9: 0.02,
            10: 0.05,
            11: 0.08,
            12: 0.10,
            13: 0.12,
            14: 0.13,
            15: 0.13,
            16: 0.12,
            17: 0.10,
            18: 0.07,
            19: 0.04,
            20: 0.02,
            21: 0.01,
        },

        "parking_duration_hours": {
            "min": 1.0,
            "max": 6.0,
            "mean": 3.0,
            "std": 1.0,
        },
    },

    # --------------------------------------------------------
    # CAMPUS
    # --------------------------------------------------------
    "campus": {
        "arrival_weights": {
            6: 0.01,
            7: 0.05,
            8: 0.15,
            9: 0.25,
            10: 0.18,
            11: 0.10,
            12: 0.07,
            13: 0.05,
            14: 0.04,
            15: 0.03,
            16: 0.03,
            17: 0.02,
            18: 0.01,
            19: 0.01,
        },

        "parking_duration_hours": {
            "min": 4.0,
            "max": 10.0,
            "mean": 7.0,
            "std": 1.5,
        },
    },

    # --------------------------------------------------------
    # HOTEL
    # --------------------------------------------------------
    "hotel": {
        "arrival_weights": {
            0: 0.02,
            1: 0.02,
            2: 0.02,
            3: 0.02,
            4: 0.02,
            5: 0.02,
            6: 0.03,
            7: 0.04,
            8: 0.05,
            9: 0.06,
            10: 0.07,
            11: 0.08,
            12: 0.08,
            13: 0.08,
            14: 0.08,
            15: 0.08,
            16: 0.08,
            17: 0.07,
            18: 0.06,
            19: 0.05,
            20: 0.04,
            21: 0.03,
            22: 0.02,
            23: 0.02,
        },

        "parking_duration_hours": {
            "min": 3.0,
            "max": 12.0,
            "mean": 7.0,
            "std": 2.0,
        },
    },
}


# ============================================================
# LOAD REFERENCE DATA
# ============================================================

def load_reference_data():
    """
    Load the processed ACN-derived dataset.

    This dataset is used only as a statistical reference for
    generating EV characteristics.

    Original timestamps are not replayed.
    """

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Reference dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE
    )

    required_columns = [
        "ev_id",
        "battery_capacity_kwh",
        "current_soc",
        "target_soc",
        "max_charging_power_kw",
        "clusterID",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Reference dataset is missing required columns: "
            + ", ".join(missing_columns)
        )

    return df


# ============================================================
# VALIDATE SITE TYPE
# ============================================================

def validate_site_type(site_type):
    """
    Validate the requested site type.
    """

    site_type = str(
        site_type
    ).lower().strip()

    if site_type not in SITE_PROFILES:
        valid_types = ", ".join(
            SITE_PROFILES.keys()
        )

        raise ValueError(
            f"Unknown site type: '{site_type}'. "
            f"Valid types are: {valid_types}"
        )

    return site_type


# ============================================================
# SAMPLE ARRIVAL TIME
# ============================================================

def sample_arrival_time(
    site_type,
    scenario_date,
    rng,
):
    """
    Generate an arrival time using the site-specific arrival
    distribution.
    """

    profile = SITE_PROFILES[
        site_type
    ]

    arrival_weights = profile[
        "arrival_weights"
    ]

    hours = np.array(
        list(
            arrival_weights.keys()
        ),
        dtype=int,
    )

    probabilities = np.array(
        list(
            arrival_weights.values()
        ),
        dtype=float,
    )

    probabilities = (
        probabilities
        / probabilities.sum()
    )

    selected_hour = int(
        rng.choice(
            hours,
            p=probabilities,
        )
    )

    # Random minute within the selected hour.
    minute = int(
        rng.integers(
            0,
            60,
        )
    )

    arrival = pd.Timestamp(
        scenario_date
    ).normalize()

    arrival = arrival.replace(
        hour=selected_hour,
        minute=minute,
        second=0,
    )

    # Convert to 15-minute simulation resolution.
    arrival = arrival.round(
        "15min"
    )

    # Safety correction if rounding crosses midnight.
    if arrival.date() != scenario_date.date():

        arrival = (
            pd.Timestamp(
                scenario_date
            ).normalize()
        )

    return arrival


# ============================================================
# SAMPLE PARKING DURATION
# ============================================================

def sample_parking_duration(
    site_type,
    rng,
):
    """
    Generate a realistic parking duration based on site type.
    """

    profile = SITE_PROFILES[
        site_type
    ]

    duration_config = profile[
        "parking_duration_hours"
    ]

    duration = rng.normal(
        loc=duration_config["mean"],
        scale=duration_config["std"],
    )

    duration = np.clip(
        duration,
        duration_config["min"],
        duration_config["max"],
    )

    return float(
        duration
    )


# ============================================================
# GENERATE DEPARTURE TIME
# ============================================================

def generate_departure_time(
    arrival_time,
    site_type,
    rng,
):
    """
    Generate departure time based on arrival and site-specific
    parking duration.
    """

    duration_hours = (
        sample_parking_duration(
            site_type,
            rng,
        )
    )

    departure_time = (
        arrival_time
        + pd.Timedelta(
            hours=duration_hours
        )
    )

    # Round to 15-minute resolution.
    departure_time = departure_time.round(
        "15min"
    )

    # Ensure at least 15 minutes of connection time.
    minimum_departure = (
        arrival_time
        + pd.Timedelta(
            minutes=15
        )
    )

    if departure_time <= arrival_time:

        departure_time = (
            minimum_departure
        )

    return departure_time


# ============================================================
# SAMPLE EV CHARACTERISTICS
# ============================================================

def sample_ev_characteristics(
    reference_df,
    rng,
):
    """
    Sample EV characteristics from the reference dataset.

    We sample an actual reference row instead of independently
    generating every value. This preserves relationships between:

        Battery capacity
        SOC
        Charger power
        Energy requirement
        Cluster
    """

    reference_index = int(
        rng.integers(
            0,
            len(reference_df),
        )
    )

    row = reference_df.iloc[
        reference_index
    ]

    battery_capacity = float(
        row[
            "battery_capacity_kwh"
        ]
    )

    current_soc = float(
        row[
            "current_soc"
        ]
    )

    target_soc = float(
        row[
            "target_soc"
        ]
    )

    charger_power = float(
        row[
            "max_charging_power_kw"
        ]
    )

    cluster_id = int(
        row[
            "clusterID"
        ]
    )

    return {
        "battery_capacity_kwh": battery_capacity,
        "current_soc": current_soc,
        "target_soc": target_soc,
        "max_charging_power_kw": charger_power,
        "cluster_id": cluster_id,
    }


# ============================================================
# GENERATE ONE EV
# ============================================================

def generate_single_ev(
    reference_df,
    ev_number,
    scenario_date,
    site_type,
    rng,
):
    """
    Generate one complete simulated EV.
    """

    # --------------------------------------------------------
    # EV characteristics
    # --------------------------------------------------------

    characteristics = (
        sample_ev_characteristics(
            reference_df,
            rng,
        )
    )

    battery_capacity = (
        characteristics[
            "battery_capacity_kwh"
        ]
    )

    current_soc = (
        characteristics[
            "current_soc"
        ]
    )

    target_soc = (
        characteristics[
            "target_soc"
        ]
    )

    charger_power = (
        characteristics[
            "max_charging_power_kw"
        ]
    )

    cluster_id = (
        characteristics[
            "cluster_id"
        ]
    )

    # --------------------------------------------------------
    # Arrival
    # --------------------------------------------------------

    arrival_time = sample_arrival_time(
        site_type=site_type,
        scenario_date=scenario_date,
        rng=rng,
    )

    # --------------------------------------------------------
    # Departure
    # --------------------------------------------------------

    departure_time = (
        generate_departure_time(
            arrival_time=arrival_time,
            site_type=site_type,
            rng=rng,
        )
    )

    # --------------------------------------------------------
    # Energy required
    # --------------------------------------------------------

    energy_required = (
        battery_capacity
        * (
            target_soc
            - current_soc
        )
        / 100.0
    )

    energy_required = max(
        0.0,
        energy_required,
    )

    # --------------------------------------------------------
    # Parking duration
    # --------------------------------------------------------

    parking_duration_hours = (
        departure_time
        - arrival_time
    ).total_seconds() / 3600.0

    # --------------------------------------------------------
    # Required average power
    # --------------------------------------------------------

    if parking_duration_hours > 0:

        required_average_power = (
            energy_required
            / parking_duration_hours
        )

    else:

        required_average_power = (
            energy_required
        )

    # --------------------------------------------------------
    # Initial status
    # --------------------------------------------------------

    if current_soc >= target_soc:

        charging_status = "complete"

    else:

        charging_status = "waiting"

    # --------------------------------------------------------
    # Create EV record
    # --------------------------------------------------------

    ev = {

        "ev_id": (
            f"EV-{ev_number:03d}"
        ),

        "site_type": site_type,

        "cluster_id": cluster_id,

        "arrival_time": arrival_time,

        "departure_time": departure_time,

        "parking_duration_hours": round(
            parking_duration_hours,
            2,
        ),

        "battery_capacity_kwh": round(
            battery_capacity,
            2,
        ),

        "current_soc": round(
            current_soc,
            2,
        ),

        "target_soc": round(
            target_soc,
            2,
        ),

        "energy_required_kwh": round(
            energy_required,
            2,
        ),

        "max_charging_power_kw": round(
            charger_power,
            2,
        ),

        "required_average_power_kw": round(
            required_average_power,
            2,
        ),

        # Optimizer will update this.
        "charging_power_kw": 0.0,

        # Energy delivered by optimizer.
        "energy_delivered_kwh": 0.0,

        "charging_status": charging_status,

        "charging_complete": False,

        "data_source": (
            "synthetic_from_acn_reference"
        ),

        "timestamp_source": (
            "synthetic_site_profile"
        ),
    }

    return ev


# ============================================================
# GENERATE COMPLETE EV SCENARIO
# ============================================================

def generate_ev_scenario(
    num_evs=DEFAULT_NUM_EVS,
    site_type=DEFAULT_SITE_TYPE,
    scenario_date=DEFAULT_SCENARIO_DATE,
    random_seed=RANDOM_SEED,
):
    """
    Generate a complete EV charging scenario.

    Parameters
    ----------
    num_evs : int
        Number of EVs.

    site_type : str
        Site type.

    scenario_date : str or pandas.Timestamp
        Simulation date.

    random_seed : int
        Random seed.

    Returns
    -------
    pandas.DataFrame
        Generated EV scenario.
    """

    # --------------------------------------------------------
    # Validate number of EVs
    # --------------------------------------------------------

    if num_evs <= 0:

        raise ValueError(
            "num_evs must be greater than 0."
        )

    # --------------------------------------------------------
    # Validate site type
    # --------------------------------------------------------

    site_type = validate_site_type(
        site_type
    )

    # --------------------------------------------------------
    # Scenario date
    # --------------------------------------------------------

    scenario_date = pd.Timestamp(
        scenario_date
    ).normalize()

    # --------------------------------------------------------
    # Random generator
    # --------------------------------------------------------

    rng = np.random.default_rng(
        random_seed
    )

    # --------------------------------------------------------
    # Load reference dataset
    # --------------------------------------------------------

    reference_df = (
        load_reference_data()
    )

    # --------------------------------------------------------
    # Generate EV records
    # --------------------------------------------------------

    ev_records = []

    for ev_number in range(
        1,
        num_evs + 1,
    ):

        ev = generate_single_ev(
            reference_df=reference_df,
            ev_number=ev_number,
            scenario_date=scenario_date,
            site_type=site_type,
            rng=rng,
        )

        ev_records.append(
            ev
        )

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    scenario_df = pd.DataFrame(
        ev_records
    )

    # --------------------------------------------------------
    # Sort by arrival time
    # --------------------------------------------------------

    scenario_df = (
        scenario_df
        .sort_values(
            "arrival_time"
        )
        .reset_index(
            drop=True
        )
    )

    # --------------------------------------------------------
    # Re-number EVs after sorting
    # --------------------------------------------------------

    scenario_df["ev_id"] = [
        f"EV-{number:03d}"
        for number in range(
            1,
            len(scenario_df) + 1,
        )
    ]

    return scenario_df


# ============================================================
# SAVE SCENARIO
# ============================================================

def save_scenario(
    scenario_df,
    filename="ev_scenario.csv",
):
    """
    Save generated EV scenario.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR
        / filename
    )

    scenario_df.to_csv(
        output_file,
        index=False,
    )

    return output_file


# ============================================================
# SCENARIO SUMMARY
# ============================================================

def print_scenario_summary(
    scenario_df,
):
    """
    Print useful information about the generated scenario.
    """

    print()
    print("=" * 70)
    print("EV SCENARIO SUMMARY")
    print("=" * 70)

    print(
        f"Site type: "
        f"{scenario_df['site_type'].iloc[0]}"
    )

    print(
        f"Number of EVs: "
        f"{len(scenario_df)}"
    )

    print(
        f"Scenario date: "
        f"{scenario_df['arrival_time'].dt.date.iloc[0]}"
    )

    print()

    print(
        f"Average battery capacity: "
        f"{scenario_df['battery_capacity_kwh'].mean():.2f} kWh"
    )

    print(
        f"Average current SOC: "
        f"{scenario_df['current_soc'].mean():.2f}%"
    )

    print(
        f"Average energy required: "
        f"{scenario_df['energy_required_kwh'].mean():.2f} kWh"
    )

    print(
        f"Total energy required: "
        f"{scenario_df['energy_required_kwh'].sum():.2f} kWh"
    )

    print(
        f"Average charger power: "
        f"{scenario_df['max_charging_power_kw'].mean():.2f} kW"
    )

    print(
        f"Peak requested charging power "
        f"if all EVs charge simultaneously: "
        f"{scenario_df['max_charging_power_kw'].sum():.2f} kW"
    )

    print(
        f"Average parking duration: "
        f"{scenario_df['parking_duration_hours'].mean():.2f} hours"
    )

    print(
        f"Minimum parking duration: "
        f"{scenario_df['parking_duration_hours'].min():.2f} hours"
    )

    print(
        f"Maximum parking duration: "
        f"{scenario_df['parking_duration_hours'].max():.2f} hours"
    )

    # --------------------------------------------------------
    # Arrival distribution
    # --------------------------------------------------------

    print()
    print("Arrival distribution:")

    arrival_distribution = (
        scenario_df[
            "arrival_time"
        ]
        .dt.hour
        .value_counts()
        .sort_index()
    )

    print(
        arrival_distribution.to_string()
    )

    # --------------------------------------------------------
    # Departure distribution
    # --------------------------------------------------------

    print()
    print("Departure distribution:")

    departure_distribution = (
        scenario_df[
            "departure_time"
        ]
        .dt.hour
        .value_counts()
        .sort_index()
    )

    print(
        departure_distribution.to_string()
    )

    # --------------------------------------------------------
    # Cluster distribution
    # --------------------------------------------------------

    print()
    print("Cluster distribution:")

    cluster_distribution = (
        scenario_df[
            "cluster_id"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        cluster_distribution.to_string()
    )

    # --------------------------------------------------------
    # First EVs
    # --------------------------------------------------------

    print()
    print("First 10 EVs:")

    display_columns = [
        "ev_id",
        "site_type",
        "cluster_id",
        "arrival_time",
        "departure_time",
        "parking_duration_hours",
        "battery_capacity_kwh",
        "current_soc",
        "target_soc",
        "energy_required_kwh",
        "max_charging_power_kw",
        "required_average_power_kw",
    ]

    print(
        scenario_df[
            display_columns
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    print(
        "=" * 70
    )

    print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "Loading ACN reference data..."
    )

    # --------------------------------------------------------
    # Generate residential scenario
    # --------------------------------------------------------

    scenario = generate_ev_scenario(
        num_evs=50,
        site_type="residential",
        scenario_date="2026-01-01",
        random_seed=42,
    )

    print_scenario_summary(
        scenario
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_file = save_scenario(
        scenario,
        filename="ev_scenario_50_residential.csv",
    )

    print(
        f"Scenario saved to:\n{output_file}"
    )
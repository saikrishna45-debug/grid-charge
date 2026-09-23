"""
Smart EV Charging & Local Grid Management
------------------------------------------

Site-level simulation combining:

1. EV charging sessions
2. Building electricity demand
3. Solar renewable generation
4. Grid capacity
5. Uncontrolled EV charging analysis
6. Placeholder for intelligent optimization

Solar generation is loaded from the project's
15-minute Excel solar dataset instead of being
generated using a hard-coded mathematical curve.
"""


# ============================================================
# IMPORTS
# ============================================================

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EV_SCENARIO_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ev_scenario_50_residential.csv"
)

SOLAR_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "solar"
    / "synthetic_solar_24hr_15min.xlsx"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
)


# ============================================================
# DEFAULT CONFIGURATION
# ============================================================

DEFAULT_SITE_CONFIG = {

    "site_id": "SITE-001",

    "site_type": "residential",

    # Maximum allowed power drawn from the grid.
    "grid_limit_kw": 250.0,

    # Building demand simulation parameters.
    "building_base_load_kw": 120.0,

    "building_peak_load_kw": 190.0,

    # Installed solar PV capacity at the site.
    #
    # The Excel dataset contains a 5 kW reference
    # solar profile. The profile will be scaled
    # to this site capacity.
    "solar_capacity_kw": 60.0,

    # Simulation resolution.
    "interval_minutes": 15,

    # Simulation date.
    "simulation_date": "2026-01-01",
}


# ============================================================
# RANDOM SEED
# ============================================================

RANDOM_SEED = 42


# ============================================================
# LOAD EV SCENARIO
# ============================================================

def load_ev_scenario(
    filepath=EV_SCENARIO_FILE,
):
    """
    Load the generated EV scenario.

    Parameters
    ----------
    filepath : Path
        Location of the EV scenario CSV.

    Returns
    -------
    pandas.DataFrame
        EV scenario data.
    """

    if not filepath.exists():

        raise FileNotFoundError(
            f"EV scenario file not found:\n{filepath}"
        )

    ev_df = pd.read_csv(
        filepath
    )

    if ev_df.empty:

        raise ValueError(
            "EV scenario file contains no rows."
        )

    # --------------------------------------------------------
    # Convert timestamps
    # --------------------------------------------------------

    ev_df["arrival_time"] = pd.to_datetime(
        ev_df["arrival_time"]
    )

    ev_df["departure_time"] = pd.to_datetime(
        ev_df["departure_time"]
    )

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    required_columns = [

        "ev_id",

        "arrival_time",

        "departure_time",

        "battery_capacity_kwh",

        "current_soc",

        "target_soc",

        "energy_required_kwh",

        "max_charging_power_kw",
    ]

    missing_columns = [

        column
        for column in required_columns
        if column not in ev_df.columns

    ]

    if missing_columns:

        raise ValueError(
            "EV scenario is missing required columns: "
            + ", ".join(missing_columns)
        )

    return ev_df


# ============================================================
# BUILDING DEMAND PROFILE
# ============================================================

def generate_building_demand(
    timestamps,
    config,
    rng,
):
    """
    Generate a synthetic building electricity-demand profile.

    The profile contains:

    - low overnight demand
    - morning activity
    - stronger evening activity
    - random variation

    This is used as the current building demand
    in the site simulation.
    """

    base_load = float(
        config[
            "building_base_load_kw"
        ]
    )

    peak_load = float(
        config[
            "building_peak_load_kw"
        ]
    )

    demand_values = []

    for timestamp in timestamps:

        hour = (
            timestamp.hour
            +
            timestamp.minute / 60.0
        )

        # ----------------------------------------------------
        # Morning activity
        # ----------------------------------------------------

        morning_center = 8.0

        morning_width = 2.5

        morning_component = np.exp(
            -(
                (
                    hour
                    -
                    morning_center
                )
                ** 2
            )
            /
            (
                2
                *
                morning_width
                ** 2
            )
        )

        # ----------------------------------------------------
        # Evening activity
        # ----------------------------------------------------

        evening_center = 20.0

        evening_width = 3.0

        evening_component = np.exp(
            -(
                (
                    hour
                    -
                    evening_center
                )
                ** 2
            )
            /
            (
                2
                *
                evening_width
                ** 2
            )
        )

        # ----------------------------------------------------
        # Combined activity
        # ----------------------------------------------------

        activity = (
            0.25
            * morning_component
            +
            0.75
            * evening_component
        )

        demand = (
            base_load
            +
            (
                peak_load
                -
                base_load
            )
            * activity
        )

        # ----------------------------------------------------
        # Random variation
        # ----------------------------------------------------

        noise = rng.normal(
            loc=0.0,
            scale=3.0,
        )

        demand += noise

        demand = max(
            0.0,
            demand,
        )

        demand_values.append(
            demand
        )

    return np.array(
        demand_values
    )


# ============================================================
# LOAD SOLAR DATASET
# ============================================================

def load_solar_dataset(
    filepath=SOLAR_DATA_FILE,
):
    """
    Load the solar generation Excel dataset.

    Expected sheet:
        solar_data

    Expected important columns:

        timestamp
        solar_generation_kw
        pv_capacity_kw

    Additional columns such as irradiance,
    temperature and cloud cover are preserved
    when the dataset is loaded.
    """

    if not filepath.exists():

        raise FileNotFoundError(
            f"Solar dataset not found:\n{filepath}"
        )

    # --------------------------------------------------------
    # Read Excel
    # --------------------------------------------------------

    solar_df = pd.read_excel(
        filepath,
        sheet_name="solar_data",
    )

    if solar_df.empty:

        raise ValueError(
            "Solar dataset contains no rows."
        )

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    required_columns = [

        "timestamp",

        "solar_generation_kw",

        "pv_capacity_kw",
    ]

    missing_columns = [

        column
        for column in required_columns
        if column not in solar_df.columns

    ]

    if missing_columns:

        raise ValueError(
            "Solar dataset is missing required columns: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # Convert timestamp
    # --------------------------------------------------------

    solar_df["timestamp"] = pd.to_datetime(
        solar_df["timestamp"]
    )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    solar_df = solar_df.sort_values(
        "timestamp"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Convert numeric columns
    # --------------------------------------------------------

    solar_df["solar_generation_kw"] = pd.to_numeric(
        solar_df["solar_generation_kw"],
        errors="coerce",
    )

    solar_df["pv_capacity_kw"] = pd.to_numeric(
        solar_df["pv_capacity_kw"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------------

    solar_df = solar_df.dropna(
        subset=[
            "timestamp",
            "solar_generation_kw",
            "pv_capacity_kw",
        ]
    ).reset_index(
        drop=True
    )

    if solar_df.empty:

        raise ValueError(
            "No valid rows remain in the solar dataset."
        )

    # --------------------------------------------------------
    # Validate PV capacity
    # --------------------------------------------------------

    reference_capacity = float(
        solar_df[
            "pv_capacity_kw"
        ].iloc[0]
    )

    if reference_capacity <= 0:

        raise ValueError(
            "Solar dataset PV capacity must be greater than zero."
        )

    # --------------------------------------------------------
    # Validate solar generation
    # --------------------------------------------------------

    if (
        solar_df[
            "solar_generation_kw"
        ]
        < 0
    ).any():

        raise ValueError(
            "Solar generation contains negative values."
        )

    # --------------------------------------------------------
    # Validate generation against capacity
    # --------------------------------------------------------

    maximum_generation = float(
        solar_df[
            "solar_generation_kw"
        ].max()
    )

    if maximum_generation > reference_capacity:

        print(
            "WARNING: Solar generation exceeds "
            "the reference PV capacity."
        )

    return solar_df


# ============================================================
# GENERATE SOLAR PROFILE FROM DATASET
# ============================================================

def generate_solar_generation(
    timestamps,
    config,
    solar_df,
):
    """
    Generate site solar generation using the provided
    15-minute solar dataset.

    The dataset contains a reference PV capacity.

    Example:

        Dataset PV capacity = 5 kW
        Site PV capacity    = 60 kW

    A dataset value of 4.0 kW becomes:

        (4.0 / 5.0) * 60
        = 48 kW

    This preserves the shape of the solar profile
    while allowing configurable site PV capacity.
    """

    site_solar_capacity = float(
        config[
            "solar_capacity_kw"
        ]
    )

    if site_solar_capacity < 0:

        raise ValueError(
            "solar_capacity_kw cannot be negative."
        )

    # --------------------------------------------------------
    # Reference capacity
    # --------------------------------------------------------

    reference_capacity = float(
        solar_df[
            "pv_capacity_kw"
        ].iloc[0]
    )

    if reference_capacity <= 0:

        raise ValueError(
            "Reference PV capacity must be greater than zero."
        )

    # --------------------------------------------------------
    # Create normalized time-of-day profile
    # --------------------------------------------------------

    solar_reference = solar_df.copy()

    solar_reference["time_key"] = (
        solar_reference[
            "timestamp"
        ].dt.hour
        * 60
        +
        solar_reference[
            "timestamp"
        ].dt.minute
    )

    # --------------------------------------------------------
    # Create lookup dictionary
    # --------------------------------------------------------

    solar_lookup = dict(
        zip(
            solar_reference[
                "time_key"
            ],
            solar_reference[
                "solar_generation_kw"
            ],
        )
    )

    solar_values = []

    for timestamp in timestamps:

        time_key = (
            timestamp.hour * 60
            +
            timestamp.minute
        )

        # ----------------------------------------------------
        # Find matching 15-minute solar value
        # ----------------------------------------------------

        if time_key in solar_lookup:

            reference_generation = float(
                solar_lookup[
                    time_key
                ]
            )

        else:

            # ------------------------------------------------
            # If an exact timestamp is unavailable,
            # use zero rather than inventing a value.
            # ------------------------------------------------

            reference_generation = 0.0

        # ----------------------------------------------------
        # Scale reference profile to site capacity
        # ----------------------------------------------------

        solar_power = (
            reference_generation
            /
            reference_capacity
        ) * site_solar_capacity

        solar_power = max(
            0.0,
            solar_power,
        )

        # ----------------------------------------------------
        # Never exceed installed site capacity
        # ----------------------------------------------------

        solar_power = min(
            solar_power,
            site_solar_capacity,
        )

        solar_values.append(
            solar_power
        )

    return np.array(
        solar_values
    )


# ============================================================
# CONNECTED EV CALCULATION
# ============================================================

def get_connected_evs(
    ev_df,
    timestamp,
):
    """
    Return EVs connected at a particular timestamp.

    An EV is connected when:

        arrival_time <= timestamp < departure_time
    """

    connected = ev_df[
        (
            ev_df["arrival_time"]
            <= timestamp
        )
        &
        (
            ev_df["departure_time"]
            > timestamp
        )
    ].copy()

    return connected


# ============================================================
# SITE SIMULATION
# ============================================================

def simulate_site(
    ev_df,
    config=None,
    random_seed=RANDOM_SEED,
    solar_df=None,
):
    """
    Create the complete 15-minute site simulation.

    Parameters
    ----------
    ev_df : pandas.DataFrame
        Generated EV scenario.

    config : dict, optional
        Site configuration.

    random_seed : int
        Random seed.

    solar_df : pandas.DataFrame, optional
        Solar dataset.

    Returns
    -------
    pandas.DataFrame
        Site simulation timeline.
    """

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    if config is None:

        config = (
            DEFAULT_SITE_CONFIG.copy()
        )

    else:

        merged_config = (
            DEFAULT_SITE_CONFIG.copy()
        )

        merged_config.update(
            config
        )

        config = merged_config

    # --------------------------------------------------------
    # Validate EV data
    # --------------------------------------------------------

    if ev_df.empty:

        raise ValueError(
            "EV scenario contains no EVs."
        )

    # --------------------------------------------------------
    # Load solar dataset if not supplied
    # --------------------------------------------------------

    if solar_df is None:

        solar_df = (
            load_solar_dataset()
        )

    # --------------------------------------------------------
    # Random generator
    # --------------------------------------------------------

    rng = np.random.default_rng(
        random_seed
    )

    # --------------------------------------------------------
    # Simulation boundaries
    # --------------------------------------------------------

    simulation_date = pd.Timestamp(
        config[
            "simulation_date"
        ]
    )

    start_time = (
        simulation_date.normalize()
    )

    end_time = (
        start_time
        +
        pd.Timedelta(
            days=1
        )
        -
        pd.Timedelta(
            minutes=config[
                "interval_minutes"
            ]
        )
    )

    # --------------------------------------------------------
    # Create timeline
    # --------------------------------------------------------

    timestamps = pd.date_range(
        start=start_time,
        end=end_time,
        freq=(
            f'{config["interval_minutes"]}min'
        ),
    )

    # --------------------------------------------------------
    # Generate building demand
    # --------------------------------------------------------

    building_demand = (
        generate_building_demand(
            timestamps=timestamps,
            config=config,
            rng=rng,
        )
    )

    # --------------------------------------------------------
    # Generate solar from Excel dataset
    # --------------------------------------------------------

    solar_generation = (
        generate_solar_generation(
            timestamps=timestamps,
            config=config,
            solar_df=solar_df,
        )
    )

    # --------------------------------------------------------
    # Simulation rows
    # --------------------------------------------------------

    simulation_rows = []

    for index, timestamp in enumerate(
        timestamps
    ):

        # ====================================================
        # CONNECTED EVs
        # ====================================================

        connected_evs = (
            get_connected_evs(
                ev_df,
                timestamp,
            )
        )

        connected_ev_count = len(
            connected_evs
        )

        # ----------------------------------------------------
        # Connected EV IDs
        # ----------------------------------------------------

        if connected_ev_count > 0:

            connected_ev_ids = ",".join(
                connected_evs[
                    "ev_id"
                ].astype(str)
            )

        else:

            connected_ev_ids = ""

        # ====================================================
        # CURRENT BUILDING DEMAND
        # ====================================================

        current_building_demand = float(
            building_demand[
                index
            ]
        )

        # ====================================================
        # CURRENT SOLAR
        # ====================================================

        current_solar_generation = float(
            solar_generation[
                index
            ]
        )

        # ====================================================
        # REQUESTED EV POWER
        # ====================================================

        if connected_ev_count > 0:

            requested_ev_power = float(
                connected_evs[
                    "max_charging_power_kw"
                ].sum()
            )

        else:

            requested_ev_power = 0.0

        # ====================================================
        # TOTAL ENERGY STILL REQUIRED
        # ====================================================

        if connected_ev_count > 0:

            total_energy_required = float(
                connected_evs[
                    "energy_required_kwh"
                ].sum()
            )

        else:

            total_energy_required = 0.0

        # ====================================================
        # AVAILABLE EV CAPACITY
        # ====================================================

        available_ev_capacity = (
            config[
                "grid_limit_kw"
            ]
            -
            current_building_demand
            +
            current_solar_generation
        )

        available_ev_capacity = max(
            0.0,
            available_ev_capacity,
        )

        # ====================================================
        # UTILIZATION OF AVAILABLE EV CAPACITY
        # ====================================================

        if available_ev_capacity > 0:

            requested_capacity_ratio = (
                requested_ev_power
                /
                available_ev_capacity
            )

        else:

            requested_capacity_ratio = (
                np.inf
                if requested_ev_power > 0
                else 0.0
            )

        # ====================================================
        # UNCONTROLLED SITE DEMAND
        # ====================================================

        uncontrolled_site_demand = (
            current_building_demand
            +
            requested_ev_power
            -
            current_solar_generation
        )

        # ====================================================
        # GRID OVERLOAD
        # ====================================================

        overload_without_control = max(
            0.0,
            uncontrolled_site_demand
            -
            config[
                "grid_limit_kw"
            ],
        )

        # ====================================================
        # GRID UTILIZATION
        # ====================================================

        if (
            config[
                "grid_limit_kw"
            ]
            > 0
        ):

            grid_utilization = (
                uncontrolled_site_demand
                /
                config[
                    "grid_limit_kw"
                ]
            ) * 100.0

        else:

            grid_utilization = 0.0

        # ====================================================
        # AVAILABLE CAPACITY AFTER REQUESTED EV POWER
        # ====================================================

        remaining_capacity_after_request = (
            available_ev_capacity
            -
            requested_ev_power
        )

        # ====================================================
        # OPTIMIZER PLACEHOLDER
        # ====================================================

        optimized_ev_power = 0.0

        controlled_site_demand = (
            current_building_demand
            -
            current_solar_generation
            +
            optimized_ev_power
        )

        # ====================================================
        # CONTROLLED GRID UTILIZATION
        # ====================================================

        if (
            config[
                "grid_limit_kw"
            ]
            > 0
        ):

            controlled_grid_utilization = (
                controlled_site_demand
                /
                config[
                    "grid_limit_kw"
                ]
            ) * 100.0

        else:

            controlled_grid_utilization = 0.0

        # ====================================================
        # APPEND ROW
        # ====================================================

        simulation_rows.append(
            {

                # ------------------------------------------------
                # Time
                # ------------------------------------------------

                "timestamp": timestamp,

                # ------------------------------------------------
                # Site
                # ------------------------------------------------

                "site_id": config[
                    "site_id"
                ],

                "site_type": config[
                    "site_type"
                ],

                # ------------------------------------------------
                # Building
                # ------------------------------------------------

                "building_demand_kw": round(
                    current_building_demand,
                    3,
                ),

                # ------------------------------------------------
                # Solar
                # ------------------------------------------------

                "solar_generation_kw": round(
                    current_solar_generation,
                    3,
                ),

                "pv_capacity_kw": round(
                    config[
                        "solar_capacity_kw"
                    ],
                    3,
                ),

                # ------------------------------------------------
                # Grid
                # ------------------------------------------------

                "grid_limit_kw": round(
                    config[
                        "grid_limit_kw"
                    ],
                    3,
                ),

                "available_ev_capacity_kw": round(
                    available_ev_capacity,
                    3,
                ),

                # ------------------------------------------------
                # EV state
                # ------------------------------------------------

                "connected_ev_count": (
                    connected_ev_count
                ),

                "connected_ev_ids": (
                    connected_ev_ids
                ),

                "requested_ev_power_kw": round(
                    requested_ev_power,
                    3,
                ),

                "total_energy_required_kwh": round(
                    total_energy_required,
                    3,
                ),

                # ------------------------------------------------
                # Capacity analysis
                # ------------------------------------------------

                "requested_capacity_ratio": (
                    round(
                        requested_capacity_ratio,
                        3,
                    )
                    if np.isfinite(
                        requested_capacity_ratio
                    )
                    else np.inf
                ),

                "remaining_capacity_after_request_kw": round(
                    remaining_capacity_after_request,
                    3,
                ),

                # ------------------------------------------------
                # Uncontrolled scenario
                # ------------------------------------------------

                "uncontrolled_site_demand_kw": round(
                    uncontrolled_site_demand,
                    3,
                ),

                "overload_without_control_kw": round(
                    overload_without_control,
                    3,
                ),

                "grid_utilization_percent": round(
                    grid_utilization,
                    2,
                ),

                # ------------------------------------------------
                # Optimizer placeholder
                # ------------------------------------------------

                "optimized_ev_power_kw": round(
                    optimized_ev_power,
                    3,
                ),

                "controlled_site_demand_kw": round(
                    controlled_site_demand,
                    3,
                ),

                "controlled_grid_utilization_percent": round(
                    controlled_grid_utilization,
                    2,
                ),
            }
        )

    # --------------------------------------------------------
    # Create DataFrame
    # --------------------------------------------------------

    simulation_df = pd.DataFrame(
        simulation_rows
    )

    return simulation_df


# ============================================================
# SAVE SIMULATION
# ============================================================

def save_simulation(
    simulation_df,
    filename="site_simulation.csv",
):
    """
    Save site simulation to data/synthetic/.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR
        /
        filename
    )

    simulation_df.to_csv(
        output_file,
        index=False,
    )

    return output_file


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_simulation_summary(
    simulation_df,
):
    """
    Print useful simulation statistics.
    """

    print()

    print(
        "=" * 70
    )

    print(
        "SITE SIMULATION SUMMARY"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # Basic information
    # --------------------------------------------------------

    print(
        f"Simulation intervals: "
        f"{len(simulation_df)}"
    )

    print(
        f"Simulation start: "
        f"{simulation_df['timestamp'].min()}"
    )

    print(
        f"Simulation end: "
        f"{simulation_df['timestamp'].max()}"
    )

    print()

    # --------------------------------------------------------
    # Building
    # --------------------------------------------------------

    print(
        f"Peak building demand: "
        f"{simulation_df['building_demand_kw'].max():.2f} kW"
    )

    print(
        f"Minimum building demand: "
        f"{simulation_df['building_demand_kw'].min():.2f} kW"
    )

    # --------------------------------------------------------
    # Solar
    # --------------------------------------------------------

    print(
        f"Configured PV capacity: "
        f"{simulation_df['pv_capacity_kw'].iloc[0]:.2f} kW"
    )

    print(
        f"Peak solar generation: "
        f"{simulation_df['solar_generation_kw'].max():.2f} kW"
    )

    # --------------------------------------------------------
    # EVs
    # --------------------------------------------------------

    print(
        f"Peak connected EVs: "
        f"{simulation_df['connected_ev_count'].max()}"
    )

    print(
        f"Peak requested EV charging: "
        f"{simulation_df['requested_ev_power_kw'].max():.2f} kW"
    )

    print(
        f"Total energy required "
        f"across EV sessions: "
        f"{simulation_df['total_energy_required_kwh'].max():.2f} kWh"
    )

    # --------------------------------------------------------
    # Grid capacity
    # --------------------------------------------------------

    print(
        f"Maximum available EV capacity: "
        f"{simulation_df['available_ev_capacity_kw'].max():.2f} kW"
    )

    print(
        f"Minimum available EV capacity: "
        f"{simulation_df['available_ev_capacity_kw'].min():.2f} kW"
    )

    print()

    # --------------------------------------------------------
    # Overload
    # --------------------------------------------------------

    overload_intervals = int(
        (
            simulation_df[
                "overload_without_control_kw"
            ]
            > 0
        ).sum()
    )

    print(
        f"Intervals that would overload "
        f"the grid without EV control: "
        f"{overload_intervals}"
    )

    print(
        f"Maximum uncontrolled overload: "
        f"{simulation_df['overload_without_control_kw'].max():.2f} kW"
    )

    print(
        f"Maximum uncontrolled grid utilization: "
        f"{simulation_df['grid_utilization_percent'].max():.2f}%"
    )

    # --------------------------------------------------------
    # Capacity stress
    # --------------------------------------------------------

    overloaded_request_intervals = int(
        (
            simulation_df[
                "remaining_capacity_after_request_kw"
            ]
            < 0
        ).sum()
    )

    print(
        f"Intervals where requested EV power "
        f"exceeds available capacity: "
        f"{overloaded_request_intervals}"
    )

    print()

    # --------------------------------------------------------
    # Timeline sample
    # --------------------------------------------------------

    print(
        "Sample timeline:"
    )

    sample_columns = [

        "timestamp",

        "building_demand_kw",

        "solar_generation_kw",

        "pv_capacity_kw",

        "grid_limit_kw",

        "available_ev_capacity_kw",

        "connected_ev_count",

        "requested_ev_power_kw",

        "remaining_capacity_after_request_kw",

        "overload_without_control_kw",

    ]

    print(
        simulation_df[
            sample_columns
        ]
        .head(20)
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
        "Loading EV scenario..."
    )

    ev_scenario = (
        load_ev_scenario()
    )

    print(
        f"Loaded "
        f"{len(ev_scenario)} EVs."
    )

    # --------------------------------------------------------
    # Detect site type from scenario
    # --------------------------------------------------------

    if "site_type" in ev_scenario.columns:

        scenario_site_type = str(
            ev_scenario[
                "site_type"
            ].iloc[0]
        )

    else:

        scenario_site_type = (
            "residential"
        )

    print(
        f"Scenario site type: "
        f"{scenario_site_type}"
    )

    print()

    # --------------------------------------------------------
    # Load solar dataset
    # --------------------------------------------------------

    print(
        "Loading solar dataset..."
    )

    solar_dataset = (
        load_solar_dataset()
    )

    print(
        f"Loaded "
        f"{len(solar_dataset)} solar records."
    )

    print(
        f"Reference PV capacity: "
        f"{solar_dataset['pv_capacity_kw'].iloc[0]:.2f} kW"
    )

    print(
        f"Reference peak solar generation: "
        f"{solar_dataset['solar_generation_kw'].max():.2f} kW"
    )

    print()

    # --------------------------------------------------------
    # Generate site simulation
    # --------------------------------------------------------

    print(
        "Generating site simulation..."
    )

    site_simulation = (
        simulate_site(

            ev_df=ev_scenario,

            solar_df=solar_dataset,

            config={

                "site_id": "SITE-001",

                "site_type": (
                    scenario_site_type
                ),

                "grid_limit_kw": 250.0,

                "building_base_load_kw": 120.0,

                "building_peak_load_kw": 190.0,

                # ------------------------------------------------
                # IMPORTANT:
                #
                # The reference solar dataset is 5 kW.
                # We scale it to 60 kW for this site.
                # ------------------------------------------------

                "solar_capacity_kw": 60.0,

                "interval_minutes": 15,

                "simulation_date": (
                    "2026-01-01"
                ),
            },

            random_seed=42,
        )
    )

    # --------------------------------------------------------
    # Print summary
    # --------------------------------------------------------

    print_simulation_summary(
        site_simulation
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_file = (
        save_simulation(
            site_simulation,

            filename=(
                "site_simulation_50ev_residential.csv"
            ),
        )
    )

    print(
        f"Simulation saved to:\n"
        f"{output_file}"
    )
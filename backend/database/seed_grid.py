from pathlib import Path

import pandas as pd

from backend.database.database import SessionLocal
from backend.database.models import GridMeasurement


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GRID_SIMULATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "optimized_site_simulation_v3_50ev_residential.csv"
)


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def parse_datetime(value):
    """
    Convert a CSV timestamp into a Python datetime.
    """

    timestamp = pd.to_datetime(value, errors="coerce")

    if pd.isna(timestamp):
        return None

    # Remove timezone information for SQLite compatibility.
    if getattr(timestamp, "tzinfo", None) is not None:
        timestamp = timestamp.tz_localize(None)

    return timestamp.to_pydatetime()


def safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """

    try:
        number = float(value)

        if pd.isna(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------
# Database seeding
# ---------------------------------------------------------

def seed_grid_measurements():
    """
    Load the V3 optimized site simulation and insert
    grid measurements into SQLite.
    """

    if not GRID_SIMULATION_FILE.exists():
        raise FileNotFoundError(
            "Grid simulation file not found:\n"
            f"{GRID_SIMULATION_FILE}"
        )

    print("Loading V3 optimized grid simulation...")

    df = pd.read_csv(GRID_SIMULATION_FILE)

    if df.empty:
        raise ValueError(
            "Grid simulation file is empty."
        )

    print(f"Records found: {len(df)}")

    # -----------------------------------------------------
    # Required columns
    # -----------------------------------------------------

    required_columns = [
        "timestamp",
        "building_demand_kw",
        "solar_generation_kw",
        "grid_limit_kw",
        "optimized_ev_charging_kw",
        "grid_utilization_percent",
        "controlled_overload_kw",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # -----------------------------------------------------
    # Database session
    # -----------------------------------------------------

    db = SessionLocal()

    try:

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():

            timestamp = parse_datetime(
                row["timestamp"]
            )

            if timestamp is None:
                print(
                    "Skipping record with invalid timestamp."
                )
                skipped += 1
                continue

            # -------------------------------------------------
            # Prevent duplicate measurements
            # -------------------------------------------------

            existing = (
                db.query(GridMeasurement)
                .filter(
                    GridMeasurement.timestamp == timestamp
                )
                .first()
            )

            if existing:
                skipped += 1
                continue

            # -------------------------------------------------
            # Read values
            # -------------------------------------------------

            building_demand = safe_float(
                row["building_demand_kw"]
            )

            solar_generation = safe_float(
                row["solar_generation_kw"]
            )

            grid_limit = safe_float(
                row["grid_limit_kw"]
            )

            ev_charging = safe_float(
                row["optimized_ev_charging_kw"]
            )

            grid_utilization = safe_float(
                row["grid_utilization_percent"]
            )

            overload = safe_float(
                row["controlled_overload_kw"]
            )

            # -------------------------------------------------
            # Basic validation
            # -------------------------------------------------

            if building_demand < 0:
                print(
                    f"Skipping {timestamp}: "
                    "negative building demand."
                )
                skipped += 1
                continue

            if solar_generation < 0:
                print(
                    f"Skipping {timestamp}: "
                    "negative solar generation."
                )
                skipped += 1
                continue

            if grid_limit <= 0:
                print(
                    f"Skipping {timestamp}: "
                    "invalid grid limit."
                )
                skipped += 1
                continue

            if ev_charging < 0:
                print(
                    f"Skipping {timestamp}: "
                    "negative EV charging."
                )
                skipped += 1
                continue

            # -------------------------------------------------
            # Create grid measurement
            # -------------------------------------------------

            measurement = GridMeasurement(
                timestamp=timestamp,
                building_demand_kw=building_demand,
                solar_generation_kw=solar_generation,
                grid_limit_kw=grid_limit,
                ev_charging_power_kw=ev_charging,
                grid_utilization_percent=grid_utilization,
                overload_kw=overload,
            )

            db.add(measurement)

            inserted += 1

        # -----------------------------------------------------
        # Commit changes
        # -----------------------------------------------------

        db.commit()

        print()
        print("=" * 55)
        print("GRID DATABASE SEEDING COMPLETED")
        print("=" * 55)
        print(f"Inserted measurements: {inserted}")
        print(f"Skipped measurements:  {skipped}")
        print(f"Simulation records:    {len(df)}")
        print("=" * 55)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    seed_grid_measurements()
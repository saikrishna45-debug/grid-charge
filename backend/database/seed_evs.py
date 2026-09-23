from pathlib import Path

import pandas as pd

from backend.database.database import SessionLocal
from backend.database.models import EV


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EV_SCENARIO_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ev_scenario_50_residential.csv"
)


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def parse_datetime(value):
    """
    Convert a CSV datetime value into a Python datetime.
    """

    timestamp = pd.to_datetime(value, errors="coerce")

    if pd.isna(timestamp):
        return None

    # SQLite DateTime columns currently use naive datetimes.
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

def seed_evs():
    """
    Load the 50-EV residential simulation scenario
    and insert the EVs into SQLite.
    """

    if not EV_SCENARIO_FILE.exists():
        raise FileNotFoundError(
            f"EV scenario file not found:\n{EV_SCENARIO_FILE}"
        )

    print("Loading 50-EV residential scenario...")

    df = pd.read_csv(EV_SCENARIO_FILE)

    if df.empty:
        raise ValueError("EV scenario file is empty.")

    print(f"Records found: {len(df)}")

    # -----------------------------------------------------
    # Required columns
    # -----------------------------------------------------

    required_columns = [
        "ev_id",
        "arrival_time",
        "departure_time",
        "battery_capacity_kwh",
        "current_soc",
        "target_soc",
        "max_charging_power_kw",
        "charging_status",
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

            ev_id = str(row["ev_id"]).strip()

            if not ev_id:
                print("Skipping record with empty EV ID.")
                skipped += 1
                continue

            # -------------------------------------------------
            # Check for existing EV
            # -------------------------------------------------

            existing_ev = (
                db.query(EV)
                .filter(EV.ev_id == ev_id)
                .first()
            )

            if existing_ev:
                skipped += 1
                continue

            # -------------------------------------------------
            # Read EV values
            # -------------------------------------------------

            battery_capacity = safe_float(
                row["battery_capacity_kwh"]
            )

            current_soc = safe_float(
                row["current_soc"]
            )

            target_soc = safe_float(
                row["target_soc"]
            )

            max_charging_power = safe_float(
                row["max_charging_power_kw"]
            )

            arrival_time = parse_datetime(
                row["arrival_time"]
            )

            departure_time = parse_datetime(
                row["departure_time"]
            )

            charging_status = str(
                row["charging_status"]
            ).strip()

            # -------------------------------------------------
            # Validate values
            # -------------------------------------------------

            if battery_capacity <= 0:
                print(
                    f"Skipping {ev_id}: "
                    "invalid battery capacity."
                )
                skipped += 1
                continue

            if not 0 <= current_soc <= 100:
                print(
                    f"Skipping {ev_id}: "
                    "invalid current SOC."
                )
                skipped += 1
                continue

            if not 0 <= target_soc <= 100:
                print(
                    f"Skipping {ev_id}: "
                    "invalid target SOC."
                )
                skipped += 1
                continue

            if max_charging_power <= 0:
                print(
                    f"Skipping {ev_id}: "
                    "invalid charging power."
                )
                skipped += 1
                continue

            if arrival_time is None:
                print(
                    f"Skipping {ev_id}: "
                    "invalid arrival time."
                )
                skipped += 1
                continue

            if departure_time is None:
                print(
                    f"Skipping {ev_id}: "
                    "invalid departure time."
                )
                skipped += 1
                continue

            if departure_time <= arrival_time:
                print(
                    f"Skipping {ev_id}: "
                    "departure must be after arrival."
                )
                skipped += 1
                continue

            # -------------------------------------------------
            # Create database record
            # -------------------------------------------------

            ev = EV(
                ev_id=ev_id,
                battery_capacity_kwh=battery_capacity,
                current_soc_percent=current_soc,
                target_soc_percent=target_soc,
                arrival_time=arrival_time,
                departure_time=departure_time,
                max_charging_power_kw=max_charging_power,
                charging_status=charging_status,
            )

            db.add(ev)
            inserted += 1

        # -----------------------------------------------------
        # Commit
        # -----------------------------------------------------

        db.commit()

        print()
        print("=" * 55)
        print("EV DATABASE SEEDING COMPLETED")
        print("=" * 55)
        print(f"Inserted EVs:    {inserted}")
        print(f"Skipped EVs:     {skipped}")
        print(f"Scenario rows:   {len(df)}")
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
    seed_evs()
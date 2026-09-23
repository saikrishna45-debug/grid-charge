from pathlib import Path

import pandas as pd

from backend.database.database import SessionLocal
from backend.database.models import ChargingSession


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCENARIO_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ev_scenario_50_residential.csv"
)

RESULTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ev_optimization_results_v3_50ev_residential.csv"
)


def parse_datetime(value):
    """Convert a timestamp to a timezone-naive Python datetime."""

    timestamp = pd.to_datetime(value, errors="coerce")

    if pd.isna(timestamp):
        return None

    if getattr(timestamp, "tzinfo", None) is not None:
        timestamp = timestamp.tz_localize(None)

    return timestamp.to_pydatetime()


def safe_float(value, default=0.0):
    """Safely convert a value to float."""

    try:
        number = float(value)

        if pd.isna(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def safe_bool(value):
    """Safely convert common CSV boolean values to bool."""

    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


def seed_charging_sessions():
    """Create one charging-session record for each EV."""

    if not SCENARIO_FILE.exists():
        raise FileNotFoundError(
            f"EV scenario file not found: {SCENARIO_FILE}"
        )

    if not RESULTS_FILE.exists():
        raise FileNotFoundError(
            f"EV optimization results file not found: {RESULTS_FILE}"
        )

    print("Loading EV scenario...")

    scenario_df = pd.read_csv(SCENARIO_FILE)

    print("Loading V3 optimization results...")

    results_df = pd.read_csv(RESULTS_FILE)

    if scenario_df.empty:
        raise ValueError(
            "EV scenario file contains no records."
        )

    if results_df.empty:
        raise ValueError(
            "EV optimization results file contains no records."
        )

    required_scenario_columns = [
        "ev_id",
        "arrival_time",
        "departure_time",
        "max_charging_power_kw",
    ]

    required_result_columns = [
        "ev_id",
        "energy_delivered_kwh",
        "charging_complete",
        "deadline_missed",
    ]

    missing_scenario = [
        column
        for column in required_scenario_columns
        if column not in scenario_df.columns
    ]

    missing_results = [
        column
        for column in required_result_columns
        if column not in results_df.columns
    ]

    if missing_scenario:
        raise ValueError(
            f"Scenario file is missing columns: {missing_scenario}"
        )

    if missing_results:
        raise ValueError(
            f"Results file is missing columns: {missing_results}"
        )

    # Keep only the columns needed for session creation.
    scenario = scenario_df[
        required_scenario_columns
    ].copy()

    results = results_df[
        required_result_columns
    ].copy()

    # Make sure each EV appears only once.
    if scenario["ev_id"].duplicated().any():
        raise ValueError(
            "Scenario contains duplicate EV IDs."
        )

    if results["ev_id"].duplicated().any():
        raise ValueError(
            "Optimization results contain duplicate EV IDs."
        )

    # Combine the two sources using EV ID.
    merged = scenario.merge(
        results,
        on="ev_id",
        how="inner",
        validate="one_to_one",
    )

    if len(merged) != len(scenario):
        raise ValueError(
            "Not every EV in the scenario has a matching "
            "optimization result."
        )

    print(f"EV sessions to create: {len(merged)}")

    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        for _, row in merged.iterrows():

            ev_id = str(row["ev_id"]).strip()

            if not ev_id:
                skipped += 1
                continue

            start_time = parse_datetime(
                row["arrival_time"]
            )

            departure_time = parse_datetime(
                row["departure_time"]
            )

            if start_time is None or departure_time is None:
                print(
                    f"Skipping {ev_id}: invalid session timestamps."
                )
                skipped += 1
                continue

            if departure_time <= start_time:
                print(
                    f"Skipping {ev_id}: departure is not after arrival."
                )
                skipped += 1
                continue

            energy_delivered = safe_float(
                row["energy_delivered_kwh"]
            )

            max_charging_power = safe_float(
                row["max_charging_power_kw"]
            )

            charging_complete = safe_bool(
                row["charging_complete"]
            )

            deadline_missed = safe_bool(
                row["deadline_missed"]
            )

            if energy_delivered < 0:
                print(
                    f"Skipping {ev_id}: negative energy delivered."
                )
                skipped += 1
                continue

            if max_charging_power <= 0:
                print(
                    f"Skipping {ev_id}: invalid maximum charging power."
                )
                skipped += 1
                continue

            existing_session = (
                db.query(ChargingSession)
                .filter(
                    ChargingSession.session_id
                    == f"SESSION-{ev_id}"
                )
                .first()
            )

            if existing_session:
                skipped += 1
                continue

            if charging_complete:
                completion_status = "completed"
            elif deadline_missed:
                completion_status = "deadline_missed"
            else:
                completion_status = "incomplete"

            session = ChargingSession(
                session_id=f"SESSION-{ev_id}",
                ev_id=ev_id,
                start_time=start_time,
                end_time=departure_time,
                energy_delivered_kwh=energy_delivered,
                charging_power_kw=max_charging_power,
                completion_status=completion_status,
            )

            db.add(session)
            inserted += 1

        db.commit()

        print("=" * 60)
        print("CHARGING SESSION DATABASE SEEDING COMPLETED")
        print("=" * 60)
        print(f"Inserted sessions: {inserted}")
        print(f"Skipped sessions:  {skipped}")
        print(f"Source EVs:        {len(merged)}")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_charging_sessions()
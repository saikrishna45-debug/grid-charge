from pathlib import Path

import pandas as pd

from backend.database.database import SessionLocal
from backend.database.models import OptimizationDecision


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DECISIONS_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "optimization_decisions_v3_50ev_residential.csv"
)


def parse_datetime(value):
    """Convert a CSV timestamp into a timezone-naive Python datetime."""

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

    value = str(value).strip().lower()

    return value in {"true", "1", "yes", "y"}


def seed_optimization_decisions():
    """Load V3 optimizer decisions into the SQLite database."""

    if not DECISIONS_FILE.exists():
        raise FileNotFoundError(
            f"Optimization decision file not found: {DECISIONS_FILE}"
        )

    print("Loading V3 optimization decisions...")

    df = pd.read_csv(DECISIONS_FILE)

    if df.empty:
        raise ValueError("Optimization decision file contains no records.")

    print(f"Records found: {len(df)}")

    required_columns = [
        "timestamp",
        "ev_id",
        "priority_score",
        "allocated_charging_power_kw",
        "decision_reason",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        for _, row in df.iterrows():

            timestamp = parse_datetime(row["timestamp"])

            if timestamp is None:
                print("Skipping row with invalid timestamp.")
                skipped += 1
                continue

            ev_id = str(row["ev_id"]).strip()

            if not ev_id:
                print("Skipping row with empty EV ID.")
                skipped += 1
                continue

            priority_score = safe_float(row["priority_score"])

            allocated_power = safe_float(
                row["allocated_charging_power_kw"]
            )

            decision_reason = str(
                row["decision_reason"]
            ).strip()

            # Avoid inserting the same decision twice.
            existing_decision = (
                db.query(OptimizationDecision)
                .filter(
                    OptimizationDecision.timestamp == timestamp,
                    OptimizationDecision.ev_id == ev_id,
                )
                .first()
            )

            if existing_decision:
                skipped += 1
                continue

            decision = OptimizationDecision(
                timestamp=timestamp,
                ev_id=ev_id,
                priority_score=priority_score,
                allocated_power_kw=allocated_power,
                reason=decision_reason,
            )

            db.add(decision)
            inserted += 1

        db.commit()

        print("=" * 55)
        print("OPTIMIZATION DATABASE SEEDING COMPLETED")
        print("=" * 55)
        print(f"Inserted decisions: {inserted}")
        print(f"Skipped decisions:  {skipped}")
        print(f"Source records:     {len(df)}")
        print("=" * 55)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_optimization_decisions()
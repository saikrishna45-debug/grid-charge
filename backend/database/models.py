from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from backend.database.database import Base


class EV(Base):
    """
    Stores the current configuration and state of an electric vehicle.
    """

    __tablename__ = "evs"

    id = Column(Integer, primary_key=True, index=True)

    ev_id = Column(String, unique=True, index=True, nullable=False)

    battery_capacity_kwh = Column(Float, nullable=False)

    current_soc_percent = Column(Float, nullable=False)

    target_soc_percent = Column(Float, nullable=False)

    arrival_time = Column(DateTime, nullable=False)

    departure_time = Column(DateTime, nullable=False)

    max_charging_power_kw = Column(Float, nullable=False)

    charging_status = Column(
        String,
        default="waiting",
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class ChargingSession(Base):
    """
    Stores charging-session information for an EV.
    """

    __tablename__ = "charging_sessions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    ev_id = Column(
        String,
        index=True,
        nullable=False,
    )

    start_time = Column(DateTime, nullable=True)

    end_time = Column(DateTime, nullable=True)

    energy_delivered_kwh = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    charging_power_kw = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    completion_status = Column(
        String,
        default="in_progress",
        nullable=False,
    )


class GridMeasurement(Base):
    """
    Stores building, solar, EV charging and grid measurements.
    """

    __tablename__ = "grid_measurements"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(
        DateTime,
        index=True,
        nullable=False,
    )

    building_demand_kw = Column(Float, nullable=False)

    solar_generation_kw = Column(Float, nullable=False)

    grid_limit_kw = Column(Float, nullable=False)

    ev_charging_power_kw = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    grid_utilization_percent = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    overload_kw = Column(
        Float,
        default=0.0,
        nullable=False,
    )


class OptimizationDecision(Base):
    """
    Stores the optimizer's charging decision for each EV.
    """

    __tablename__ = "optimization_decisions"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(
        DateTime,
        index=True,
        nullable=False,
    )

    ev_id = Column(
        String,
        index=True,
        nullable=False,
    )

    priority_score = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    allocated_power_kw = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    reason = Column(
        String,
        nullable=True,
    )


class SiteConfiguration(Base):
    """
    Stores configuration for a charging site.
    """

    __tablename__ = "site_configurations"

    id = Column(Integer, primary_key=True, index=True)

    site_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    site_type = Column(
        String,
        nullable=False,
    )

    grid_capacity_kw = Column(
        Float,
        nullable=False,
    )

    building_peak_demand_kw = Column(
        Float,
        nullable=False,
    )

    solar_capacity_kw = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    charger_count = Column(
        Integer,
        default=0,
        nullable=False,
    )


class Forecast(Base):
    """
    Stores ML building-demand forecasts.
    """

    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(
        DateTime,
        index=True,
        nullable=False,
    )

    predicted_demand_kw = Column(
        Float,
        nullable=False,
    )

    model = Column(
        String,
        nullable=False,
    )

    forecast_horizon = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
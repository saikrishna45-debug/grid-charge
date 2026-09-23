from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
SAFETY_TOLERANCE_KW = 1e-9

ARTIFACT_PATHS = {
    "timeline": DATA_DIR / "optimized_site_simulation_v5_50ev_residential.csv",
    "decisions": DATA_DIR / "optimization_decisions_v5_50ev_residential.csv",
    "results": DATA_DIR / "ev_optimization_results_v5_50ev_residential.csv",
    "forecast": DATA_DIR / "site_demand_forecast_v5_50ev_residential.csv",
    "scenario": DATA_DIR / "ev_scenario_50_residential.csv",
}

REQUIRED_COLUMNS = {
    "timeline": {
        "timestamp",
        "building_demand_kw",
        "forecast_building_demand_kw",
        "forecast_available_capacity_kw",
        "solar_generation_kw",
        "grid_limit_kw",
        "available_ev_capacity_kw",
        "connected_ev_count",
        "uncontrolled_requested_ev_power_kw",
        "optimized_ev_charging_kw",
        "uncontrolled_site_demand_kw",
        "controlled_site_demand_kw",
        "uncontrolled_overload_kw",
        "controlled_overload_kw",
        "grid_utilization_percent",
        "remaining_grid_capacity_kw",
    },
    "decisions": {
        "timestamp",
        "ev_id",
        "current_soc_percent",
        "required_average_power_kw",
        "slack_hours",
        "forecast_building_demand_kw",
        "forecast_available_capacity_kw",
        "forecast_competing_ev_demand_kw",
        "forecast_congestion_ratio",
        "forecast_feasibility_ratio",
        "forecast_urgency_score",
        "forecast_influenced_decision",
        "priority_score",
        "allocated_charging_power_kw",
        "decision_reason",
    },
    "results": {
        "ev_id",
        "initial_soc_percent",
        "final_soc_percent",
        "target_soc_percent",
        "initial_energy_required_kwh",
        "energy_delivered_kwh",
        "energy_unmet_kwh",
        "completion_percentage",
        "max_charging_power_kw",
        "charging_complete",
        "deadline_missed",
        "physically_infeasible",
        "scheduler_or_grid_constrained",
    },
    "forecast": {
        "timestamp",
        "actual_building_demand_kw",
        "forecast_building_demand_kw",
        "forecast_available_capacity_kw",
        "forecast_scaling_ratio",
    },
    "scenario": {
        "ev_id",
        "arrival_time",
        "departure_time",
        "battery_capacity_kwh",
        "current_soc",
        "target_soc",
        "energy_required_kwh",
        "max_charging_power_kw",
        "charging_status",
        "data_source",
        "timestamp_source",
    },
}


def _read_artifact(name):
    path = ARTIFACT_PATHS[name]

    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"V5 artifact is missing: {path}",
        )

    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read V5 artifact {path.name}: {exc}",
        )

    if frame.empty:
        raise HTTPException(
            status_code=503,
            detail=f"V5 artifact is empty: {path.name}",
        )

    missing = sorted(REQUIRED_COLUMNS[name] - set(frame.columns))
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"V5 artifact {path.name} is missing columns: {missing}",
        )

    return frame


@lru_cache(maxsize=1)
def load_v5_artifacts():
    """Load and validate immutable, read-only V5 artifact data."""

    artifacts = {
        name: _read_artifact(name)
        for name in ARTIFACT_PATHS
    }

    for name in ("timeline", "decisions", "forecast"):
        artifacts[name]["timestamp"] = pd.to_datetime(
            artifacts[name]["timestamp"],
            errors="coerce",
            utc=True,
        )
        if artifacts[name]["timestamp"].isna().any():
            raise HTTPException(
                status_code=500,
                detail=f"V5 {name} artifact contains invalid timestamps.",
            )

    for name in ("timeline", "decisions", "results", "forecast"):
        numeric_columns = artifacts[name].select_dtypes(include=[np.number]).columns
        numeric_values = artifacts[name][numeric_columns].to_numpy(dtype=float)
        if not np.isfinite(numeric_values).all():
            raise HTTPException(
                status_code=500,
                detail=f"V5 {name} artifact contains NaN or infinite numeric values.",
            )

    return artifacts


def clear_v5_cache():
    load_v5_artifacts.cache_clear()


def _bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _json_value(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _records(frame):
    return [
        {
            key: _json_value(value)
            for key, value in row.items()
        }
        for row in frame.to_dict(orient="records")
    ]


def _timestamp_key(frame):
    return pd.to_datetime(frame["timestamp"], utc=True)


def get_grid_frame():
    artifacts = load_v5_artifacts()
    timeline = artifacts["timeline"].copy()
    timeline["timestamp"] = _timestamp_key(timeline)
    timeline["predicted_building_demand_kw"] = timeline["forecast_building_demand_kw"]
    timeline["grid_safe"] = (
        timeline["controlled_site_demand_kw"]
        <= timeline["grid_limit_kw"] + SAFETY_TOLERANCE_KW
    )
    return timeline


def get_forecast_frame():
    artifacts = load_v5_artifacts()
    forecast = artifacts["forecast"].copy()
    forecast["timestamp"] = _timestamp_key(forecast)
    forecast["current_building_demand_kw"] = forecast["actual_building_demand_kw"]
    forecast["predicted_building_demand_kw"] = forecast["forecast_building_demand_kw"]
    forecast["forecast_horizon_minutes"] = 15
    return forecast


def get_result_frame():
    return load_v5_artifacts()["results"].copy()


def get_decision_frame():
    artifacts = load_v5_artifacts()
    decisions = artifacts["decisions"].copy()
    decisions["timestamp"] = _timestamp_key(decisions)
    scenario = artifacts["scenario"].copy()
    scenario["ev_id"] = scenario["ev_id"].astype(str)
    scenario["arrival_time"] = pd.to_datetime(scenario["arrival_time"], utc=True)
    scenario["departure_time"] = pd.to_datetime(scenario["departure_time"], utc=True)
    decisions = decisions.merge(
        scenario[
            [
                "ev_id",
                "departure_time",
                "energy_required_kwh",
                "charging_status",
            ]
        ],
        on="ev_id",
        how="left",
        validate="many_to_one",
    )
    grid = get_grid_frame()
    decisions = decisions.merge(
        grid[
            [
                "timestamp",
                "solar_generation_kw",
            ]
        ],
        on="timestamp",
        how="left",
        validate="many_to_one",
    )
    decisions["current_soc"] = decisions["current_soc_percent"]
    decisions["allocated_power_kw"] = decisions["allocated_charging_power_kw"]
    decisions["forecasted_building_demand_kw"] = decisions["forecast_building_demand_kw"]
    decisions["forecasted_solar_generation_kw"] = decisions["solar_generation_kw"]
    decisions["forecasted_available_ev_capacity_kw"] = decisions["forecast_available_capacity_kw"]
    decisions["forecast_congestion"] = decisions["forecast_congestion_ratio"]
    decisions["available_hours"] = (
        decisions["departure_time"] - decisions["timestamp"]
    ).dt.total_seconds() / 3600.0
    decisions["charging_status"] = decisions["charging_status"].fillna("unknown")
    return decisions


def get_ev_frame():
    artifacts = load_v5_artifacts()
    scenario = artifacts["scenario"][
        [
            "ev_id",
            "arrival_time",
            "departure_time",
            "battery_capacity_kwh",
            "current_soc",
            "target_soc",
            "energy_required_kwh",
            "max_charging_power_kw",
            "data_source",
            "timestamp_source",
        ]
    ].copy()
    results = artifacts["results"][
        [
            "ev_id",
            "completion_percentage",
            "energy_delivered_kwh",
            "energy_unmet_kwh",
            "charging_complete",
            "deadline_missed",
            "physically_infeasible",
        ]
    ].copy()
    decisions = get_decision_frame()

    latest = (
        decisions.sort_values("timestamp")
        .groupby("ev_id", as_index=False)
        .tail(1)
        [["ev_id", "current_soc", "allocated_power_kw"]]
        .rename(columns={"current_soc": "optimized_current_soc"})
    )
    evs = scenario.merge(results, on="ev_id", how="inner", validate="one_to_one")
    evs = evs.merge(latest, on="ev_id", how="left", validate="one_to_one")
    evs["optimized_charging_power_kw"] = evs["allocated_power_kw"].fillna(0.0)
    evs["current_soc"] = evs["optimized_current_soc"].fillna(evs["current_soc"])
    evs["charging_status"] = np.select(
        [
            evs["charging_complete"].map(_bool),
            evs["deadline_missed"].map(_bool),
        ],
        ["completed", "deadline_missed"],
        default="incomplete",
    )
    return evs[
        [
            "ev_id",
            "arrival_time",
            "departure_time",
            "battery_capacity_kwh",
            "current_soc",
            "target_soc",
            "energy_required_kwh",
            "max_charging_power_kw",
            "optimized_charging_power_kw",
            "charging_status",
            "completion_percentage",
            "energy_delivered_kwh",
            "energy_unmet_kwh",
            "deadline_missed",
            "physically_infeasible",
            "data_source",
            "timestamp_source",
        ]
    ]


def get_optimization_summary():
    results = get_result_frame()
    grid = get_grid_frame()
    overload = np.maximum(
        grid["controlled_site_demand_kw"] - grid["grid_limit_kw"],
        0.0,
    )
    maximum_overload = float(overload.max())
    if maximum_overload <= SAFETY_TOLERANCE_KW:
        maximum_overload = 0.0

    return {
        "optimization_version": "V5",
        "total_evs": int(len(results)),
        "completed_evs": int(results["charging_complete"].map(_bool).sum()),
        "incomplete_evs": int((~results["charging_complete"].map(_bool)).sum()),
        "deadline_misses": int(results["deadline_missed"].map(_bool).sum()),
        "physically_infeasible": int(results["physically_infeasible"].map(_bool).sum()),
        "scheduler_or_grid_constrained": int(results["scheduler_or_grid_constrained"].map(_bool).sum()),
        "required_energy_kwh": float(results["initial_energy_required_kwh"].sum()),
        "delivered_energy_kwh": float(results["energy_delivered_kwh"].sum()),
        "unmet_energy_kwh": float(results["energy_unmet_kwh"].sum()),
        "average_completion_percent": float(results["completion_percentage"].mean()),
        "peak_ev_charging_kw": float(grid["optimized_ev_charging_kw"].max()),
        "peak_controlled_site_demand_kw": float(grid["controlled_site_demand_kw"].max()),
        "max_controlled_overload_kw": maximum_overload,
        "grid_safe_intervals": int((overload <= SAFETY_TOLERANCE_KW).sum()),
        "total_intervals": int(len(grid)),
        "peak_grid_utilization_percent": float(grid["grid_utilization_percent"].max()),
    }


def get_provenance():
    return {
        "ev_scenario": "synthetic residential scenario with ACN-derived session context",
        "solar_profile": "synthetic solar profile",
        "building_demand": "UCI-derived historical demand behavior",
        "forecast": "historical-model-based site demand forecast used for look-ahead simulation",
        "optimization": "calculated by validated V5 optimizer",
    }


def records_for(frame):
    return _records(frame)

from fastapi import APIRouter, HTTPException

from backend.services.v5_data_service import get_grid_frame, records_for


router = APIRouter(prefix="/api/grid", tags=["Grid"])
GRID_FIELDS = [
    "timestamp",
    "building_demand_kw",
    "predicted_building_demand_kw",
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
    "grid_safe",
]


def _grid_records():
    frame = get_grid_frame()
    return frame[GRID_FIELDS]


@router.get("")
def get_grid():
    frame = _grid_records()
    return {
        "count": len(frame),
        "optimization_version": "V5",
        "source": "V5 optimized site simulation artifact",
        "data": records_for(frame),
    }


@router.get("/latest")
def get_latest_grid_status():
    frame = _grid_records()
    if frame.empty:
        raise HTTPException(status_code=404, detail="V5 grid simulation contains no records.")
    return {
        "optimization_version": "V5",
        "data": records_for(frame.tail(1))[0],
    }


@router.get("/summary")
def get_grid_summary():
    frame = _grid_records()
    if frame.empty:
        raise HTTPException(status_code=404, detail="V5 grid simulation contains no records.")
    return {
        "optimization_version": "V5",
        "simulation_intervals": len(frame),
        "peak_building_demand_kw": float(frame["building_demand_kw"].max()),
        "peak_solar_generation_kw": float(frame["solar_generation_kw"].max()),
        "peak_ev_charging_kw": float(frame["optimized_ev_charging_kw"].max()),
        "peak_grid_utilization_percent": float(frame["grid_utilization_percent"].max()),
        "maximum_controlled_overload_kw": float(frame["controlled_overload_kw"].clip(lower=0).max()),
        "maximum_uncontrolled_overload_kw": float(frame["uncontrolled_overload_kw"].clip(lower=0).max()),
        "controlled_overload_intervals": int((~frame["grid_safe"]).sum()),
        "uncontrolled_overload_intervals": int((frame["uncontrolled_overload_kw"] > 1e-9).sum()),
        "grid_safety_passed": bool(frame["grid_safe"].all()),
    }

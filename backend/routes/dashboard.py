from fastapi import APIRouter

from backend.services.v5_data_service import (
    get_decision_frame,
    get_ev_frame,
    get_forecast_frame,
    get_grid_frame,
    get_optimization_summary,
    get_provenance,
    records_for,
)


router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("")
def get_dashboard_status():
    grid = get_grid_frame()
    evs = get_ev_frame()
    forecast = get_forecast_frame()
    decisions = get_decision_frame()
    summary = get_optimization_summary()
    latest_grid = grid.tail(1)
    latest_forecast = forecast.sort_values("timestamp").tail(1)
    latest_decisions = decisions[decisions["timestamp"] == decisions["timestamp"].max()]

    grid_record = records_for(latest_grid)[0]
    ev_summary = {
        "total_evs": len(evs),
        "connected_evs": int(grid_record["connected_ev_count"]),
        "completed_evs": summary["completed_evs"],
        "incomplete_evs": summary["incomplete_evs"],
        "deadline_misses": summary["deadline_misses"],
        "physically_infeasible": summary["physically_infeasible"],
        "average_soc_percent": float(evs["current_soc"].mean()),
        "average_completion_percent": summary["average_completion_percent"],
        "optimized_charging_kw": grid_record["optimized_ev_charging_kw"],
    }
    energy = {
        "required_energy_kwh": summary["required_energy_kwh"],
        "delivered_energy_kwh": summary["delivered_energy_kwh"],
        "unmet_energy_kwh": summary["unmet_energy_kwh"],
    }
    forecast_record = records_for(latest_forecast)[0]
    return {
        "optimization_version": "V5",
        "system_status": "SAFE" if bool(grid_record["grid_safe"]) else "OVERLOAD",
        "grid": grid_record,
        "evs": ev_summary,
        "energy": energy,
        "forecast": forecast_record,
        "optimization": summary,
        "latest_decision_count": len(latest_decisions),
        "provenance": get_provenance(),
    }

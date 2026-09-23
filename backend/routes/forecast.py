from fastapi import APIRouter, HTTPException

from backend.services.v5_data_service import get_forecast_frame, records_for


router = APIRouter(prefix="/api/forecast", tags=["Forecast"])
FORECAST_FIELDS = [
    "timestamp",
    "current_building_demand_kw",
    "predicted_building_demand_kw",
    "forecast_scaling_ratio",
    "forecast_horizon_minutes",
]


@router.get("")
def get_forecast_info():
    frame = get_forecast_frame()
    return {
        "count": len(frame),
        "optimization_version": "V5",
        "source": "V5 site demand forecast artifact",
        "forecast_role": "historical-model-based site demand forecast used for look-ahead simulation",
        "data": records_for(frame[FORECAST_FIELDS]),
    }


@router.get("/sample")
def get_sample_forecast():
    frame = get_forecast_frame()
    if frame.empty:
        raise HTTPException(status_code=404, detail="V5 forecast contains no records.")
    return {
        "optimization_version": "V5",
        "source": "V5 site demand forecast artifact",
        "forecast_role": "historical-model-based site demand forecast used for look-ahead simulation",
        "data": records_for(frame[FORECAST_FIELDS].head(1))[0],
    }

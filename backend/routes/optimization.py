from fastapi import APIRouter, HTTPException

from backend.services.v5_data_service import (
    get_decision_frame,
    get_optimization_summary,
    get_result_frame,
    records_for,
)


router = APIRouter(prefix="/api/optimization", tags=["Optimization"])


@router.get("")
def get_optimization_summary_route():
    return get_optimization_summary()


@router.get("/decisions")
def get_optimization_decisions():
    decisions = get_decision_frame()
    return {
        "count": len(decisions),
        "optimization_version": "V5",
        "source": "V5 optimization decisions artifact",
        "data": records_for(decisions),
    }


@router.get("/decisions/latest")
def get_latest_decisions():
    decisions = get_decision_frame()
    if decisions.empty:
        raise HTTPException(status_code=404, detail="V5 decision history is empty.")
    latest_timestamp = decisions["timestamp"].max()
    latest = decisions[decisions["timestamp"] == latest_timestamp]
    return {
        "timestamp": latest_timestamp.isoformat(),
        "optimization_version": "V5",
        "count": len(latest),
        "data": records_for(latest),
    }


@router.get("/ev/{ev_id}")
def get_ev_optimization(ev_id: str):
    results = get_result_frame()
    matches = results[results["ev_id"].astype(str).str.upper() == ev_id.upper()]
    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"V5 optimization result for EV '{ev_id}' not found.",
        )
    decisions = get_decision_frame()
    history = decisions[decisions["ev_id"].astype(str).str.upper() == ev_id.upper()]
    return {
        "optimization_version": "V5",
        "result": records_for(matches)[0],
        "decision_history": records_for(history),
    }

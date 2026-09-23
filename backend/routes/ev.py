from fastapi import APIRouter, HTTPException

from backend.services.v5_data_service import get_ev_frame, records_for


router = APIRouter(prefix="/api/evs", tags=["EVs"])


@router.get("")
def get_evs():
    evs = get_ev_frame()
    return {
        "count": len(evs),
        "optimization_version": "V5",
        "source": "V5 optimization artifacts and synthetic EV scenario",
        "data": records_for(evs),
    }


@router.get("/{ev_id}")
def get_ev(ev_id: str):
    evs = get_ev_frame()
    matches = evs[evs["ev_id"].astype(str).str.upper() == ev_id.upper()]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"EV '{ev_id}' not found.")
    return {
        "optimization_version": "V5",
        "data": records_for(matches)[0],
    }

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.dashboard import router as dashboard_router
from backend.routes.ev import router as ev_router
from backend.routes.forecast import router as forecast_router
from backend.routes.grid import router as grid_router
from backend.routes.optimization import router as optimization_router


app = FastAPI(
    title="Smart EV Charging & Local Grid Management API",
    description=(
        "Backend API for smart EV charging, grid management, "
        "building demand forecasting, and site energy planning."
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(ev_router)
app.include_router(grid_router)
app.include_router(forecast_router)
app.include_router(optimization_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return {
        "message": "Smart EV Charging API is running",
        "version": "1.0.0",
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "smart-ev-charging-backend",
        "timestamp": datetime.now().isoformat(),
    }
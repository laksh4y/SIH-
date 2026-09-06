"""
main.py — FastAPI application for SteelRoute AI.
Serves the frontend dashboard and exposes REST API endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from backend.data_loader import load_ports, load_routes, VESSEL_SPECS
from backend.vessel_optimizer import optimize, get_feasible_vessels
from backend.forecasting import (
    forecast_freight_rate,
    forecast_fuel_price,
    forecast_commodity_price,
)
from backend.route_engine import calculate_voyage, find_route

# ---------- App Setup ----------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = FastAPI(
    title="SteelRoute AI",
    description="Intelligent Freight Forecasting for Optimized Vessel Chartering — Ministry of Steel, India",
    version="1.0.0",
)

# Serve static frontend files
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ---------- Request Models ----------

class OptimizeRequest(BaseModel):
    origin_id: str
    dest_id: str
    cargo_volume_mt: float = 100000
    target_days_ahead: int = 90


# ---------- Frontend ----------

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve the main dashboard page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ---------- API Endpoints ----------

@app.get("/api/ports")
async def get_ports():
    """List all ports with metadata."""
    df = load_ports()
    ports = df.to_dict(orient="records")

    origins = [p for p in ports if p["port_type"] == "origin"]
    destinations = [p for p in ports if p["port_type"] == "destination"]

    return {
        "origins": origins,
        "destinations": destinations,
        "all_ports": ports,
    }


@app.get("/api/routes")
async def get_routes():
    """List all shipping routes."""
    df = load_routes()
    return {"routes": df.to_dict(orient="records")}


@app.get("/api/vessels")
async def get_vessels():
    """List all vessel types and specs."""
    return {"vessels": VESSEL_SPECS}


@app.get("/api/forecast/{series}")
async def get_forecast(series: str, vessel_type: Optional[str] = None, days: int = 90):
    """
    Get a forecast for a given series.
    series: 'freight', 'fuel', or 'commodity'
    vessel_type: Required for 'freight' series (default: 'Panamax')
    days: Forecast horizon (default: 90)
    """
    days = min(days, 365)  # cap at 1 year

    try:
        if series == "freight":
            vt = vessel_type or "Panamax"
            fcst = forecast_freight_rate(vt, days)
        elif series == "fuel":
            fcst = forecast_fuel_price(days)
        elif series == "commodity":
            fcst = forecast_commodity_price(days)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown series '{series}'. Use 'freight', 'fuel', or 'commodity'.",
            )

        return {
            "series": series,
            "vessel_type": vessel_type,
            "days": days,
            "forecast": {
                "dates": [d.strftime("%Y-%m-%d") for d in fcst["ds"]],
                "predicted": [round(v, 2) for v in fcst["yhat"].tolist()],
                "lower": [round(v, 2) for v in fcst["yhat_lower"].tolist()],
                "upper": [round(v, 2) for v in fcst["yhat_upper"].tolist()],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/voyage")
async def get_voyage(origin_id: str, dest_id: str, vessel_type: str):
    """Calculate voyage details for a route + vessel combination."""
    voyage = calculate_voyage(origin_id, dest_id, vessel_type)
    if voyage is None:
        raise HTTPException(
            status_code=404,
            detail=f"No route found from {origin_id} to {dest_id}.",
        )
    return {"voyage": voyage}


@app.get("/api/feasibility")
async def check_feasibility(origin_id: str, dest_id: str, cargo_mt: float = 100000):
    """Check which vessel types are feasible for a route."""
    feasible, rejected = get_feasible_vessels(origin_id, dest_id, cargo_mt)
    return {
        "feasible_vessels": feasible,
        "rejected_vessels": rejected,
        "origin_id": origin_id,
        "dest_id": dest_id,
        "cargo_volume_mt": cargo_mt,
    }


@app.post("/api/optimize")
async def run_optimization(req: OptimizeRequest):
    """
    Full optimization: find the best vessel + timing for a shipment.
    Returns ranked recommendations with cost breakdowns.
    """
    try:
        result = optimize(
            origin_id=req.origin_id,
            dest_id=req.dest_id,
            cargo_volume_mt=req.cargo_volume_mt,
            target_days_ahead=req.target_days_ahead,
        )

        if "error" in result and not result.get("recommendations"):
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Health Check ----------

@app.get("/api/health")
async def health_check():
    return {"status": "operational", "service": "SteelRoute AI", "version": "1.0.0"}

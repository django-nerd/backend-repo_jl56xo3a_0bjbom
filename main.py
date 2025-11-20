import os
from datetime import date
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import create_document, get_documents, db

app = FastAPI(title="RegimeEye API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegimeNow(BaseModel):
    timestamp: str
    regime: str
    probabilities: Dict[str, float]
    conviction: int
    weights: Dict[str, float]
    benchmark_weights: Dict[str, float]


class BacktestPoint(BaseModel):
    date: str
    taa: float
    saa: float
    sixty_forty: float


class BacktestResponse(BaseModel):
    equity_curve: List[BacktestPoint]
    weights_over_time: List[Dict[str, float]]


class ScenarioRequest(BaseModel):
    name: str
    assumptions: Dict[str, float]


@app.get("/")
def read_root():
    return {"message": "RegimeEye API ready"}


@app.get("/api/regime-now", response_model=RegimeNow)
def regime_now():
    # Mocked signal for MVP visual. Replace with model outputs later.
    data = RegimeNow(
        timestamp=date.today().isoformat(),
        regime="Slowdown",
        probabilities={
            "Expansion": 0.22,
            "Slowdown": 0.53,
            "Contraction": 0.18,
            "Recovery": 0.07,
        },
        conviction=84,
        weights={"SPY": 0.35, "IEF": 0.35, "GLD": 0.15, "DBC": 0.10, "SHY": 0.05},
        benchmark_weights={"SPY": 0.60, "IEF": 0.40},
    )
    return data


@app.get("/api/backtest", response_model=BacktestResponse)
def backtest(start: Optional[str] = "2005-01-01", end: Optional[str] = None, benchmark: str = "60_40"):
    # Minimal synthetic curve for MVP animation
    import math

    if end is None:
        end = date.today().isoformat()

    # Generate 240 monthly points (~20 years)
    n = 240
    pts: List[BacktestPoint] = []
    weights_ot: List[Dict[str, float]] = []

    for i in range(n):
        t = i / n
        taa = 100 * (1 + 0.08) ** (t * 20) * (1 + 0.02 * math.sin(8 * t))
        saa = 100 * (1 + 0.05) ** (t * 20)
        sixty = 100 * (1 + 0.06) ** (t * 20)
        pts.append(BacktestPoint(date=f"{2005 + i//12}-{(i%12)+1:02d}-01", taa=taa, saa=saa, sixty_forty=sixty))
        # Simple animated weights
        w_spy = 0.55 - 0.25 * math.sin(2 * math.pi * t)
        w_ief = 0.35 + 0.20 * math.sin(2 * math.pi * t)
        w_gld = 0.10 + 0.10 * math.sin(4 * math.pi * t)
        w_dbc = max(0.0, 0.15 * math.cos(2 * math.pi * t))
        w_shy = max(0.0, 1 - (w_spy + w_ief + w_gld + w_dbc))
        weights_ot.append({"SPY": w_spy, "IEF": w_ief, "GLD": w_gld, "DBC": w_dbc, "SHY": w_shy})

    return BacktestResponse(equity_curve=pts, weights_over_time=weights_ot)


@app.post("/api/stress-test")
def stress_test(req: ScenarioRequest):
    # Store scenario for auditability, return adjusted conviction/weights
    try:
        scenario_id = create_document("scenario", {"name": req.name, "assumptions": req.assumptions})
    except Exception:
        scenario_id = None

    # Simple rules to illustrate reactivity
    shift = sum(req.assumptions.values()) if req.assumptions else 0.0
    conviction = max(0, min(100, 70 + int(5 * (1 if shift < 0 else -1))))
    weights = {"SPY": 0.30, "IEF": 0.45, "GLD": 0.15, "DBC": 0.07, "SHY": 0.03}

    return {"scenario_id": scenario_id, "conviction": conviction, "weights": weights}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

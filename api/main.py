"""
API REST del Predictor EPL (FastAPI).

Envuelve `EPLPredictor` (prediction_service.py) y expone un contrato JSON limpio
para el frontend. Con EPL_MOCK=1 funciona sin TensorFlow ni datasets (solo para
desarrollar la interfaz).

Ejecutar desde la raíz del repo:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MOCK = os.getenv("EPL_MOCK", "0") == "1"

# Equipos de la temporada 2024/25 (los "activos" que se muestran primero en la UI).
CURRENT_SEASON = "2024/25"


# ---------------------------------------------------------------- esquemas
class PredictRequest(BaseModel):
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)
    match_date: Optional[date] = None
    odds: Optional[list[float]] = Field(
        default=None, description="Cuotas decimales [local, empate, visitante]"
    )

    @model_validator(mode="after")
    def _check_odds(self):
        if self.odds is not None:
            if len(self.odds) != 3 or any(o <= 1.0 for o in self.odds):
                raise ValueError("Las cuotas deben ser 3 valores decimales mayores a 1.00")
        return self


class Probabilities(BaseModel):
    home: float
    draw: float
    away: float


class TeamState(BaseModel):
    elo: float
    form5: float
    rolling_pts5: float
    rolling_gf5: float
    rolling_ga5: float
    rest_days: float
    season_pts: float
    season_gd: float


class PredictResponse(BaseModel):
    home_team: str
    away_team: str
    match_date: Optional[str]
    probabilities: Probabilities  # en porcentaje, suman 100
    predicted: str  # "home" | "draw" | "away"
    odds_used: bool
    home_state: TeamState
    away_state: TeamState
    h2h: Probabilities  # % histórico (local / empate / visitante)
    home_last_match: Optional[str] = None  # último partido registrado antes de la fecha
    away_last_match: Optional[str] = None
    data_end: Optional[str] = None  # fecha del último partido del dataset
    mock: bool = False


# ---------------------------------------------------------------- backends
class RealBackend:
    def __init__(self):
        from prediction_service import EPLPredictor  # import perezoso (TensorFlow)

        self.p = EPLPredictor()
        epl = self.p.epl
        self.current = sorted(
            set(epl.loc[epl["Season"] == CURRENT_SEASON, "HomeTeam"].unique())
        )
        self.all_teams = sorted(self.p.known_teams)

    def teams(self):
        return self.current, self.all_teams

    def _last_match(self, team: str, before: Optional[str]) -> Optional[str]:
        h = self.p.df_history
        mask = (h["HomeTeam"] == team) | (h["AwayTeam"] == team)
        if before:
            mask &= h["MatchDate"] < before
        dates = h.loc[mask, "MatchDate"]
        return dates.max().date().isoformat() if len(dates) else None

    def predict(self, req: PredictRequest) -> PredictResponse:
        p = self.p
        home = p.normalize_team(req.home_team)
        away = p.normalize_team(req.away_team)
        when = req.match_date.isoformat() if req.match_date else None
        res = p.predict_match(home, away, when, req.odds)
        if res["status"] != "success":
            raise HTTPException(status_code=422, detail=res["message"])

        h_stats = p.get_latest_team_stats(home, when)
        a_stats = p.get_latest_team_stats(away, when)
        h2h = p.get_h2h_stats(home, away, when)
        np_ = res["numeric_probabilities"]
        total = np_["P_Home"] + np_["P_Draw"] + np_["P_Away"]
        pct = {k: round(v / total * 100, 1) for k, v in
               {"home": np_["P_Home"], "draw": np_["P_Draw"], "away": np_["P_Away"]}.items()}
        pct["home"] = round(pct["home"] + (100.0 - sum(pct.values())), 1)
        predicted = max(pct, key=pct.get)
        return PredictResponse(
            home_team=home,
            away_team=away,
            match_date=when,
            home_last_match=self._last_match(home, when),
            away_last_match=self._last_match(away, when),
            data_end=self.p.df_history["MatchDate"].max().date().isoformat(),
            probabilities=Probabilities(**pct),
            predicted=predicted,
            odds_used=req.odds is not None,
            home_state=_state(h_stats),
            away_state=_state(a_stats),
            h2h=Probabilities(home=round(h2h[0] * 100, 1), draw=round(h2h[1] * 100, 1),
                              away=round(h2h[2] * 100, 1)),
        )


def _state(s: dict) -> TeamState:
    return TeamState(**{k: round(float(s[k]), 2) for k in TeamState.model_fields})


class MockBackend:
    """Datos simulados: solo para diseñar la UI sin cargar TensorFlow."""

    ELO = {
        "Man City": 1990, "Arsenal": 1960, "Liverpool": 1950, "Chelsea": 1850,
        "Newcastle": 1830, "Aston Villa": 1810, "Tottenham": 1800, "Man United": 1790,
        "Brighton": 1760, "West Ham": 1740, "Crystal Palace": 1730, "Fulham": 1720,
        "Brentford": 1715, "Bournemouth": 1710, "Wolves": 1690, "Everton": 1680,
        "Nott'm Forest": 1670, "Leicester": 1640, "Southampton": 1600, "Ipswich": 1580,
    }

    def teams(self):
        t = sorted(self.ELO)
        return t, t

    def predict(self, req: PredictRequest) -> PredictResponse:
        h, a = req.home_team, req.away_team
        if h not in self.ELO or a not in self.ELO:
            raise HTTPException(422, f"Equipo no reconocido: '{h if h not in self.ELO else a}'.")
        if h == a:
            raise HTTPException(422, "Un equipo no puede jugar contra sí mismo.")
        d = self.ELO[h] - self.ELO[a] + 100
        ph = 1 / (1 + 10 ** (-d / 400))
        draw = 0.27 - abs(ph - 0.5) * 0.2
        home, away = ph * (1 - draw), (1 - ph) * (1 - draw)
        pct = {"home": round(home * 100, 1), "draw": round(draw * 100, 1)}
        pct["away"] = round(100 - pct["home"] - pct["draw"], 1)

        def st(t):
            e = self.ELO[t]
            return TeamState(elo=e, form5=round((e - 1500) / 40, 1), rolling_pts5=round(e / 1000, 2),
                             rolling_gf5=round(e / 1100, 2), rolling_ga5=round(2300 / e, 2),
                             rest_days=7, season_pts=round((e - 1500) / 6), season_gd=round((e - 1750) / 10))

        return PredictResponse(
            home_team=h, away_team=a,
            match_date=req.match_date.isoformat() if req.match_date else None,
            probabilities=Probabilities(**pct), predicted=max(pct, key=pct.get),
            odds_used=req.odds is not None, home_state=st(h), away_state=st(a),
            h2h=Probabilities(home=40, draw=25, away=35), mock=True,
            home_last_match="2025-05-04", away_last_match="2025-05-04", data_end="2025-05-25",
        )


# ---------------------------------------------------------------- app
state: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    state["backend"] = MockBackend() if MOCK else RealBackend()
    yield


app = FastAPI(title="Predictor EPL API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    """Mensajes de validación en español y con `detail` siempre como texto."""
    fields = {str(e["loc"][-1]) for e in exc.errors()}
    if "odds" in fields or any("cuotas" in str(e.get("msg", "")) for e in exc.errors()):
        msg = "Las cuotas deben ser tres valores decimales (local, empate, visitante), todos mayores a 1,00."
    elif "match_date" in fields:
        msg = "La fecha no es válida. Usa el formato AAAA-MM-DD."
    else:
        msg = "Los datos enviados no son válidos. Revisa los equipos, la fecha y las cuotas."
    return JSONResponse(status_code=422, content={"detail": msg})


@app.get("/api/health")
def health():
    return {"status": "ok", "mock": MOCK}


@app.get("/api/teams")
def teams():
    current, all_teams = state["backend"].teams()
    return {"season": CURRENT_SEASON, "current": current, "all": all_teams}


@app.post("/api/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    return state["backend"].predict(req)


@app.get("/api/metrics")
def metrics():
    """Resumen de entrenamiento y benchmark (models/training_summary.json)."""
    path = ROOT / "models" / "training_summary.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)

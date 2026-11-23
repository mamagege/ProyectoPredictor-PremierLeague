"""API REST FastAPI para el Sistema Predictor de Resultados EPL (Hito 3)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from prediction_service import EPLPredictor, get_predictor

logger = logging.getLogger(__name__)


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class OddsInput(BaseModel):
    home: float = Field(..., gt=1.0, le=1000.0, description="Cuota decimal para victoria local en (1.0, 1000].")
    draw: float = Field(..., gt=1.0, le=1000.0, description="Cuota decimal para empate en (1.0, 1000].")
    away: float = Field(..., gt=1.0, le=1000.0, description="Cuota decimal para victoria visitante en (1.0, 1000].")


class PredictionRequest(BaseModel):
    home_team: str = Field(..., min_length=1, description="Nombre o alias del equipo local.")
    away_team: str = Field(..., min_length=1, description="Nombre o alias del equipo visitante.")
    match_date: Optional[str] = Field(
        default=None,
        description="Fecha programada del encuentro en formato ISO (YYYY-MM-DD o ISO-8601).",
    )
    odds: Optional[OddsInput] = Field(
        default=None,
        description="Cuotas decimales pre-partido (opcional; si se omite usa modelo Elo->Mercado).",
    )
    decision_mode: Literal["argmax", "bayesian"] = Field(
        default="argmax",
        description="Regla de decisión discreta: 'argmax' o 'bayesian'.",
    )

    @field_validator("home_team", "away_team")
    @classmethod
    def _strip_team(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("El nombre del equipo no puede estar vacío.")
        return cleaned


class BatchPredictionRequest(BaseModel):
    matches: list[PredictionRequest] = Field(..., min_length=1, max_length=50)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.predictor = get_predictor()
    yield


app = FastAPI(
    title="EPL Match Outcome Predictor API (PTIA - Hito 3)",
    description=(
        "Backend de inferencia probabilística pre-partido para la English Premier League "
        "basado en Red Neuronal Profunda calibrada y características causales sin fuga."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_app_predictor() -> EPLPredictor:
    predictor = getattr(app.state, "predictor", None)
    if predictor is None:
        predictor = get_predictor()
        app.state.predictor = predictor
    return predictor


def _raise_for_service_error(res: dict[str, Any]) -> None:
    code = res.get("error_code", "bad_request")
    msg = res.get("message", "Error en la solicitud de predicción.")
    detail: dict[str, Any] = {"error_code": code, "message": msg}
    if "match_index" in res:
        detail["match_index"] = res["match_index"]
    if code in ("unknown_team", "insufficient_history"):
        raise HTTPException(status_code=404, detail=detail)
    raise HTTPException(status_code=400, detail=detail)


@app.get("/health")
def health_check() -> dict[str, Any]:
    predictor = _get_app_predictor()
    return {
        "status": "ok",
        "model_version": predictor.model_version,
        "model_architecture": predictor.selected_architecture,
        "n_features": len(predictor.feature_names),
        "n_known_teams": len(predictor.known_teams),
        "history_matches": int(len(predictor.df_history)),
        "last_history_date": str(predictor.last_history_date.date()),
        "temperature": predictor.temperature,
        "bayesian_weights": predictor.bayesian_weights,
    }


@app.get("/teams")
def list_teams() -> dict[str, Any]:
    predictor = _get_app_predictor()
    teams = sorted(predictor.known_teams)
    return {"count": len(teams), "teams": teams}


@app.get("/teams/{team_name}/stats")
def get_team_stats(
    team_name: str,
    match_date: Optional[str] = Query(default=None, description="Fecha de corte YYYY-MM-DD o ISO-8601."),
    venue: Literal["home", "away"] = Query(default="home", description="Contexto de sede para forma específica."),
) -> dict[str, Any]:
    predictor = _get_app_predictor()
    try:
        stats = predictor.get_team_snapshot(
            team_name=team_name,
            target_date=match_date,
            is_home=(venue == "home"),
        )
        return {"status": "success", "stats": stats}
    except ValueError as exc:
        msg = str(exc)
        status_code = 404 if ("no reconocido" in msg or "Historial insuficiente" in msg) else 400
        raise HTTPException(status_code=status_code, detail={"message": msg}) from exc


@app.post("/predict")
def predict_single(payload: PredictionRequest) -> dict[str, Any]:
    predictor = _get_app_predictor()
    odds_tuple = (
        [payload.odds.home, payload.odds.draw, payload.odds.away]
        if payload.odds is not None
        else None
    )
    res = predictor.predict_match(
        home_team=payload.home_team,
        away_team=payload.away_team,
        match_date=payload.match_date,
        odds=odds_tuple,
        decision_mode=payload.decision_mode,
    )
    if res.get("status") != "success":
        _raise_for_service_error(res)
    return res


@app.post("/predict/batch")
def predict_batch(payload: BatchPredictionRequest) -> dict[str, Any]:
    predictor = _get_app_predictor()
    batch_items = [
        {
            "home_team": item.home_team,
            "away_team": item.away_team,
            "match_date": item.match_date,
            "odds": [item.odds.home, item.odds.draw, item.odds.away] if item.odds is not None else None,
            "decision_mode": item.decision_mode,
        }
        for item in payload.matches
    ]
    res = predictor.predict_matches_batch(batch_items)
    if res.get("status") != "success":
        _raise_for_service_error(res)
    return res


@app.get("/model/metrics")
def get_model_metrics(
    include_bins: bool = Query(
        default=False,
        description="Incluir los bins detallados de curvas de confiabilidad por clase.",
    ),
) -> dict[str, Any]:
    predictor = _get_app_predictor()
    summary = predictor.training_summary
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "No se encontró models/training_summary.json."},
        )
    if include_bins:
        return summary
    compact = dict(summary)
    for split_key in ("val_results", "test_results", "prospective_2025_26_results"):
        if split_key in compact and isinstance(compact[split_key], list):
            compact[split_key] = [
                {k: v for k, v in entry.items() if k != "calibration_bins"}
                for entry in compact[split_key]
            ]
    return compact

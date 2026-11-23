"""
Fechas disponibles, partidos jugados y calendario opcional de próximos partidos.

Rutas (se montan con `make_router` desde api/main.py):
    GET /api/dates                  fechas con partidos en el historial (más recientes primero)
    GET /api/matches?date=AAAA-MM-DD  partidos jugados ese día; sin fecha, los últimos 10 jugados
    GET /api/fixtures               próximos partidos, si existe el archivo de calendario

Los datos del proyecto solo contienen partidos ya jugados. Los próximos partidos salen de un
CSV opcional (`datasets/fixtures.csv`, o la ruta de la variable FIXTURES_CSV) con columnas
`date,home_team,away_team[,round]`; solo se muestran las filas posteriores al último partido
del historial. Si el archivo no existe, la API lo dice y no inventa nada.
"""
from __future__ import annotations

import csv
import os
from datetime import date as Date
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Query

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_CSV = Path(os.getenv("FIXTURES_CSV", str(ROOT / "datasets" / "fixtures.csv")))
MAX_FIXTURES = 60


# ---------------------------------------------------------------- funciones puras
def available_dates(history, limit: int = 120) -> list[dict[str, Any]]:
    """Fechas con partidos (más recientes primero) y cuántos partidos hubo cada día."""
    counts = history.groupby("MatchDate").size().sort_index(ascending=False).head(limit)
    return [{"date": d.date().isoformat(), "matches": int(n)} for d, n in counts.items()]


def matches_on(history, day: Optional[str], latest: int = 10) -> tuple[Optional[str], list[dict[str, Any]]]:
    """Partidos jugados un día; sin día, los últimos `latest` partidos del historial (más recientes primero)."""
    import pandas as pd

    if day:
        rows = history[history["MatchDate"] == pd.Timestamp(day)].sort_values(["HomeTeam", "AwayTeam"])
    else:
        rows = history.sort_values(["MatchDate", "HomeTeam"], ascending=[False, True]).head(latest)
    out = [
        {
            "date": r.MatchDate.date().isoformat(),
            "home_team": str(r.HomeTeam),
            "away_team": str(r.AwayTeam),
            "home_goals": int(r.FullTimeHomeGoals),
            "away_goals": int(r.FullTimeAwayGoals),
            "result": str(r.FullTimeResult),
            "season": str(r.Season) if "Season" in rows.columns else None,
        }
        for r in rows.itertuples(index=False)
    ]
    return day, out


def load_fixtures(
    path: Path,
    after: Date,
    normalize: Callable[[str], str] = lambda x: x,
    known: Optional[set[str]] = None,
) -> Optional[dict[str, Any]]:
    """Lee el calendario opcional. Devuelve None si el archivo no existe.

    Solo conserva filas posteriores a `after` (lo ya jugado vive en el historial) y cuenta las
    filas inválidas en lugar de fallar.
    """
    if not path.exists():
        return None
    fixtures: list[dict[str, Any]] = []
    skipped = 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        for rec in csv.DictReader(f):
            try:
                day = Date.fromisoformat((rec["date"] or "").strip())
                home = normalize((rec["home_team"] or "").strip())
                away = normalize((rec["away_team"] or "").strip())
            except (KeyError, ValueError, AttributeError):
                skipped += 1
                continue
            if not home or not away or home == away:
                skipped += 1
                continue
            if day <= after:
                continue
            fixtures.append(
                {
                    "date": day.isoformat(),
                    "home_team": home,
                    "away_team": away,
                    "round": (rec.get("round") or "").strip() or None,
                    "known": known is None or (home in known and away in known),
                }
            )
    fixtures.sort(key=lambda x: (x["date"], x["home_team"]))
    return {"fixtures": fixtures[:MAX_FIXTURES], "skipped": skipped}


# ---------------------------------------------------------------- rutas
def make_router(get_backend: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api")

    def history_of(backend):
        p = getattr(backend, "p", None)
        return getattr(p, "df_history", None)

    @router.get("/dates")
    def dates(limit: int = Query(120, ge=1, le=500)):
        backend = get_backend()
        history = history_of(backend)
        if history is None:  # modo simulado: sin datasets
            return {"dates": [{"date": "2025-05-25", "matches": 10}, {"date": "2025-05-18", "matches": 10}]}
        return {"dates": available_dates(history, limit)}

    @router.get("/matches")
    def matches(date: Optional[Date] = None):
        backend = get_backend()
        history = history_of(backend)
        if history is None:
            return {"date": "2025-05-25", "matches": [], "mock": True}
        day, rows = matches_on(history, date.isoformat() if date else None)
        return {"date": day, "matches": rows}

    @router.get("/fixtures")
    def fixtures():
        backend = get_backend()
        p = getattr(backend, "p", None)
        after = Date.fromisoformat(backend.data_end())
        normalize = getattr(p, "normalize_team", None) or (lambda x: x)
        known = getattr(p, "known_teams", None)
        loaded = load_fixtures(FIXTURES_CSV, after, normalize, known)
        if loaded is None:
            return {"available": False, "fixtures": [], "skipped": 0, "data_end": after.isoformat()}
        return {"available": True, "data_end": after.isoformat(), **loaded}

    return router

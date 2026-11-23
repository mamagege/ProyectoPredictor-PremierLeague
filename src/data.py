"""Módulo de ingesta, normalización, consolidación y búsqueda causal de datos EPL."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.config import (
    ELO_RATINGS_CSV,
    MATCHES_CSV,
    PREMIER_LEAGUE_CSV,
    infer_epl_season,
    normalize_season_label,
)

logger = logging.getLogger(__name__)


def _normalize_raw_team_col(series: pd.Series) -> pd.Series:
    """Estandariza nombres conocidos entre Kaggle CSVs manteniendo nombres canónicos."""
    return series.astype(str).str.strip().replace({"Nottm Forest": "Nott'm Forest"})


def _to_naive_utc_ts(dt: pd.Timestamp | str) -> pd.Timestamp:
    ts = pd.Timestamp(dt)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


def load_elo_ratings(elo_csv: Path | str = ELO_RATINGS_CSV) -> pd.DataFrame:
    """Carga y normaliza el histórico Elo de clubes ingleses desde EloRatings.csv."""
    df_elo = pd.read_csv(elo_csv)
    df_eng = df_elo[df_elo["country"] == "ENG"].copy()
    raw_club = df_eng["club"].astype(str).str.strip()
    # Priorizar registros ya etiquetados como "Nott'm Forest" frente a "Nottm Forest" congelados (2025-2026)
    df_eng["_canonical_priority"] = (raw_club != "Nottm Forest").astype(int)
    df_eng["club"] = _normalize_raw_team_col(raw_club)
    df_eng["date"] = pd.to_datetime(df_eng["date"], errors="raise")
    df_eng["elo"] = pd.to_numeric(df_eng["elo"], errors="raise").astype(float)
    df_eng = (
        df_eng.sort_values(["club", "date", "_canonical_priority"])
        .drop_duplicates(subset=["club", "date"], keep="last")
        .drop(columns=["_canonical_priority"])
        .reset_index(drop=True)
    )
    logger.debug("EloRatings ENG cargado: %d registros, %d clubes.", len(df_eng), df_eng["club"].nunique())
    return df_eng[["date", "club", "elo"]]


@dataclass
class EloLookup:
    """Índice en memoria para consulta causal O(log n) de Elo en fecha <= target_date."""

    _clubs: dict[str, tuple[np.ndarray, np.ndarray]]

    @classmethod
    def from_dataframe(cls, df_elo: pd.DataFrame) -> "EloLookup":
        clubs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for club, grp in df_elo.groupby("club", sort=False):
            grp_sorted = grp.sort_values("date")
            dates_i64 = grp_sorted["date"].to_numpy(dtype="datetime64[ns]").astype(np.int64)
            elos_f64 = grp_sorted["elo"].to_numpy(dtype=np.float64)
            clubs[str(club)] = (dates_i64, elos_f64)
        return cls(_clubs=clubs)

    @classmethod
    def from_csv(cls, elo_csv: Path | str = ELO_RATINGS_CSV) -> "EloLookup":
        return cls.from_dataframe(load_elo_ratings(elo_csv))

    def get_elo(self, team: str, target_date: pd.Timestamp | str) -> Optional[float]:
        """Retorna el rating Elo más reciente registrado en fecha <= target_date."""
        entry = self._clubs.get(team)
        if entry is None:
            return None
        dates_i64, elos_f64 = entry
        ts = _to_naive_utc_ts(target_date)
        ts_i64 = np.datetime64(ts, "ns").astype(np.int64)
        idx = int(np.searchsorted(dates_i64, ts_i64, side="right")) - 1
        if idx < 0:
            return None
        return float(elos_f64[idx])

    def get_elo_series(self, teams: pd.Series, dates: pd.Series) -> np.ndarray:
        """Consulta vectorizada equivalente paso a paso a get_elo."""
        out = np.full(len(teams), np.nan, dtype=np.float64)
        for i, (team, dt) in enumerate(zip(teams, dates)):
            val = self.get_elo(str(team), dt)
            if val is not None:
                out[i] = val
        return out


def load_unified_matches(
    premier_league_csv: Path | str = PREMIER_LEAGUE_CSV,
    matches_csv: Path | str = MATCHES_CSV,
    elo_csv: Path | str = ELO_RATINGS_CSV,
    include_prospective: bool = True,
) -> tuple[pd.DataFrame, EloLookup]:
    """
    Construye el historial unificado de la EPL sin huecos temporales:
    - Base 2000/01-2024/25 desde PremierLeague.csv (9,500 partidos = 25 x 380 exactos).
    - Cuotas de respaldo desde Matches.csv (Division == 'E0').
    - Partidos prospectivos 2025/26+ desde Matches.csv (E0) si include_prospective=True.
    - Elo estrictamente causal obtenido de manera uniforme desde EloLookup (date <= MatchDate),
      garantizando paridad matemática exacta entre entrenamiento e inferencia.
    """
    df_prem = pd.read_csv(premier_league_csv, low_memory=False)
    df_prem["MatchDate"] = pd.to_datetime(df_prem["Date"], errors="raise")
    df_prem = df_prem[df_prem["MatchDate"] >= pd.Timestamp("2000-08-01")].copy()

    base = pd.DataFrame(
        {
            "MatchDate": df_prem["MatchDate"],
            "Season": df_prem["Season"].map(normalize_season_label),
            "HomeTeam": _normalize_raw_team_col(df_prem["HomeTeam"]),
            "AwayTeam": _normalize_raw_team_col(df_prem["AwayTeam"]),
            "FullTimeHomeGoals": pd.to_numeric(df_prem["FullTimeHomeTeamGoals"], errors="raise").astype(int),
            "FullTimeAwayGoals": pd.to_numeric(df_prem["FullTimeAwayTeamGoals"], errors="raise").astype(int),
            "FullTimeResult": df_prem["FullTimeResult"].astype(str).str.strip(),
            "HomeShots": pd.to_numeric(df_prem["HomeTeamShots"], errors="coerce").astype(float),
            "AwayShots": pd.to_numeric(df_prem["AwayTeamShots"], errors="coerce").astype(float),
            "HomeShotsOnTarget": pd.to_numeric(df_prem["HomeTeamShotsOnTarget"], errors="coerce").astype(float),
            "AwayShotsOnTarget": pd.to_numeric(df_prem["AwayTeamShotsOnTarget"], errors="coerce").astype(float),
            "B365HomeTeam": pd.to_numeric(df_prem["B365HomeTeam"], errors="coerce").astype(float),
            "B365Draw": pd.to_numeric(df_prem["B365Draw"], errors="coerce").astype(float),
            "B365AwayTeam": pd.to_numeric(df_prem["B365AwayTeam"], errors="coerce").astype(float),
        }
    )

    df_matches = pd.read_csv(matches_csv, low_memory=False)
    df_e0 = df_matches[df_matches["Division"] == "E0"].copy()
    df_e0["MatchDate"] = pd.to_datetime(df_e0["MatchDate"], errors="raise")
    df_e0["HomeTeam"] = _normalize_raw_team_col(df_e0["HomeTeam"])
    df_e0["AwayTeam"] = _normalize_raw_team_col(df_e0["AwayTeam"])

    # Enriquecer 2000/01-2024/25 con cuotas respaldo (OddHome/Draw/Away) via LEFT JOIN
    e0_odds = df_e0[["MatchDate", "HomeTeam", "AwayTeam", "OddHome", "OddDraw", "OddAway"]].drop_duplicates(
        subset=["MatchDate", "HomeTeam", "AwayTeam"], keep="first"
    )
    unified = pd.merge(
        base,
        e0_odds,
        on=["MatchDate", "HomeTeam", "AwayTeam"],
        how="left",
    )

    if include_prospective:
        max_prem_date = unified["MatchDate"].max()
        df_post = df_e0[df_e0["MatchDate"] > max_prem_date].copy()
        if not df_post.empty:
            post_frame = pd.DataFrame(
                {
                    "MatchDate": df_post["MatchDate"],
                    "Season": df_post["MatchDate"].map(infer_epl_season),
                    "HomeTeam": df_post["HomeTeam"],
                    "AwayTeam": df_post["AwayTeam"],
                    "FullTimeHomeGoals": pd.to_numeric(df_post["FTHome"], errors="raise").astype(int),
                    "FullTimeAwayGoals": pd.to_numeric(df_post["FTAway"], errors="raise").astype(int),
                    "FullTimeResult": df_post["FTResult"].astype(str).str.strip(),
                    "HomeShots": pd.to_numeric(df_post["HomeShots"], errors="coerce").astype(float),
                    "AwayShots": pd.to_numeric(df_post["AwayShots"], errors="coerce").astype(float),
                    "HomeShotsOnTarget": pd.to_numeric(df_post["HomeTarget"], errors="coerce").astype(float),
                    "AwayShotsOnTarget": pd.to_numeric(df_post["AwayTarget"], errors="coerce").astype(float),
                    "B365HomeTeam": pd.to_numeric(df_post["OddHome"], errors="coerce").astype(float),
                    "B365Draw": pd.to_numeric(df_post["OddDraw"], errors="coerce").astype(float),
                    "B365AwayTeam": pd.to_numeric(df_post["OddAway"], errors="coerce").astype(float),
                    "OddHome": pd.to_numeric(df_post["OddHome"], errors="coerce").astype(float),
                    "OddDraw": pd.to_numeric(df_post["OddDraw"], errors="coerce").astype(float),
                    "OddAway": pd.to_numeric(df_post["OddAway"], errors="coerce").astype(float),
                }
            )
            unified = pd.concat([unified, post_frame], ignore_index=True)

    unified = unified.sort_values(["MatchDate", "HomeTeam", "AwayTeam"]).reset_index(drop=True)

    # Cuotas consolidadas pre-partido (Bet365 primaria, Odd* respaldo)
    unified["Odds_H"] = unified["B365HomeTeam"].combine_first(unified["OddHome"])
    unified["Odds_D"] = unified["B365Draw"].combine_first(unified["OddDraw"])
    unified["Odds_A"] = unified["B365AwayTeam"].combine_first(unified["OddAway"])

    # Invalidar cuotas no válidas (<= 1.0) para evitar probabilidades degeneradas
    for col in ("Odds_H", "Odds_D", "Odds_A"):
        unified.loc[unified[col] <= 1.0, col] = np.nan

    # Rating Elo causal uniforme desde EloRatings.csv (date <= MatchDate)
    elo_lookup = EloLookup.from_csv(elo_csv)
    unified["HomeElo"] = elo_lookup.get_elo_series(unified["HomeTeam"], unified["MatchDate"])
    unified["AwayElo"] = elo_lookup.get_elo_series(unified["AwayTeam"], unified["MatchDate"])

    # Verificaciones estrictas de integridad
    dup_count = int(unified.duplicated(subset=["MatchDate", "HomeTeam", "AwayTeam"]).sum())
    if dup_count > 0:
        raise ValueError(f"Se detectaron {dup_count} partidos duplicados tras la consolidación.")
    valid_results = {"H", "D", "A"}
    bad_results = set(unified["FullTimeResult"].unique()) - valid_results
    if bad_results:
        raise ValueError(f"Resultados inválidos en FullTimeResult: {bad_results}")

    return unified, elo_lookup

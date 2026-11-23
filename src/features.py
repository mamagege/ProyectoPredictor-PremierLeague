"""Motor único de ingeniería de características pre-partido y preprocesador causal sin fuga."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.config import SEED, infer_epl_season
from src.data import EloLookup

logger = logging.getLogger(__name__)


def _to_naive_utc_timestamp(dt: pd.Timestamp | str) -> pd.Timestamp:
    """Convierte cualquier fecha o timestamp ISO (incluyendo tz-aware) a UTC naive normalizado."""
    ts = pd.Timestamp(dt)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


def _infer_season_causal(
    target_ts: pd.Timestamp,
    prev_match_ts: Optional[pd.Timestamp],
    prev_match_season: Optional[str],
) -> str:
    """
    Infiere la temporada mirando ÚNICAMENTE partidos estrictamente anteriores (< target_ts),
    preservando extensiones excepcionales de temporada (ej. julio 2020 COVID) sin fuga futura.
    """
    if prev_match_ts is not None and prev_match_season is not None:
        if (target_ts - prev_match_ts).days <= 21:
            return prev_match_season
    return infer_epl_season(target_ts)

# 45 características estrictamente pre-partido (eliminando redundancia Form5 == 5 * RollingPts5)
FEATURE_NAMES: list[str] = [
    # Mercado (5)
    "ProbMarket_Home",
    "ProbMarket_Draw",
    "ProbMarket_Away",
    "MarketEntropy",
    "MarketFavMargin",
    # Elo (4)
    "HomeElo",
    "AwayElo",
    "DiffElo",
    "EloProb_Home",
    # Forma rodante general últimos 3 y 5 partidos (18)
    "RollingPts3_Home",
    "RollingPts3_Away",
    "DiffRollingPts3",
    "RollingPts5_Home",
    "RollingPts5_Away",
    "DiffRollingPts5",
    "RollingGF5_Home",
    "RollingGF5_Away",
    "DiffRollingGF5",
    "RollingGA5_Home",
    "RollingGA5_Away",
    "DiffRollingGA5",
    "RollingShots5_Home",
    "RollingShots5_Away",
    "DiffRollingShots5",
    "RollingSoT5_Home",
    "RollingSoT5_Away",
    "DiffRollingSoT5",
    # Forma específica de sede últimos 5 partidos como local / visitante (6)
    "VenuePts5_Home",
    "VenuePts5_Away",
    "DiffVenuePts5",
    "VenueGD5_Home",
    "VenueGD5_Away",
    "DiffVenueGD5",
    # Días de descanso (3)
    "RestDays_Home",
    "RestDays_Away",
    "DiffRestDays",
    # Acumulado de temporada vigente (reseteado estrictamente por temporada) (6)
    "SeasonPts_Home",
    "SeasonPts_Away",
    "DiffSeasonPts",
    "SeasonGD_Home",
    "SeasonGD_Away",
    "DiffSeasonGD",
    # Historial directo suavizado con priors de entrenamiento (3)
    "H2H_HomeWins",
    "H2H_Draws",
    "H2H_AwayWins",
]

MARKET_FEATURE_NAMES: list[str] = [
    "ProbMarket_Home",
    "ProbMarket_Draw",
    "ProbMarket_Away",
    "MarketEntropy",
    "MarketFavMargin",
]

NON_MARKET_FEATURE_NAMES: list[str] = [
    f for f in FEATURE_NAMES if f not in set(MARKET_FEATURE_NAMES)
]

# Valores neutros por defecto solo cuando un equipo aún no tiene partidos en la base histórica
_DEFAULT_PTS = 1.3
_DEFAULT_GF = 1.3
_DEFAULT_GA = 1.3
_DEFAULT_SHOTS = 11.5
_DEFAULT_SOT = 4.2
_DEFAULT_REST = 7.0
_H2H_WINDOW = 10
_H2H_SMOOTHING_ALPHA = 3.0


def _compute_elo_prob_home(home_elo: np.ndarray | float, away_elo: np.ndarray | float) -> np.ndarray | float:
    diff = home_elo - away_elo
    return 1.0 / (1.0 + 10.0 ** ((-diff - 100.0) / 400.0))


def _compute_market_probs_from_odds(odds_h: float, odds_d: float, odds_a: float) -> tuple[float, float, float]:
    inv_h = 1.0 / float(odds_h)
    inv_d = 1.0 / float(odds_d)
    inv_a = 1.0 / float(odds_a)
    overround = inv_h + inv_d + inv_a
    return inv_h / overround, inv_d / overround, inv_a / overround


@dataclass
class CausalPreprocessor:
    """
    Preprocesador causal ajustado EXCLUSIVAMENTE sobre el conjunto de entrenamiento:
    - Priors empíricos de clases (train_priors_) para suavizado H2H y fallbacks.
    - Mediana Elo de entrenamiento (train_elo_median_) como último recurso si faltara Elo.
    - Modelo Elo->Mercado (elo_market_fallback_) ajustado solo en Train cuando no hay cuotas.
    - StandardScaler ajustado exclusivamente en Train.
    """

    feature_names: list[str] = field(default_factory=lambda: list(FEATURE_NAMES))
    train_priors_: np.ndarray = field(default_factory=lambda: np.array([0.46, 0.25, 0.29], dtype=np.float64))
    train_elo_median_: float = 1700.0
    elo_market_fallback_: Optional[LogisticRegression] = None
    scaler_: StandardScaler = field(default_factory=StandardScaler)
    is_fitted_: bool = False

    def _build_elo_features_df(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        out = df_raw.copy()
        out["HomeElo"] = out["HomeElo"].fillna(self.train_elo_median_).astype(float)
        out["AwayElo"] = out["AwayElo"].fillna(self.train_elo_median_).astype(float)
        out["DiffElo"] = out["HomeElo"] - out["AwayElo"]
        out["EloProb_Home"] = _compute_elo_prob_home(out["HomeElo"], out["AwayElo"])
        return out

    def fit(self, df_raw_train: pd.DataFrame, y_train: np.ndarray) -> "CausalPreprocessor":
        """Ajusta todos los parámetros estadísticos y de escala usando SOLO Train."""
        counts = np.bincount(y_train, minlength=3).astype(np.float64)
        self.train_priors_ = counts / counts.sum()

        elo_vals = pd.concat([df_raw_train["HomeElo"], df_raw_train["AwayElo"]]).dropna()
        self.train_elo_median_ = float(elo_vals.median()) if not elo_vals.empty else 1700.0

        df_elo = self._build_elo_features_df(df_raw_train)

        # Ajustar modelo auxiliar Elo -> probabilidades de mercado usando solo filas con cuotas en Train
        valid_odds_mask = (
            df_elo["Odds_H"].notna()
            & df_elo["Odds_D"].notna()
            & df_elo["Odds_A"].notna()
            & (df_elo["Odds_H"] > 1.0)
            & (df_elo["Odds_D"] > 1.0)
            & (df_elo["Odds_A"] > 1.0)
        )
        elo_cols = ["HomeElo", "AwayElo", "DiffElo", "EloProb_Home"]
        fit_mask = valid_odds_mask.to_numpy() if valid_odds_mask.sum() >= 100 else np.ones(len(df_elo), dtype=bool)
        fallback = LogisticRegression(max_iter=1000, random_state=SEED)
        fallback.fit(df_elo.loc[fit_mask, elo_cols].to_numpy(dtype=np.float64), y_train[fit_mask])
        self.elo_market_fallback_ = fallback

        df_final = self.finalize_features_df(df_raw_train)
        X_train_raw = df_final[self.feature_names].to_numpy(dtype=np.float64)
        self.scaler_ = StandardScaler()
        self.scaler_.fit(X_train_raw)
        self.is_fitted_ = True
        return self

    def finalize_features_df(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Convierte un DataFrame de estadísticas brutas pre-partido en las 45 features finales
        sin fuga (imputación causal de Elo, cuotas con fallback Elo, entropía, H2H suavizado).
        """
        out = self._build_elo_features_df(df_raw)

        valid_odds = (
            out["Odds_H"].notna()
            & out["Odds_D"].notna()
            & out["Odds_A"].notna()
            & (out["Odds_H"] > 1.0)
            & (out["Odds_D"] > 1.0)
            & (out["Odds_A"] > 1.0)
        )

        p_h = np.zeros(len(out), dtype=np.float64)
        p_d = np.zeros(len(out), dtype=np.float64)
        p_a = np.zeros(len(out), dtype=np.float64)

        if valid_odds.any():
            raw_h = 1.0 / out.loc[valid_odds, "Odds_H"].to_numpy(dtype=np.float64)
            raw_d = 1.0 / out.loc[valid_odds, "Odds_D"].to_numpy(dtype=np.float64)
            raw_a = 1.0 / out.loc[valid_odds, "Odds_A"].to_numpy(dtype=np.float64)
            overround = raw_h + raw_d + raw_a
            p_h[valid_odds] = raw_h / overround
            p_d[valid_odds] = raw_d / overround
            p_a[valid_odds] = raw_a / overround

        missing_odds = ~valid_odds
        if missing_odds.any():
            if self.elo_market_fallback_ is not None:
                elo_cols = ["HomeElo", "AwayElo", "DiffElo", "EloProb_Home"]
                probs_fb = self.elo_market_fallback_.predict_proba(
                    out.loc[missing_odds, elo_cols].to_numpy(dtype=np.float64)
                )
                p_h[missing_odds] = probs_fb[:, 0]
                p_d[missing_odds] = probs_fb[:, 1]
                p_a[missing_odds] = probs_fb[:, 2]
            else:
                p_h[missing_odds] = self.train_priors_[0]
                p_d[missing_odds] = self.train_priors_[1]
                p_a[missing_odds] = self.train_priors_[2]

        out["ProbMarket_Home"] = p_h
        out["ProbMarket_Draw"] = p_d
        out["ProbMarket_Away"] = p_a

        probs_mat = np.clip(np.column_stack([p_h, p_d, p_a]), 1e-12, 1.0)
        out["MarketEntropy"] = -np.sum(probs_mat * np.log(probs_mat), axis=1)
        out["MarketFavMargin"] = np.abs(p_h - p_a)

        # Suavizado Bayesiano / Dirichlet del historial directo (H2H últimos 10)
        n_h2h = out["_raw_h2h_n"].to_numpy(dtype=np.float64)
        denom = n_h2h + _H2H_SMOOTHING_ALPHA
        out["H2H_HomeWins"] = (
            out["_raw_h2h_hw"].to_numpy(dtype=np.float64) + _H2H_SMOOTHING_ALPHA * self.train_priors_[0]
        ) / denom
        out["H2H_Draws"] = (
            out["_raw_h2h_d"].to_numpy(dtype=np.float64) + _H2H_SMOOTHING_ALPHA * self.train_priors_[1]
        ) / denom
        out["H2H_AwayWins"] = (
            out["_raw_h2h_aw"].to_numpy(dtype=np.float64) + _H2H_SMOOTHING_ALPHA * self.train_priors_[2]
        ) / denom

        missing_cols = [c for c in self.feature_names if c not in out.columns]
        if missing_cols:
            raise ValueError(f"Faltan columnas requeridas: {missing_cols}")

        return out

    def transform_df(
        self,
        df_raw: pd.DataFrame,
        selected_features: Optional[list[str]] = None,
    ) -> np.ndarray:
        """Transforma un DataFrame crudo en la matriz estandarizada lista para el modelo."""
        if not self.is_fitted_:
            raise RuntimeError("CausalPreprocessor debe ajustarse primero con .fit().")
        df_fin = self.finalize_features_df(df_raw)
        X_all = df_fin[self.feature_names].to_numpy(dtype=np.float64)
        if not np.all(np.isfinite(X_all)):
            raise ValueError("Se detectaron valores NaN o infinitos en las características.")
        X_scaled = self.scaler_.transform(X_all)
        if selected_features is None or selected_features == self.feature_names:
            return X_scaled
        idx_map = {name: i for i, name in enumerate(self.feature_names)}
        indices = [idx_map[name] for name in selected_features]
        return X_scaled[:, indices]

    def transform_single(
        self,
        raw_features: dict[str, Any],
        selected_features: Optional[list[str]] = None,
    ) -> tuple[np.ndarray, dict[str, float]]:
        """
        Ejecuta exactamente la misma transformación que transform_df sobre un único partido.
        Retorna (X_scaled_row, finalized_feature_dict).
        """
        if not self.is_fitted_:
            raise RuntimeError("CausalPreprocessor debe ajustarse primero con .fit().")
        df_one = pd.DataFrame([raw_features])
        df_fin = self.finalize_features_df(df_one)
        fin_dict = {name: float(df_fin.iloc[0][name]) for name in self.feature_names}
        X_scaled = self.transform_df(df_one, selected_features=selected_features)
        return X_scaled, fin_dict


def _extract_team_rolling_stats(
    t_hist: list[dict[str, Any]],
    venue_hist: list[dict[str, Any]],
    match_date: pd.Timestamp,
) -> dict[str, float]:
    """Calcula métricas rodantes generales (k=3, k=5), específicas de sede (k=5) y descanso."""
    if not t_hist:
        pts3 = _DEFAULT_PTS
        pts5 = _DEFAULT_PTS
        gf5 = _DEFAULT_GF
        ga5 = _DEFAULT_GA
        shots5 = _DEFAULT_SHOTS
        sot5 = _DEFAULT_SOT
        rest_days = _DEFAULT_REST
    else:
        sub3 = t_hist[-3:]
        sub5 = t_hist[-5:]
        pts3 = sum(m["pts"] for m in sub3) / len(sub3)
        n5 = len(sub5)
        pts5 = sum(m["pts"] for m in sub5) / n5
        gf5 = sum(m["gf"] for m in sub5) / n5
        ga5 = sum(m["ga"] for m in sub5) / n5
        shots5 = sum(m["shots"] for m in sub5) / n5
        sot5 = sum(m["sot"] for m in sub5) / n5
        last_date = t_hist[-1]["date"]
        rest_days = min(30.0, max(1.0, float((match_date - last_date).days)))

    if not venue_hist:
        v_pts5 = _DEFAULT_PTS
        v_gd5 = 0.0
    else:
        v_sub5 = venue_hist[-5:]
        nv = len(v_sub5)
        v_pts5 = sum(m["pts"] for m in v_sub5) / nv
        v_gd5 = sum(m["gf"] - m["ga"] for m in v_sub5) / nv

    return {
        "pts3": float(pts3),
        "pts5": float(pts5),
        "gf5": float(gf5),
        "ga5": float(ga5),
        "shots5": float(shots5),
        "sot5": float(sot5),
        "rest": float(rest_days),
        "venue_pts5": float(v_pts5),
        "venue_gd5": float(v_gd5),
    }


def _assemble_raw_match_row(
    h_team: str,
    a_team: str,
    home_elo: float,
    away_elo: float,
    odds_h: float,
    odds_d: float,
    odds_a: float,
    h_roll: dict[str, float],
    a_roll: dict[str, float],
    h_season: dict[str, float],
    a_season: dict[str, float],
    past_h2h: list[str],
) -> dict[str, Any]:
    """Ensambla el diccionario bruto compartido entre modo batch e inferencia individual."""
    recent_h2h = past_h2h[-_H2H_WINDOW:]
    n_h2h = len(recent_h2h)
    hw = sum(1 for winner in recent_h2h if winner == h_team)
    d_cnt = sum(1 for winner in recent_h2h if winner == "D")
    aw = sum(1 for winner in recent_h2h if winner == a_team)

    return {
        "Odds_H": odds_h,
        "Odds_D": odds_d,
        "Odds_A": odds_a,
        "HomeElo": home_elo,
        "AwayElo": away_elo,
        "RollingPts3_Home": h_roll["pts3"],
        "RollingPts3_Away": a_roll["pts3"],
        "DiffRollingPts3": h_roll["pts3"] - a_roll["pts3"],
        "RollingPts5_Home": h_roll["pts5"],
        "RollingPts5_Away": a_roll["pts5"],
        "DiffRollingPts5": h_roll["pts5"] - a_roll["pts5"],
        "RollingGF5_Home": h_roll["gf5"],
        "RollingGF5_Away": a_roll["gf5"],
        "DiffRollingGF5": h_roll["gf5"] - a_roll["gf5"],
        "RollingGA5_Home": h_roll["ga5"],
        "RollingGA5_Away": a_roll["ga5"],
        "DiffRollingGA5": h_roll["ga5"] - a_roll["ga5"],
        "RollingShots5_Home": h_roll["shots5"],
        "RollingShots5_Away": a_roll["shots5"],
        "DiffRollingShots5": h_roll["shots5"] - a_roll["shots5"],
        "RollingSoT5_Home": h_roll["sot5"],
        "RollingSoT5_Away": a_roll["sot5"],
        "DiffRollingSoT5": h_roll["sot5"] - a_roll["sot5"],
        "VenuePts5_Home": h_roll["venue_pts5"],
        "VenuePts5_Away": a_roll["venue_pts5"],
        "DiffVenuePts5": h_roll["venue_pts5"] - a_roll["venue_pts5"],
        "VenueGD5_Home": h_roll["venue_gd5"],
        "VenueGD5_Away": a_roll["venue_gd5"],
        "DiffVenueGD5": h_roll["venue_gd5"] - a_roll["venue_gd5"],
        "RestDays_Home": h_roll["rest"],
        "RestDays_Away": a_roll["rest"],
        "DiffRestDays": h_roll["rest"] - a_roll["rest"],
        "SeasonPts_Home": float(h_season["pts"]),
        "SeasonPts_Away": float(a_season["pts"]),
        "DiffSeasonPts": float(h_season["pts"] - a_season["pts"]),
        "SeasonGD_Home": float(h_season["gf"] - h_season["ga"]),
        "SeasonGD_Away": float(a_season["gf"] - a_season["ga"]),
        "DiffSeasonGD": float((h_season["gf"] - h_season["ga"]) - (a_season["gf"] - a_season["ga"])),
        "_raw_h2h_hw": float(hw),
        "_raw_h2h_d": float(d_cnt),
        "_raw_h2h_aw": float(aw),
        "_raw_h2h_n": float(n_h2h),
    }


class FeatureStateEngine:
    """
    Fuente única de verdad para el cálculo causal de variables pre-partido,
    compartida entre el pipeline batch (entrenamiento/evaluación) y la inferencia puntual.
    """

    @staticmethod
    def compute_batch_features(df_matches: pd.DataFrame) -> pd.DataFrame:
        """
        Recorre df_matches en orden cronológico estricto calculando todas las variables
        pre-partido antes de actualizar el historial con el desenlace de cada partido.
        """
        df_sorted = df_matches.sort_values(["MatchDate", "HomeTeam", "AwayTeam"]).reset_index(drop=True)

        team_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        home_venue_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        away_venue_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        season_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0})
        h2h_records: dict[tuple[str, str], list[str]] = defaultdict(list)

        rows_out: list[dict[str, Any]] = []

        for row in df_sorted.itertuples(index=False):
            h_team = row.HomeTeam
            a_team = row.AwayTeam
            m_date = pd.Timestamp(row.MatchDate)
            season = row.Season

            h_roll = _extract_team_rolling_stats(team_history[h_team], home_venue_history[h_team], m_date)
            a_roll = _extract_team_rolling_stats(team_history[a_team], away_venue_history[a_team], m_date)

            s_h = season_stats[(season, h_team)]
            s_a = season_stats[(season, a_team)]

            h2h_key = (h_team, a_team) if h_team <= a_team else (a_team, h_team)
            past_h2h = h2h_records[h2h_key]

            raw_row = _assemble_raw_match_row(
                h_team=h_team,
                a_team=a_team,
                home_elo=float(row.HomeElo) if pd.notna(row.HomeElo) else np.nan,
                away_elo=float(row.AwayElo) if pd.notna(row.AwayElo) else np.nan,
                odds_h=float(row.Odds_H) if pd.notna(row.Odds_H) else np.nan,
                odds_d=float(row.Odds_D) if pd.notna(row.Odds_D) else np.nan,
                odds_a=float(row.Odds_A) if pd.notna(row.Odds_A) else np.nan,
                h_roll=h_roll,
                a_roll=a_roll,
                h_season=s_h,
                a_season=s_a,
                past_h2h=past_h2h,
            )
            rows_out.append(raw_row)

            # Actualización estrictamente POST-PARTIDO
            ft_res = row.FullTimeResult
            h_goals = int(row.FullTimeHomeGoals)
            a_goals = int(row.FullTimeAwayGoals)
            h_shots = float(row.HomeShots) if pd.notna(row.HomeShots) else _DEFAULT_SHOTS
            a_shots = float(row.AwayShots) if pd.notna(row.AwayShots) else _DEFAULT_SHOTS
            h_sot = float(row.HomeShotsOnTarget) if pd.notna(row.HomeShotsOnTarget) else _DEFAULT_SOT
            a_sot = float(row.AwayShotsOnTarget) if pd.notna(row.AwayShotsOnTarget) else _DEFAULT_SOT

            if ft_res == "H":
                h_p, a_p, winner = 3, 0, h_team
            elif ft_res == "A":
                h_p, a_p, winner = 0, 3, a_team
            else:
                h_p, a_p, winner = 1, 1, "D"

            h_entry = {"date": m_date, "pts": h_p, "gf": h_goals, "ga": a_goals, "shots": h_shots, "sot": h_sot}
            a_entry = {"date": m_date, "pts": a_p, "gf": a_goals, "ga": h_goals, "shots": a_shots, "sot": a_sot}

            team_history[h_team].append(h_entry)
            team_history[a_team].append(a_entry)
            home_venue_history[h_team].append(h_entry)
            away_venue_history[a_team].append(a_entry)

            s_h["pts"] += h_p
            s_h["gf"] += h_goals
            s_h["ga"] += a_goals
            s_a["pts"] += a_p
            s_a["gf"] += a_goals
            s_a["ga"] += h_goals
            h2h_records[h2h_key].append(winner)

        df_raw = pd.DataFrame(rows_out)
        # Conservar metadatos necesarios para partición y evaluación
        for meta_col in ("MatchDate", "Season", "HomeTeam", "AwayTeam", "FullTimeResult"):
            df_raw[meta_col] = df_sorted[meta_col].values
        return df_raw

    @staticmethod
    def compute_single_match_features(
        df_history: pd.DataFrame,
        elo_lookup: EloLookup,
        home_team: str,
        away_team: str,
        match_date: pd.Timestamp | str | None = None,
        odds: Optional[tuple[float, float, float] | list[float]] = None,
        history_index: Optional["MatchHistoryIndex"] = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Calcula las variables brutas pre-partido para un encuentro puntual usando
        exclusivamente registros con MatchDate < match_date (o todo el historial si match_date=None).
        """
        if history_index is not None:
            return history_index.compute_single_match_features(
                elo_lookup=elo_lookup,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                odds=odds,
            )

        if match_date is not None:
            target_ts = _to_naive_utc_timestamp(match_date)
            hist_before = df_history[df_history["MatchDate"] < target_ts]
            ref_date = target_ts
        else:
            hist_before = df_history
            last_max = pd.Timestamp(df_history["MatchDate"].max())
            ref_date = last_max + pd.Timedelta(days=7)

        if not hist_before.empty:
            prev_row = hist_before.iloc[-1]
            target_season = _infer_season_causal(
                ref_date,
                pd.Timestamp(prev_row["MatchDate"]),
                str(prev_row["Season"]),
            )
        else:
            target_season = infer_epl_season(ref_date)

        def _collect_team_state(team: str, is_home_target: bool) -> tuple[dict[str, float], dict[str, int], int]:
            team_rows = hist_before[(hist_before["HomeTeam"] == team) | (hist_before["AwayTeam"] == team)]
            if team_rows.empty:
                return (
                    _extract_team_rolling_stats([], [], ref_date),
                    {"pts": 0, "gf": 0, "ga": 0},
                    0,
                )

            t_hist: list[dict[str, Any]] = []
            venue_hist: list[dict[str, Any]] = []
            s_pts = 0
            s_gf = 0
            s_ga = 0

            for r in team_rows.itertuples(index=False):
                m_dt = pd.Timestamp(r.MatchDate)
                played_home = r.HomeTeam == team
                res = r.FullTimeResult
                if played_home:
                    pts = 3 if res == "H" else (1 if res == "D" else 0)
                    gf = int(r.FullTimeHomeGoals)
                    ga = int(r.FullTimeAwayGoals)
                    sh = float(r.HomeShots) if pd.notna(r.HomeShots) else _DEFAULT_SHOTS
                    sot = float(r.HomeShotsOnTarget) if pd.notna(r.HomeShotsOnTarget) else _DEFAULT_SOT
                else:
                    pts = 3 if res == "A" else (1 if res == "D" else 0)
                    gf = int(r.FullTimeAwayGoals)
                    ga = int(r.FullTimeHomeGoals)
                    sh = float(r.AwayShots) if pd.notna(r.AwayShots) else _DEFAULT_SHOTS
                    sot = float(r.AwayShotsOnTarget) if pd.notna(r.AwayShotsOnTarget) else _DEFAULT_SOT

                entry = {"date": m_dt, "pts": pts, "gf": gf, "ga": ga, "shots": sh, "sot": sot}
                t_hist.append(entry)
                if (is_home_target and played_home) or ((not is_home_target) and (not played_home)):
                    venue_hist.append(entry)

                if r.Season == target_season:
                    s_pts += pts
                    s_gf += gf
                    s_ga += ga

            rolling = _extract_team_rolling_stats(t_hist, venue_hist, ref_date)
            return rolling, {"pts": s_pts, "gf": s_gf, "ga": s_ga}, len(t_hist)

        h_roll, h_season, h_n_hist = _collect_team_state(home_team, is_home_target=True)
        a_roll, a_season, a_n_hist = _collect_team_state(away_team, is_home_target=False)

        h2h_rows = hist_before[
            ((hist_before["HomeTeam"] == home_team) & (hist_before["AwayTeam"] == away_team))
            | ((hist_before["HomeTeam"] == away_team) & (hist_before["AwayTeam"] == home_team))
        ]
        past_h2h: list[str] = []
        for r in h2h_rows.itertuples(index=False):
            if r.FullTimeResult == "H":
                past_h2h.append(r.HomeTeam)
            elif r.FullTimeResult == "A":
                past_h2h.append(r.AwayTeam)
            else:
                past_h2h.append("D")

        elo_date = _to_naive_utc_timestamp(match_date) if match_date is not None else ref_date
        home_elo = elo_lookup.get_elo(home_team, elo_date)
        away_elo = elo_lookup.get_elo(away_team, elo_date)

        if odds is not None:
            odds_h, odds_d, odds_a = float(odds[0]), float(odds[1]), float(odds[2])
        else:
            odds_h, odds_d, odds_a = np.nan, np.nan, np.nan

        raw_row = _assemble_raw_match_row(
            h_team=home_team,
            a_team=away_team,
            home_elo=float(home_elo) if home_elo is not None else np.nan,
            away_elo=float(away_elo) if away_elo is not None else np.nan,
            odds_h=odds_h,
            odds_d=odds_d,
            odds_a=odds_a,
            h_roll=h_roll,
            a_roll=a_roll,
            h_season=h_season,
            a_season=a_season,
            past_h2h=past_h2h,
        )

        context = {
            "target_season": target_season,
            "ref_date": str(ref_date.date()),
            "home_history_matches": h_n_hist,
            "away_history_matches": a_n_hist,
            "h2h_matches_count": len(past_h2h),
        }
        return raw_row, context


@dataclass
class MatchHistoryIndex:
    """
    Índice cronológico en memoria O(log n) para inferencia rápida en tiempo real y en lote,
    con paridad matemática exacta respecto a FeatureStateEngine.compute_batch_features.
    """

    all_dates_ns: np.ndarray
    all_seasons: list[str]
    max_date: pd.Timestamp
    team_dates_ns: dict[str, np.ndarray]
    team_entries: dict[str, list[dict[str, Any]]]
    home_dates_ns: dict[str, np.ndarray]
    home_entries: dict[str, list[dict[str, Any]]]
    away_dates_ns: dict[str, np.ndarray]
    away_entries: dict[str, list[dict[str, Any]]]
    h2h_dates_ns: dict[tuple[str, str], np.ndarray]
    h2h_winners: dict[tuple[str, str], list[str]]

    @classmethod
    def from_dataframe(cls, df_history: pd.DataFrame) -> "MatchHistoryIndex":
        df_sorted = df_history.sort_values(["MatchDate", "HomeTeam", "AwayTeam"]).reset_index(drop=True)

        all_dates_list: list[int] = []
        all_seasons: list[str] = []
        t_dates: dict[str, list[int]] = defaultdict(list)
        t_entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
        h_dates: dict[str, list[int]] = defaultdict(list)
        h_entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
        a_dates: dict[str, list[int]] = defaultdict(list)
        a_entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
        h2h_d: dict[tuple[str, str], list[int]] = defaultdict(list)
        h2h_w: dict[tuple[str, str], list[str]] = defaultdict(list)

        for r in df_sorted.itertuples(index=False):
            m_dt = pd.Timestamp(r.MatchDate)
            ts_ns = int(np.datetime64(m_dt, "ns").astype(np.int64))
            season = str(r.Season)
            h_team = str(r.HomeTeam)
            a_team = str(r.AwayTeam)

            all_dates_list.append(ts_ns)
            all_seasons.append(season)

            ft_res = r.FullTimeResult
            h_goals = int(r.FullTimeHomeGoals)
            a_goals = int(r.FullTimeAwayGoals)
            h_shots = float(r.HomeShots) if pd.notna(r.HomeShots) else _DEFAULT_SHOTS
            a_shots = float(r.AwayShots) if pd.notna(r.AwayShots) else _DEFAULT_SHOTS
            h_sot = float(r.HomeShotsOnTarget) if pd.notna(r.HomeShotsOnTarget) else _DEFAULT_SOT
            a_sot = float(r.AwayShotsOnTarget) if pd.notna(r.AwayShotsOnTarget) else _DEFAULT_SOT

            if ft_res == "H":
                h_p, a_p, winner = 3, 0, h_team
            elif ft_res == "A":
                h_p, a_p, winner = 0, 3, a_team
            else:
                h_p, a_p, winner = 1, 1, "D"

            h_entry = {"date": m_dt, "season": season, "pts": h_p, "gf": h_goals, "ga": a_goals, "shots": h_shots, "sot": h_sot}
            a_entry = {"date": m_dt, "season": season, "pts": a_p, "gf": a_goals, "ga": h_goals, "shots": a_shots, "sot": a_sot}

            t_dates[h_team].append(ts_ns)
            t_entries[h_team].append(h_entry)
            h_dates[h_team].append(ts_ns)
            h_entries[h_team].append(h_entry)

            t_dates[a_team].append(ts_ns)
            t_entries[a_team].append(a_entry)
            a_dates[a_team].append(ts_ns)
            a_entries[a_team].append(a_entry)

            h2h_key = (h_team, a_team) if h_team <= a_team else (a_team, h_team)
            h2h_d[h2h_key].append(ts_ns)
            h2h_w[h2h_key].append(winner)

        max_date = pd.Timestamp(df_sorted["MatchDate"].max()) if not df_sorted.empty else pd.Timestamp("2000-08-19")
        return cls(
            all_dates_ns=np.asarray(all_dates_list, dtype=np.int64),
            all_seasons=all_seasons,
            max_date=max_date,
            team_dates_ns={k: np.asarray(v, dtype=np.int64) for k, v in t_dates.items()},
            team_entries=dict(t_entries),
            home_dates_ns={k: np.asarray(v, dtype=np.int64) for k, v in h_dates.items()},
            home_entries=dict(h_entries),
            away_dates_ns={k: np.asarray(v, dtype=np.int64) for k, v in a_dates.items()},
            away_entries=dict(a_entries),
            h2h_dates_ns={k: np.asarray(v, dtype=np.int64) for k, v in h2h_d.items()},
            h2h_winners=dict(h2h_w),
        )

    def _collect_team_state(
        self,
        team: str,
        is_home_target: bool,
        target_ns: int,
        ref_date: pd.Timestamp,
        target_season: str,
        k: int = 5,
    ) -> tuple[dict[str, float], dict[str, int], int]:
        t_dates = self.team_dates_ns.get(team)
        if t_dates is None:
            return _extract_team_rolling_stats([], [], ref_date), {"pts": 0, "gf": 0, "ga": 0}, 0
        end_t = int(np.searchsorted(t_dates, target_ns, side="left"))
        if end_t == 0:
            return _extract_team_rolling_stats([], [], ref_date), {"pts": 0, "gf": 0, "ga": 0}, 0

        t_list = self.team_entries[team]
        t_hist = t_list[max(0, end_t - max(k, 5)) : end_t]

        v_dates_map = self.home_dates_ns if is_home_target else self.away_dates_ns
        v_entries_map = self.home_entries if is_home_target else self.away_entries
        v_dates = v_dates_map.get(team)
        if v_dates is not None:
            end_v = int(np.searchsorted(v_dates, target_ns, side="left"))
            v_list = v_entries_map[team]
            venue_hist = v_list[max(0, end_v - 5) : end_v]
        else:
            venue_hist = []

        s_pts = 0
        s_gf = 0
        s_ga = 0
        for idx in range(end_t - 1, -1, -1):
            entry = t_list[idx]
            if entry["season"] != target_season:
                break
            s_pts += entry["pts"]
            s_gf += entry["gf"]
            s_ga += entry["ga"]

        rolling = _extract_team_rolling_stats(t_hist, venue_hist, ref_date)
        return rolling, {"pts": s_pts, "gf": s_gf, "ga": s_ga}, end_t

    def get_h2h_slice(
        self,
        home_team: str,
        away_team: str,
        target_ns: int,
        window: Optional[int] = _H2H_WINDOW,
    ) -> list[str]:
        h2h_key = (home_team, away_team) if home_team <= away_team else (away_team, home_team)
        h_dates = self.h2h_dates_ns.get(h2h_key)
        if h_dates is None:
            return []
        end_h = int(np.searchsorted(h_dates, target_ns, side="left"))
        if end_h == 0:
            return []
        winners = self.h2h_winners[h2h_key]
        if window is None:
            return winners[:end_h]
        return winners[max(0, end_h - window) : end_h]

    def resolve_target_context(self, match_date: pd.Timestamp | str | None) -> tuple[pd.Timestamp, int, str]:
        if match_date is not None:
            ref_date = _to_naive_utc_timestamp(match_date)
            target_ns = int(np.datetime64(ref_date, "ns").astype(np.int64))
            prev_idx = int(np.searchsorted(self.all_dates_ns, target_ns, side="left")) - 1
            prev_ts = pd.Timestamp(self.all_dates_ns[prev_idx], unit="ns") if prev_idx >= 0 else None
            prev_season = self.all_seasons[prev_idx] if prev_idx >= 0 else None
            target_season = _infer_season_causal(ref_date, prev_ts, prev_season)
        else:
            ref_date = self.max_date + pd.Timedelta(days=7)
            target_ns = int(np.datetime64(ref_date, "ns").astype(np.int64))
            prev_season = self.all_seasons[-1] if self.all_seasons else None
            target_season = _infer_season_causal(ref_date, self.max_date, prev_season)
        return ref_date, target_ns, target_season

    def compute_single_match_features(
        self,
        elo_lookup: EloLookup,
        home_team: str,
        away_team: str,
        match_date: pd.Timestamp | str | None = None,
        odds: Optional[tuple[float, float, float] | list[float]] = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        ref_date, target_ns, target_season = self.resolve_target_context(match_date)

        h_roll, h_season, h_n_hist = self._collect_team_state(
            home_team, True, target_ns, ref_date, target_season
        )
        a_roll, a_season, a_n_hist = self._collect_team_state(
            away_team, False, target_ns, ref_date, target_season
        )
        past_h2h = self.get_h2h_slice(home_team, away_team, target_ns, window=_H2H_WINDOW)

        elo_date = _to_naive_utc_timestamp(match_date) if match_date is not None else ref_date
        home_elo = elo_lookup.get_elo(home_team, elo_date)
        away_elo = elo_lookup.get_elo(away_team, elo_date)

        if odds is not None:
            odds_h, odds_d, odds_a = float(odds[0]), float(odds[1]), float(odds[2])
        else:
            odds_h, odds_d, odds_a = np.nan, np.nan, np.nan

        raw_row = _assemble_raw_match_row(
            h_team=home_team,
            a_team=away_team,
            home_elo=float(home_elo) if home_elo is not None else np.nan,
            away_elo=float(away_elo) if away_elo is not None else np.nan,
            odds_h=odds_h,
            odds_d=odds_d,
            odds_a=odds_a,
            h_roll=h_roll,
            a_roll=a_roll,
            h_season=h_season,
            a_season=a_season,
            past_h2h=past_h2h,
        )

        context = {
            "target_season": target_season,
            "ref_date": str(ref_date.date()),
            "home_history_matches": h_n_hist,
            "away_history_matches": a_n_hist,
            "h2h_matches_count": len(past_h2h),
        }
        return raw_row, context

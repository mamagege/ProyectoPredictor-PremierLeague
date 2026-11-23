"""
prediction_service.py
Módulo reutilizable y blindado para la predicción probabilística de partidos de la EPL
mediante la Red Neuronal Profunda calibrada y el motor único de características pre-partido.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras

from src.calibration import apply_temperature_scaling, predict_with_weights
from src.config import (
    CALIBRATION_PATH,
    ELO_RATINGS_CSV,
    FEATURE_NAMES_PATH,
    MATCHES_CSV,
    MODEL_PATH,
    PREMIER_LEAGUE_CSV,
    PREPROCESSOR_PATH,
    ROOT_DIR,
    SCALER_PATH,
    TEAM_ALIASES as _CONFIG_TEAM_ALIASES,
    TRAINING_SUMMARY_PATH,
    normalize_team_name,
)
from src.data import load_unified_matches
from src.features import CausalPreprocessor, MatchHistoryIndex

logger = logging.getLogger(__name__)

_MAX_REASONABLE_ODDS = 1000.0

_FACTOR_DESCRIPTIONS: dict[str, str] = {
    "ProbMarket_Home": "Probabilidad implícita de mercado (Local)",
    "ProbMarket_Away": "Probabilidad implícita de mercado (Visitante)",
    "ProbMarket_Draw": "Probabilidad implícita de mercado (Empate)",
    "MarketFavMargin": "Margen de favoritismo del mercado",
    "MarketEntropy": "Incertidumbre del mercado (Entropía)",
    "DiffElo": "Diferencial Elo (Local - Visitante)",
    "EloProb_Home": "Probabilidad teórica por Elo (Local)",
    "HomeElo": "Rating Elo del equipo local",
    "AwayElo": "Rating Elo del equipo visitante",
    "DiffRollingPts5": "Diferencial de puntos últimos 5 partidos",
    "DiffRollingPts3": "Diferencial de puntos últimos 3 partidos",
    "DiffRollingGF5": "Diferencial de goles a favor últimos 5 partidos",
    "DiffRollingGA5": "Diferencial de goles en contra últimos 5 partidos",
    "DiffRollingSoT5": "Diferencial de tiros al arco últimos 5 partidos",
    "DiffVenuePts5": "Diferencial de rendimiento reciente por sede",
    "DiffVenueGD5": "Diferencial de gol reciente por sede",
    "DiffSeasonPts": "Diferencial de puntos en la temporada actual",
    "DiffSeasonGD": "Diferencial de goles en la temporada actual",
    "DiffRestDays": "Diferencial de días de descanso",
    "H2H_HomeWins": "Historial directo reciente favorable al local",
    "H2H_AwayWins": "Historial directo reciente favorable al visitante",
}


def _resolve_path(p: str | Path) -> Path:
    path = Path(p)
    if path.exists():
        return path
    cand = ROOT_DIR / path
    if cand.exists():
        return cand
    return path


class EPLPredictor:
    """Servicio de inferencia pre-partido con paridad exacta respecto al entrenamiento."""

    TEAM_ALIASES = _CONFIG_TEAM_ALIASES

    def __init__(
        self,
        model_path: str | Path = MODEL_PATH,
        scaler_path: str | Path = SCALER_PATH,
        feature_names_path: str | Path = FEATURE_NAMES_PATH,
        epl_csv: Optional[str | Path] = None,
        matches_csv: str | Path = MATCHES_CSV,
        prem_csv: str | Path = PREMIER_LEAGUE_CSV,
        elo_csv: str | Path = ELO_RATINGS_CSV,
        preprocessor_path: str | Path = PREPROCESSOR_PATH,
        calibration_path: str | Path = CALIBRATION_PATH,
        summary_path: str | Path = TRAINING_SUMMARY_PATH,
    ) -> None:
        del epl_csv  # Conservado solo por retrocompatibilidad de firma con Hito 2.

        self.model_path = _resolve_path(model_path)
        self.scaler_path = _resolve_path(scaler_path)
        self.feature_names_path = _resolve_path(feature_names_path)
        self.preprocessor_path = _resolve_path(preprocessor_path)
        self.calibration_path = _resolve_path(calibration_path)
        self.summary_path = _resolve_path(summary_path)

        self.model = keras.models.load_model(self.model_path)

        with open(self.feature_names_path, "r", encoding="utf-8") as f:
            self.feature_names: list[str] = json.load(f)

        model_input_dim = self.model.input_shape[-1]
        if model_input_dim != len(self.feature_names):
            raise RuntimeError(
                f"Incompatibilidad de artefactos: el modelo espera {model_input_dim} features, "
                f"pero feature_names.json tiene {len(self.feature_names)}."
            )

        if self.preprocessor_path.exists():
            self.preprocessor: CausalPreprocessor = joblib.load(self.preprocessor_path)
            self.scaler = self.preprocessor.scaler_
        else:
            self.scaler = joblib.load(self.scaler_path)
            self.preprocessor = CausalPreprocessor(
                feature_names=self.feature_names,
                scaler_=self.scaler,
                is_fitted_=True,
            )

        self.temperature: float = 1.0
        self.bayesian_weights: list[float] = [1.0, 1.0, 1.0]
        self.model_version: str = "3.0.0"
        self.selected_architecture: str = getattr(self.model, "name", "Deep_MLP")
        if self.calibration_path.exists():
            with open(self.calibration_path, "r", encoding="utf-8") as f:
                cal_cfg = json.load(f)
            self.temperature = float(cal_cfg.get("temperature", 1.0))
            self.bayesian_weights = [float(x) for x in cal_cfg.get("bayesian_weights", [1.0, 1.0, 1.0])]
            self.model_version = str(cal_cfg.get("model_version", self.model_version))
            self.selected_architecture = str(cal_cfg.get("selected_architecture", self.selected_architecture))

        self.training_summary: Optional[dict[str, Any]] = None
        if self.summary_path.exists():
            with open(self.summary_path, "r", encoding="utf-8") as f:
                self.training_summary = json.load(f)

        self.df_history, self.elo_lookup = load_unified_matches(
            premier_league_csv=_resolve_path(prem_csv),
            matches_csv=_resolve_path(matches_csv),
            elo_csv=_resolve_path(elo_csv),
            include_prospective=True,
        )
        self.history_index = MatchHistoryIndex.from_dataframe(self.df_history)
        self.known_teams: set[str] = set(self.df_history["HomeTeam"].unique()).union(
            set(self.df_history["AwayTeam"].unique())
        )
        self.first_history_date: pd.Timestamp = pd.Timestamp(self.df_history["MatchDate"].min())
        self.last_history_date: pd.Timestamp = pd.Timestamp(self.df_history["MatchDate"].max())
        logger.info(
            "EPLPredictor cargado: modelo=%s, features=%d, partidos=%d",
            self.selected_architecture,
            len(self.feature_names),
            len(self.df_history),
        )

    def normalize_team(self, name: str) -> str:
        return normalize_team_name(name, known_teams=self.known_teams)

    @staticmethod
    def _parse_date(match_date: Any) -> pd.Timestamp:
        if not isinstance(match_date, (str, pd.Timestamp)) and not hasattr(match_date, "year"):
            raise ValueError(f"Formato de fecha inválido: '{match_date}'. Usa formato ISO YYYY-MM-DD.")
        if isinstance(match_date, str) and not match_date.strip():
            raise ValueError("Formato de fecha inválido: cadena vacía. Usa formato ISO YYYY-MM-DD.")
        try:
            ts = pd.to_datetime(match_date, errors="raise")
            if pd.isna(ts):
                raise ValueError("Fecha vacía.")
            ts_obj = pd.Timestamp(ts)
            if ts_obj.tzinfo is not None:
                ts_obj = ts_obj.tz_convert("UTC").tz_localize(None)
            return ts_obj.normalize()
        except Exception as exc:
            raise ValueError(
                f"Formato de fecha inválido: '{match_date}'. Usa formato ISO YYYY-MM-DD."
            ) from exc

    @staticmethod
    def _validate_odds(odds: Any) -> Optional[tuple[float, float, float]]:
        if odds is None:
            return None
        if not isinstance(odds, (list, tuple, np.ndarray)) or len(odds) != 3:
            raise ValueError("Las cuotas deben tener exactamente 3 valores decimales: [Odd_H, Odd_D, Odd_A].")
        vals: list[float] = []
        for val in odds:
            if isinstance(val, bool):
                raise ValueError(f"Cuota no numérica: '{val}'.")
            try:
                fval = float(val)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Cuota no numérica: '{val}'.") from exc
            if not np.isfinite(fval) or fval <= 1.0 or fval > _MAX_REASONABLE_ODDS:
                raise ValueError(
                    f"Cada cuota decimal debe ser finita en (1.0, {_MAX_REASONABLE_ODDS:.0f}] (recibido: {fval})."
                )
            vals.append(fval)
        return vals[0], vals[1], vals[2]

    def _predict_proba_matrix(self, x_scaled: np.ndarray) -> np.ndarray:
        """Ejecuta inferencia directa sin el overhead por llamada de Keras .predict()."""
        tensor_x = tf.convert_to_tensor(x_scaled, dtype=tf.float32)
        return self.model(tensor_x, training=False).numpy().astype(np.float64)

    def get_latest_team_stats(
        self,
        team_name: str,
        target_date: str | pd.Timestamp | None = None,
        k: int = 5,
    ) -> Optional[dict[str, Any]]:
        """Método retrocompatible Hito 2: estado histórico estricto de un equipo antes de target_date."""
        canonical = self.normalize_team(team_name)
        if canonical not in self.known_teams:
            return None
        parsed_date = self._parse_date(target_date) if target_date is not None else None
        ref_date, target_ns, target_season = self.history_index.resolve_target_context(parsed_date)
        rolling, season_s, n_hist = self.history_index._collect_team_state(
            canonical, True, target_ns, ref_date, target_season, k=k
        )
        if n_hist == 0:
            return None
        elo_val = self.elo_lookup.get_elo(canonical, parsed_date if parsed_date is not None else ref_date)
        elo_num = float(elo_val) if elo_val is not None else self.preprocessor.train_elo_median_
        return {
            "elo": elo_num,
            "form5": round(rolling["pts5"] * min(5, n_hist), 1),
            "form3": round(rolling["pts3"] * min(3, n_hist), 1),
            "rolling_pts3": rolling["pts3"],
            "rolling_pts5": rolling["pts5"],
            "rolling_gf5": rolling["gf5"],
            "rolling_ga5": rolling["ga5"],
            "rolling_shots5": rolling["shots5"],
            "rolling_sot5": rolling["sot5"],
            "rest_days": rolling["rest"],
            "season_pts": season_s["pts"],
            "season_gd": season_s["gf"] - season_s["ga"],
        }

    def get_h2h_stats(
        self,
        home_team: str,
        away_team: str,
        target_date: str | pd.Timestamp | None = None,
    ) -> tuple[float, float, float]:
        """Método retrocompatible Hito 2: proporción histórica de resultados directos H2H."""
        home_norm = self.normalize_team(home_team)
        away_norm = self.normalize_team(away_team)
        parsed_date = self._parse_date(target_date) if target_date is not None else None
        _, target_ns, _ = self.history_index.resolve_target_context(parsed_date)
        past = self.history_index.get_h2h_slice(home_norm, away_norm, target_ns, window=None)
        n = len(past)
        if n == 0:
            return 0.45, 0.25, 0.30
        hw = sum(1 for w in past if w == home_norm)
        d = sum(1 for w in past if w == "D")
        aw = sum(1 for w in past if w == away_norm)
        return hw / n, d / n, aw / n

    def get_team_snapshot(
        self,
        team_name: str,
        target_date: str | pd.Timestamp | None = None,
        is_home: bool = True,
    ) -> dict[str, Any]:
        """Obtiene el resumen estadístico pre-partido verificado de un equipo."""
        canonical = self.normalize_team(team_name)
        if canonical not in self.known_teams:
            raise ValueError(f"Equipo no reconocido: '{team_name}'.")

        parsed_date = self._parse_date(target_date) if target_date is not None else None
        if parsed_date is not None and parsed_date <= self.first_history_date:
            raise ValueError(f"Historial insuficiente para '{canonical}' antes de {parsed_date.date()}.")

        dummy_opp = next(t for t in sorted(self.known_teams) if t != canonical)
        if is_home:
            raw_row, ctx = self.history_index.compute_single_match_features(
                self.elo_lookup, canonical, dummy_opp, parsed_date, odds=None
            )
            suffix = "Home"
            elo_val = raw_row["HomeElo"]
        else:
            raw_row, ctx = self.history_index.compute_single_match_features(
                self.elo_lookup, dummy_opp, canonical, parsed_date, odds=None
            )
            suffix = "Away"
            elo_val = raw_row["AwayElo"]

        matches_count = ctx["home_history_matches"] if is_home else ctx["away_history_matches"]
        if matches_count == 0 and pd.isna(elo_val):
            ref_str = str(parsed_date.date()) if parsed_date is not None else ctx["ref_date"]
            raise ValueError(f"Historial insuficiente para '{canonical}' antes de {ref_str}.")

        return {
            "team": canonical,
            "target_season": ctx["target_season"],
            "reference_date": ctx["ref_date"],
            "matches_in_history": matches_count,
            "elo": round(float(elo_val), 2) if pd.notna(elo_val) else None,
            "rolling_pts3": round(float(raw_row[f"RollingPts3_{suffix}"]), 3),
            "rolling_pts5": round(float(raw_row[f"RollingPts5_{suffix}"]), 3),
            "rolling_gf5": round(float(raw_row[f"RollingGF5_{suffix}"]), 3),
            "rolling_ga5": round(float(raw_row[f"RollingGA5_{suffix}"]), 3),
            "rolling_shots5": round(float(raw_row[f"RollingShots5_{suffix}"]), 2),
            "rolling_sot5": round(float(raw_row[f"RollingSoT5_{suffix}"]), 2),
            "venue_pts5": round(float(raw_row[f"VenuePts5_{suffix}"]), 3),
            "venue_gd5": round(float(raw_row[f"VenueGD5_{suffix}"]), 3),
            "rest_days": round(float(raw_row[f"RestDays_{suffix}"]), 1),
            "season_pts": int(raw_row[f"SeasonPts_{suffix}"]),
            "season_gd": int(raw_row[f"SeasonGD_{suffix}"]),
        }

    def _build_top_factors(
        self,
        x_scaled_row: np.ndarray,
        fin_dict: dict[str, float],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        factors: list[dict[str, Any]] = []
        for idx, name in enumerate(self.feature_names):
            if name not in _FACTOR_DESCRIPTIONS:
                continue
            z_val = float(x_scaled_row[idx])
            raw_val = float(fin_dict[name])
            if name == "ProbMarket_Draw":
                direction = (
                    "Mayor probabilidad de empate"
                    if z_val > 0.25
                    else ("Baja probabilidad de empate" if z_val < -0.25 else "Equilibrado")
                )
            elif name == "MarketEntropy":
                direction = (
                    "Partido incierto/parejo"
                    if z_val > 0.25
                    else ("Favorito claro" if z_val < -0.25 else "Equilibrado")
                )
            elif name == "MarketFavMargin":
                direction = (
                    "Favorito claro"
                    if z_val > 0.25
                    else ("Partido parejo" if z_val < -0.25 else "Equilibrado")
                )
            elif "Away" in name or "RollingGA" in name:
                direction = (
                    "Favorece al Visitante"
                    if z_val > 0.25
                    else ("Favorece al Local" if z_val < -0.25 else "Equilibrado")
                )
            else:
                direction = (
                    "Favorece al Local"
                    if z_val > 0.25
                    else ("Favorece al Visitante" if z_val < -0.25 else "Equilibrado")
                )

            factors.append(
                {
                    "feature": name,
                    "description": _FACTOR_DESCRIPTIONS[name],
                    "value": round(raw_val, 4),
                    "z_score": round(z_val, 3),
                    "impact_direction": direction,
                }
            )
        factors.sort(key=lambda item: abs(item["z_score"]), reverse=True)
        return factors[:top_k]

    def _prepare_match_inputs(
        self,
        home_team: str,
        away_team: str,
        match_date: str | pd.Timestamp | None = None,
        odds: Optional[list[float] | tuple[float, float, float]] = None,
        decision_mode: str = "argmax",
    ) -> dict[str, Any]:
        if not isinstance(home_team, str) or not home_team.strip():
            return {"status": "error", "error_code": "invalid_input", "message": "Debe indicar un equipo local válido."}
        if not isinstance(away_team, str) or not away_team.strip():
            return {"status": "error", "error_code": "invalid_input", "message": "Debe indicar un equipo visitante válido."}

        home_norm = self.normalize_team(home_team)
        away_norm = self.normalize_team(away_team)

        if home_norm not in self.known_teams:
            return {
                "status": "error",
                "error_code": "unknown_team",
                "message": f"Equipo local no reconocido: '{home_team}'. No se pueden generar estadísticas válidas sin inventar datos.",
                "known_teams_sample": sorted(self.known_teams)[:12],
            }
        if away_norm not in self.known_teams:
            return {
                "status": "error",
                "error_code": "unknown_team",
                "message": f"Equipo visitante no reconocido: '{away_team}'. No se pueden generar estadísticas válidas sin inventar datos.",
                "known_teams_sample": sorted(self.known_teams)[:12],
            }
        if home_norm == away_norm:
            return {
                "status": "error",
                "error_code": "same_team",
                "message": "Un equipo no puede jugar contra sí mismo.",
            }

        parsed_date: Optional[pd.Timestamp] = None
        if match_date is not None:
            try:
                parsed_date = self._parse_date(match_date)
            except ValueError as exc:
                return {"status": "error", "error_code": "invalid_date", "message": str(exc)}

        try:
            validated_odds = self._validate_odds(odds)
        except ValueError as exc:
            return {"status": "error", "error_code": "invalid_odds", "message": str(exc)}

        if decision_mode not in ("argmax", "bayesian"):
            return {
                "status": "error",
                "error_code": "invalid_decision_mode",
                "message": "decision_mode debe ser 'argmax' o 'bayesian'.",
            }

        if parsed_date is not None and parsed_date <= self.first_history_date:
            return {
                "status": "error",
                "error_code": "insufficient_history",
                "message": "Historial insuficiente para calcular variables pre-partido antes de la fecha especificada.",
            }

        raw_row, ctx = self.history_index.compute_single_match_features(
            elo_lookup=self.elo_lookup,
            home_team=home_norm,
            away_team=away_norm,
            match_date=parsed_date,
            odds=validated_odds,
        )

        # Solo rechazar por historial insuficiente si falta tanto historial EPL como rating Elo causal
        if (ctx["home_history_matches"] == 0 and pd.isna(raw_row["HomeElo"])) or (
            ctx["away_history_matches"] == 0 and pd.isna(raw_row["AwayElo"])
        ):
            return {
                "status": "error",
                "error_code": "insufficient_history",
                "message": "Historial insuficiente para calcular variables pre-partido antes de la fecha especificada.",
            }

        warnings_list: list[str] = []
        if ctx["home_history_matches"] == 0:
            warnings_list.append(
                f"El equipo '{home_norm}' aún no registra partidos previos en EPL antes de {ctx['ref_date']}; "
                "se utilizan promedios base de debutante junto con su rating Elo."
            )
        if ctx["away_history_matches"] == 0:
            warnings_list.append(
                f"El equipo '{away_norm}' aún no registra partidos previos en EPL antes de {ctx['ref_date']}; "
                "se utilizan promedios base de debutante junto con su rating Elo."
            )
        if parsed_date is not None and parsed_date > self.last_history_date:
            warnings_list.append(
                f"La fecha solicitada ({parsed_date.date()}) es posterior al último registro histórico "
                f"({self.last_history_date.date()}); se utiliza el estado más reciente disponible."
            )

        return {
            "status": "prepared",
            "home_norm": home_norm,
            "away_norm": away_norm,
            "parsed_date": parsed_date,
            "validated_odds": validated_odds,
            "decision_mode": decision_mode,
            "raw_row": raw_row,
            "ctx": ctx,
            "warnings": warnings_list,
        }

    def _format_prediction_response(
        self,
        prep: dict[str, Any],
        x_scaled_row: np.ndarray,
        fin_dict: dict[str, float],
        raw_probs: np.ndarray,
    ) -> dict[str, Any]:
        cal_probs = apply_temperature_scaling(raw_probs, self.temperature)[0]

        p_home = float(cal_probs[0])
        p_draw = float(cal_probs[1])
        p_away = float(cal_probs[2])

        p_home_pct = round(p_home * 100.0, 1)
        p_draw_pct = round(p_draw * 100.0, 1)
        p_away_pct = round(p_away * 100.0, 1)
        diff_round = round(100.0 - (p_home_pct + p_draw_pct + p_away_pct), 1)
        p_home_pct = round(p_home_pct + diff_round, 1)

        home_norm = prep["home_norm"]
        away_norm = prep["away_norm"]
        parsed_date = prep["parsed_date"]
        ctx = prep["ctx"]

        class_names = [
            f"Victoria de {home_norm} (Local)",
            "Empate",
            f"Victoria de {away_norm} (Visitante)",
        ]
        argmax_idx = int(np.argmax([p_home, p_draw, p_away]))
        bayesian_idx = int(predict_with_weights(cal_probs, self.bayesian_weights)[0])
        chosen_idx = bayesian_idx if prep["decision_mode"] == "bayesian" else argmax_idx

        return {
            "status": "success",
            "home_team": home_norm,
            "away_team": away_norm,
            "match_date": str(parsed_date.date()) if parsed_date is not None else f"Próximo ({ctx['ref_date']})",
            "season": ctx["target_season"],
            "odds_source": "bookmaker" if prep["validated_odds"] is not None else "elo_fallback",
            "decision_mode": prep["decision_mode"],
            "model_version": self.model_version,
            "model_architecture": self.selected_architecture,
            "probabilities": {
                "Victoria (Local)": f"{p_home_pct:.1f} %",
                "Empate": f"{p_draw_pct:.1f} %",
                "Derrota (Visitante)": f"{p_away_pct:.1f} %",
            },
            "numeric_probabilities": {
                "P_Home": round(p_home, 6),
                "P_Draw": round(p_draw, 6),
                "P_Away": round(p_away, 6),
            },
            "raw_model_probabilities": {
                "P_Home": round(float(raw_probs[0]), 6),
                "P_Draw": round(float(raw_probs[1]), 6),
                "P_Away": round(float(raw_probs[2]), 6),
            },
            "pronostico_mas_probable": class_names[chosen_idx],
            "pronostico_argmax": class_names[argmax_idx],
            "pronostico_bayesiano": class_names[bayesian_idx],
            "suma_probabilidades": f"{p_home_pct + p_draw_pct + p_away_pct:.1f} %",
            "contexto_prepartido": {
                "Elo_Local": round(fin_dict["HomeElo"], 1),
                "Elo_Visitante": round(fin_dict["AwayElo"], 1),
                "Diferencial_Elo": round(fin_dict["DiffElo"], 1),
                "RollingPts5_Local": round(fin_dict["RollingPts5_Home"], 2),
                "RollingPts5_Visitante": round(fin_dict["RollingPts5_Away"], 2),
                "Forma5_Local": round(fin_dict["RollingPts5_Home"] * 5.0, 1),
                "Forma5_Visitante": round(fin_dict["RollingPts5_Away"] * 5.0, 1),
                "SeasonPts_Local": int(round(fin_dict["SeasonPts_Home"])),
                "SeasonPts_Visitante": int(round(fin_dict["SeasonPts_Away"])),
                "SeasonGD_Local": int(round(fin_dict["SeasonGD_Home"])),
                "SeasonGD_Visitante": int(round(fin_dict["SeasonGD_Away"])),
                "Descanso_Local_Dias": round(fin_dict["RestDays_Home"], 1),
                "Descanso_Visitante_Dias": round(fin_dict["RestDays_Away"], 1),
                "ProbMercado_Base": {
                    "Local": round(fin_dict["ProbMarket_Home"], 4),
                    "Empate": round(fin_dict["ProbMarket_Draw"], 4),
                    "Visitante": round(fin_dict["ProbMarket_Away"], 4),
                },
            },
            "top_factors": self._build_top_factors(x_scaled_row, fin_dict, top_k=5),
            "warnings": prep["warnings"],
        }

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        match_date: str | pd.Timestamp | None = None,
        odds: Optional[list[float] | tuple[float, float, float]] = None,
        decision_mode: str = "argmax",
    ) -> dict[str, Any]:
        """Predice las probabilidades calibradas pre-partido de un encuentro de la EPL."""
        prep = self._prepare_match_inputs(home_team, away_team, match_date, odds, decision_mode)
        if prep["status"] != "prepared":
            return prep

        x_scaled, fin_dict = self.preprocessor.transform_single(
            prep["raw_row"], selected_features=self.feature_names
        )
        raw_probs = self._predict_proba_matrix(x_scaled)[0]
        return self._format_prediction_response(prep, x_scaled[0], fin_dict, raw_probs)

    def predict_matches_batch(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Ejecuta inferencia vectorizada en lote; reporta el índice exacto ante errores."""
        if not items:
            return {"status": "error", "error_code": "empty_batch", "message": "El lote no puede estar vacío."}

        prepared: list[dict[str, Any]] = []
        raw_rows: list[dict[str, Any]] = []
        for idx, item in enumerate(items):
            prep = self._prepare_match_inputs(
                home_team=item.get("home_team"),
                away_team=item.get("away_team"),
                match_date=item.get("match_date"),
                odds=item.get("odds"),
                decision_mode=item.get("decision_mode", "argmax"),
            )
            if prep["status"] != "prepared":
                err = dict(prep)
                err["match_index"] = idx
                return err
            prepared.append(prep)
            raw_rows.append(prep["raw_row"])

        df_raw_batch = pd.DataFrame(raw_rows)
        df_fin_batch = self.preprocessor.finalize_features_df(df_raw_batch)
        x_batch_scaled = self.preprocessor.transform_df(df_raw_batch, selected_features=self.feature_names)
        probs_batch = self._predict_proba_matrix(x_batch_scaled)

        predictions: list[dict[str, Any]] = []
        for idx, prep in enumerate(prepared):
            fin_dict = {name: float(df_fin_batch.iloc[idx][name]) for name in self.feature_names}
            predictions.append(
                self._format_prediction_response(
                    prep=prep,
                    x_scaled_row=x_batch_scaled[idx],
                    fin_dict=fin_dict,
                    raw_probs=probs_batch[idx],
                )
            )
        return {"status": "success", "count": len(predictions), "predictions": predictions}


_PREDICTOR_SINGLETON: Optional[EPLPredictor] = None
_PREDICTOR_LOCK = threading.Lock()


def get_predictor() -> EPLPredictor:
    """Retorna la instancia en caché thread-safe de EPLPredictor."""
    global _PREDICTOR_SINGLETON
    if _PREDICTOR_SINGLETON is None:
        with _PREDICTOR_LOCK:
            if _PREDICTOR_SINGLETON is None:
                _PREDICTOR_SINGLETON = EPLPredictor()
    return _PREDICTOR_SINGLETON


def reset_predictor_cache() -> None:
    """Limpia la instancia en caché de forma segura entre hilos."""
    global _PREDICTOR_SINGLETON
    with _PREDICTOR_LOCK:
        _PREDICTOR_SINGLETON = None


def predecir_partido(
    equipo_local: str,
    equipo_visitante: str,
    fecha_partido: str | pd.Timestamp | None = None,
    cuotas: Optional[list[float] | tuple[float, float, float]] = None,
    modo_decision: str = "argmax",
) -> dict[str, Any]:
    """Función directa retrocompatible con el Hito 2 respaldada por caché singleton."""
    predictor = get_predictor()
    return predictor.predict_match(
        home_team=equipo_local,
        away_team=equipo_visitante,
        match_date=fecha_partido,
        odds=cuotas,
        decision_mode=modo_decision,
    )


if __name__ == "__main__":
    print("Probando servicio predictivo blindado...")
    cases = [
        ("Arsenal vs Chelsea (2024-04-23)", ("Arsenal", "Chelsea", "2024-04-23", [1.55, 4.50, 5.50])),
        ("Man City vs Liverpool (2023-11-25)", ("Man City", "Liverpool", "2023-11-25", [1.75, 4.20, 4.33])),
        ("Jornada 1 2024/25: Arsenal vs Wolves (2024-08-17)", ("arsenal", "wolves", "2024-08-17", None)),
        ("Debutante EPL: Brentford vs Arsenal (2021-08-13)", ("Brentford", "Arsenal", "2021-08-13", None)),
        ("Alias: Nottingham Forest vs Manchester City (2024-04-28)", ("Nottingham Forest", "Manchester City", "2024-04-28", None)),
        ("Equipo desconocido: Real Madrid vs Barcelona", ("Real Madrid", "Barcelona", None, None)),
    ]
    for label, args in cases:
        print(f"\n--- {label} ---")
        res = predecir_partido(*args)
        print(json.dumps(res, indent=2, ensure_ascii=False))

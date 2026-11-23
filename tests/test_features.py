"""Pruebas de paridad entrenamiento==inferencia, índice rápido, reseteo de temporada y cero fuga."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.config import TARGET_MAP, TRAIN_SEASONS
from src.data import load_unified_matches
from src.features import FEATURE_NAMES, CausalPreprocessor, FeatureStateEngine, MatchHistoryIndex


class TestFeatureParityAndCausality(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.df_unified, cls.elo_lookup = load_unified_matches(include_prospective=True)
        cls.history_index = MatchHistoryIndex.from_dataframe(cls.df_unified)
        cls.df_raw = FeatureStateEngine.compute_batch_features(cls.df_unified)
        train_mask = cls.df_raw["Season"].isin(TRAIN_SEASONS).to_numpy()
        y_train = cls.df_raw.loc[train_mask, "FullTimeResult"].map(TARGET_MAP).to_numpy(dtype=int)
        cls.preprocessor = CausalPreprocessor(feature_names=list(FEATURE_NAMES)).fit(
            cls.df_raw.loc[train_mask], y_train
        )
        cls.X_batch = cls.preprocessor.transform_df(cls.df_raw)

    def test_exact_batch_vs_single_and_index_inference_parity(self) -> None:
        """Verifica paridad matemática exacta (atol=1e-9) entre batch, fallback y MatchHistoryIndex."""
        probe_matches = [
            ("Arsenal", "Chelsea", "2024-04-23"),
            ("Man City", "Liverpool", "2023-11-25"),
            ("Hull", "Everton", "2016-12-30"),
            ("Arsenal", "Wolves", "2024-08-17"),  # Jornada 1 de temporada nueva
            ("Nott'm Forest", "Tottenham", "2024-12-26"),
            ("Nott'm Forest", "Man United", "2025-11-01"),
            ("Liverpool", "Chelsea", "2020-07-22"),  # Partido COVID en julio (2019/20)
            ("Brentford", "Arsenal", "2021-08-13"),  # Debutante EPL
            ("Aston Villa", "Newcastle", "2025-08-16"),  # Temporada prospectiva 2025/26
        ]
        for home, away, dt_str in probe_matches:
            dt = pd.Timestamp(dt_str)
            match_idx = self.df_raw.index[
                (self.df_raw["HomeTeam"] == home)
                & (self.df_raw["AwayTeam"] == away)
                & (self.df_raw["MatchDate"] == dt)
            ]
            self.assertEqual(len(match_idx), 1, msg=f"No se encontró partido único: {home} vs {away} ({dt_str})")
            idx = int(match_idx[0])

            row_meta = self.df_raw.iloc[idx]
            odds = (
                [float(row_meta["Odds_H"]), float(row_meta["Odds_D"]), float(row_meta["Odds_A"])]
                if pd.notna(row_meta["Odds_H"])
                else None
            )
            raw_idx, _ = self.history_index.compute_single_match_features(
                elo_lookup=self.elo_lookup,
                home_team=home,
                away_team=away,
                match_date=dt,
                odds=odds,
            )
            x_idx, _ = self.preprocessor.transform_single(raw_idx)
            self.assertTrue(
                np.allclose(self.X_batch[idx], x_idx[0], atol=1e-9),
                msg=f"Paridad rota (MatchHistoryIndex) en {home} vs {away} ({dt_str})",
            )

            raw_single, _ = FeatureStateEngine.compute_single_match_features(
                df_history=self.df_unified,
                elo_lookup=self.elo_lookup,
                home_team=home,
                away_team=away,
                match_date=dt,
                odds=odds,
            )
            x_single, _ = self.preprocessor.transform_single(raw_single)
            self.assertTrue(
                np.allclose(self.X_batch[idx], x_single[0], atol=1e-9),
                msg=f"Paridad rota (FeatureStateEngine) en {home} vs {away} ({dt_str})",
            )

    def test_season_stats_reset_on_matchday_one_and_no_future_leak(self) -> None:
        """Garantiza reseteo en Jornada 1 y que filas futuras no alteran resolución causal de temporada."""
        truncated = self.df_unified[self.df_unified["MatchDate"] < pd.Timestamp("2020-07-22")].copy()
        idx_trunc = MatchHistoryIndex.from_dataframe(truncated)

        raw_full, ctx_full = self.history_index.compute_single_match_features(
            self.elo_lookup, "Liverpool", "Chelsea", "2020-07-22"
        )
        raw_trunc, ctx_trunc = idx_trunc.compute_single_match_features(
            self.elo_lookup, "Liverpool", "Chelsea", "2020-07-22"
        )
        self.assertEqual(ctx_full["target_season"], "2019/20")
        self.assertEqual(ctx_trunc["target_season"], "2019/20")
        self.assertEqual(raw_full["SeasonPts_Home"], raw_trunc["SeasonPts_Home"])

        raw_j1, ctx_j1 = self.history_index.compute_single_match_features(
            elo_lookup=self.elo_lookup,
            home_team="Arsenal",
            away_team="Wolves",
            match_date="2024-08-17T14:00:00Z",
            odds=None,
        )
        self.assertEqual(ctx_j1["target_season"], "2024/25")
        self.assertEqual(raw_j1["SeasonPts_Home"], 0.0)
        self.assertEqual(raw_j1["SeasonGD_Home"], 0.0)
        self.assertEqual(raw_j1["SeasonPts_Away"], 0.0)
        self.assertEqual(raw_j1["SeasonGD_Away"], 0.0)

    def test_zero_leakage_in_preprocessor(self) -> None:
        """Modificar registros futuros de Test no debe alterar ni un bit el preprocesador."""
        train_mask = self.df_raw["Season"].isin(TRAIN_SEASONS).to_numpy()
        y_train = self.df_raw.loc[train_mask, "FullTimeResult"].map(TARGET_MAP).to_numpy(dtype=int)

        df_corrupted = self.df_raw.copy()
        df_corrupted.loc[~train_mask, "HomeElo"] = 9999.0
        df_corrupted.loc[~train_mask, "Odds_H"] = 1.05

        prep_alt = CausalPreprocessor(feature_names=list(FEATURE_NAMES)).fit(
            df_corrupted.loc[train_mask], y_train
        )
        self.assertTrue(np.allclose(self.preprocessor.scaler_.mean_, prep_alt.scaler_.mean_, atol=1e-12))
        self.assertTrue(np.allclose(self.preprocessor.scaler_.scale_, prep_alt.scaler_.scale_, atol=1e-12))
        self.assertTrue(np.allclose(self.preprocessor.train_priors_, prep_alt.train_priors_, atol=1e-12))
        self.assertEqual(self.preprocessor.scaler_.n_samples_seen_, int(train_mask.sum()))


if __name__ == "__main__":
    unittest.main()

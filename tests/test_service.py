"""Pruebas de integración, retrocompatibilidad, bordes y rendimiento para prediction_service.py."""

from __future__ import annotations

import concurrent.futures
import time
import unittest

import numpy as np

from prediction_service import EPLPredictor, get_predictor, predecir_partido


class TestPredictionService(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.predictor: EPLPredictor = get_predictor()

    def test_singleton_caching_fast_and_thread_safe(self) -> None:
        _ = predecir_partido("Arsenal", "Chelsea", "2024-04-23", cuotas=[1.55, 4.50, 5.50])
        t0 = time.perf_counter()
        res = predecir_partido("Man City", "Liverpool", "2023-11-25", cuotas=[1.75, 4.20, 4.33])
        elapsed = time.perf_counter() - t0
        self.assertEqual(res["status"], "success")
        self.assertLess(elapsed, 0.25)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            instances = list(pool.map(lambda _: get_predictor(), range(8)))
        self.assertTrue(all(inst is instances[0] for inst in instances))

    def test_direct_inference_matches_keras_predict(self) -> None:
        x = np.zeros((3, len(self.predictor.feature_names)), dtype=np.float64)
        p_fast = self.predictor._predict_proba_matrix(x)
        p_keras = self.predictor.model.predict(x, verbose=0)
        self.assertTrue(np.allclose(p_fast, p_keras, atol=1e-6))

    def test_case_insensitive_and_aliases(self) -> None:
        res_lower = predecir_partido("arsenal", "chelsea", "2024-04-23", cuotas=[1.55, 4.50, 5.50])
        self.assertEqual(res_lower["status"], "success")
        self.assertEqual(res_lower["home_team"], "Arsenal")
        self.assertEqual(res_lower["away_team"], "Chelsea")

        res_alias = predecir_partido("Manchester City", "Nottingham Forest", "2024-04-28")
        self.assertEqual(res_alias["status"], "success")
        self.assertEqual(res_alias["home_team"], "Man City")
        self.assertEqual(res_alias["away_team"], "Nott'm Forest")
        self.assertEqual(res_alias["odds_source"], "elo_fallback")

    def test_tz_aware_iso_dates_supported(self) -> None:
        res = predecir_partido("Arsenal", "Chelsea", "2024-04-23T15:00:00Z", cuotas=[1.55, 4.50, 5.50])
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["match_date"], "2024-04-23")

    def test_newly_promoted_debut_team_supported_with_warning(self) -> None:
        res = predecir_partido("Brentford", "Arsenal", "2021-08-13")
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(len(res["warnings"]), 1)

    def test_hito2_backwards_compatibility_contract(self) -> None:
        self.assertIn("manchester city", EPLPredictor.TEAM_ALIASES)
        stats = self.predictor.get_latest_team_stats("Arsenal", "2024-04-23")
        self.assertIsNotNone(stats)
        for key in ("elo", "form5", "form3", "rolling_pts5", "rest_days", "season_pts", "season_gd"):
            self.assertIn(key, stats)
        h2h = self.predictor.get_h2h_stats("Arsenal", "Chelsea", "2024-04-23")
        self.assertEqual(len(h2h), 3)
        self.assertAlmostEqual(sum(h2h), 1.0, places=5)

        res = predecir_partido("Arsenal", "Chelsea", "2024-04-23")
        self.assertIn("Forma5_Local", res["contexto_prepartido"])
        self.assertIn("Forma5_Visitante", res["contexto_prepartido"])

    def test_season_reset_in_service_matchday_one(self) -> None:
        res = predecir_partido("Arsenal", "Wolves", "2024-08-17")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["season"], "2024/25")
        self.assertEqual(res["contexto_prepartido"]["SeasonPts_Local"], 0)
        self.assertEqual(res["contexto_prepartido"]["SeasonGD_Local"], 0)

    def test_probabilities_sum_to_100_percent(self) -> None:
        res = predecir_partido("Arsenal", "Chelsea", "2024-04-23", cuotas=[1.55, 4.50, 5.50])
        self.assertEqual(res["suma_probabilidades"], "100.0 %")
        num = res["numeric_probabilities"]
        self.assertAlmostEqual(num["P_Home"] + num["P_Draw"] + num["P_Away"], 1.0, places=4)

    def test_bayesian_decision_mode(self) -> None:
        res = predecir_partido("Arsenal", "Chelsea", "2024-04-23", modo_decision="bayesian")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["decision_mode"], "bayesian")
        self.assertIn("pronostico_argmax", res)
        self.assertIn("pronostico_bayesiano", res)

    def test_top_factors_semantic_direction(self) -> None:
        res = predecir_partido("Arsenal", "Wolves", "2024-08-17")
        for factor in res["top_factors"]:
            if factor["feature"] == "ProbMarket_Draw":
                self.assertIn("empate", factor["impact_direction"].lower())
            if factor["feature"] == "MarketEntropy":
                self.assertNotIn("Local", factor["impact_direction"])
                self.assertNotIn("Visitante", factor["impact_direction"])
            if factor["feature"] == "MarketFavMargin":
                self.assertNotIn("Local", factor["impact_direction"])
                self.assertNotIn("Visitante", factor["impact_direction"])

    def test_batch_prediction_vectorized_and_index_error(self) -> None:
        ok = self.predictor.predict_matches_batch(
            [
                {"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2024-04-23"},
                {"home_team": "Man City", "away_team": "Liverpool", "match_date": "2023-11-25"},
            ]
        )
        self.assertEqual(ok["status"], "success")
        self.assertEqual(ok["count"], 2)

        err = self.predictor.predict_matches_batch(
            [
                {"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2024-04-23"},
                {"home_team": "FakeFC", "away_team": "Chelsea"},
            ]
        )
        self.assertEqual(err["status"], "error")
        self.assertEqual(err["match_index"], 1)

    def test_error_handling_edges(self) -> None:
        res_unknown = predecir_partido("Real Madrid", "Barcelona")
        self.assertEqual(res_unknown["status"], "error")
        self.assertEqual(res_unknown["error_code"], "unknown_team")

        res_same = predecir_partido("Arsenal", "arsenal")
        self.assertEqual(res_same["status"], "error")
        self.assertEqual(res_same["error_code"], "same_team")

        for bad_date in ("fecha-invalida", "", "   ", "2024-02-30"):
            res_bad_date = predecir_partido("Arsenal", "Chelsea", bad_date)
            self.assertEqual(res_bad_date["status"], "error")
            self.assertEqual(res_bad_date["error_code"], "invalid_date")

        for bad_odds in ([0.95, 3.5, 4.0], [1e5, 3.5, 4.0], [True, 3.5, 4.0], [float("nan"), 3.5, 4.0]):
            res_bad_odds = predecir_partido("Arsenal", "Chelsea", "2024-04-23", cuotas=bad_odds)
            self.assertEqual(res_bad_odds["status"], "error")
            self.assertEqual(res_bad_odds["error_code"], "invalid_odds")

        res_no_hist = predecir_partido("Arsenal", "Chelsea", "2000-08-19")
        self.assertEqual(res_no_hist["status"], "error")
        self.assertEqual(res_no_hist["error_code"], "insufficient_history")

        res_bad_mode = predecir_partido("Arsenal", "Chelsea", "2024-04-23", modo_decision="invalido")
        self.assertEqual(res_bad_mode["status"], "error")
        self.assertEqual(res_bad_mode["error_code"], "invalid_decision_mode")

    def test_future_date_warning_non_breaking(self) -> None:
        res = predecir_partido("Arsenal", "Chelsea", "2027-01-15", cuotas=[2.10, 3.40, 3.50])
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(len(res["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()

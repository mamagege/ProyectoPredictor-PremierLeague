"""Pruebas de la API que consume la interfaz web (api/main.py) y de la política CORS de src/api.py."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from api.main import app
from src import api as backend_api

PCT_TOL = 0.11  # los porcentajes se redondean a un decimal


class TestFrontendAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._ctx = TestClient(app)
        cls.client = cls._ctx.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._ctx.__exit__(None, None, None)

    def test_health_uses_real_model(self) -> None:
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "mock": False})

    def test_teams_current_season_from_history(self) -> None:
        body = self.client.get("/api/teams").json()
        self.assertRegex(body["season"], r"^\d{4}/\d{2}$")
        self.assertEqual(len(body["current"]), 20)
        self.assertTrue(set(body["current"]).issubset(body["all"]))
        self.assertGreaterEqual(len(body["all"]), 46)
        self.assertRegex(body["data_end"], r"^\d{4}-\d{2}-\d{2}$")

    def test_predict_contract(self) -> None:
        r = self.client.post(
            "/api/predict",
            json={"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2024-04-23", "odds": [1.44, 5.0, 6.0]},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        probs = body["probabilities"]
        self.assertAlmostEqual(probs["home"] + probs["draw"] + probs["away"], 100.0, delta=PCT_TOL)
        self.assertEqual(body["predicted"], max(probs, key=probs.get))
        self.assertTrue(body["odds_used"])
        self.assertFalse(body["mock"])
        self.assertEqual(body["warnings"], [])
        self.assertIsNotNone(body["model_version"])
        for side in ("home_state", "away_state"):
            self.assertGreater(body[side]["elo"], 1000)
        self.assertLess(body["home_last_match"], "2024-04-23")

    def test_predict_matches_service(self) -> None:
        from prediction_service import get_predictor

        res = get_predictor().predict_match("Man City", "Liverpool", "2023-11-25", [1.73, 4.2, 4.2])
        body = self.client.post(
            "/api/predict",
            json={"home_team": "Man City", "away_team": "Liverpool", "match_date": "2023-11-25", "odds": [1.73, 4.2, 4.2]},
        ).json()
        num = res["numeric_probabilities"]
        self.assertAlmostEqual(body["probabilities"]["home"], num["P_Home"] * 100, delta=PCT_TOL)
        self.assertAlmostEqual(body["probabilities"]["draw"], num["P_Draw"] * 100, delta=PCT_TOL)
        self.assertAlmostEqual(body["probabilities"]["away"], num["P_Away"] * 100, delta=PCT_TOL)

    def test_debutant_team_gets_warning_not_error(self) -> None:
        r = self.client.post("/api/predict", json={"home_team": "Brentford", "away_team": "Arsenal", "match_date": "2021-08-13"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsNone(body["home_last_match"])
        self.assertEqual(body["home_state"]["form5"], 0.0)
        self.assertTrue(any("Brentford" in w for w in body["warnings"]))

    def test_validation_errors_are_spanish_text(self) -> None:
        cases = [
            {"home_team": "Arsenal", "away_team": "Arsenal"},
            {"home_team": "Real Madrid", "away_team": "Arsenal"},
            {"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "1995-01-01"},
            {"home_team": "Arsenal", "away_team": "Chelsea", "odds": [0.9, 3, 3]},
            {"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "no-es-fecha"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                r = self.client.post("/api/predict", json=payload)
                self.assertEqual(r.status_code, 422)
                self.assertIsInstance(r.json()["detail"], str)

    def test_metrics_identify_deployed_model(self) -> None:
        body = self.client.get("/api/metrics").json()
        names = [row["model"] for row in body["test_results"]]
        self.assertIn(body["deployed_model"], names)
        self.assertTrue(body["deployed_model"].startswith(body["selected_architecture"]))
        self.assertIn("Calibrado", body["deployed_model"])
        self.assertEqual(body["n_features"], 45)
        self.assertEqual(len(body["confusion_matrix"]), 3)
        self.assertNotIn("calibration_bins", body["test_results"][0])


class TestBackendCORSDefaults(unittest.TestCase):
    def test_default_is_local_frontend_only(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CORS_ALLOW_ORIGINS", None)
            self.assertEqual(
                backend_api._parse_cors_origins(), ["http://localhost:5173", "http://127.0.0.1:5173"]
            )

    def test_explicit_values(self) -> None:
        with mock.patch.dict(os.environ, {"CORS_ALLOW_ORIGINS": "*"}):
            self.assertEqual(backend_api._parse_cors_origins(), ["*"])
        with mock.patch.dict(os.environ, {"CORS_ALLOW_ORIGINS": " https://a.test , https://b.test "}):
            self.assertEqual(backend_api._parse_cors_origins(), ["https://a.test", "https://b.test"])


if __name__ == "__main__":
    unittest.main()

"""Pruebas de integración HTTP, bordes adversariales y latencia para la API FastAPI (src/api.py)."""

from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from src.api import app


class TestFastAPIBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._ctx = TestClient(app)
        cls.client = cls._ctx.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._ctx.__exit__(None, None, None)

    def test_health_and_openapi(self) -> None:
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["n_features"], 45)
        self.assertGreaterEqual(body["n_known_teams"], 46)

        r_spec = self.client.get("/openapi.json")
        self.assertEqual(r_spec.status_code, 200)
        self.assertIn("/predict", r_spec.json()["paths"])

    def test_teams_list_and_team_stats(self) -> None:
        r = self.client.get("/teams")
        self.assertEqual(r.status_code, 200)
        teams = r.json()["teams"]
        self.assertIn("Arsenal", teams)
        self.assertIn("Nott'm Forest", teams)

        r_stats = self.client.get("/teams/arsenal/stats", params={"match_date": "2024-08-17"})
        self.assertEqual(r_stats.status_code, 200)
        stats = r_stats.json()["stats"]
        self.assertEqual(stats["team"], "Arsenal")
        self.assertEqual(stats["season_pts"], 0)
        self.assertEqual(stats["season_gd"], 0)

        r_tz = self.client.get("/teams/arsenal/stats", params={"match_date": "2024-04-23T15:00:00Z"})
        self.assertEqual(r_tz.status_code, 200)

        r_nf = self.client.get("/teams/Nott'm Forest/stats")
        self.assertEqual(r_nf.status_code, 200)
        self.assertAlmostEqual(r_nf.json()["stats"]["elo"], 1785.14, places=2)

        r_404 = self.client.get("/teams/RealMadrid/stats")
        self.assertEqual(r_404.status_code, 404)

    def test_predict_single_batch_tz_and_debut(self) -> None:
        payload = {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "match_date": "2024-04-23T15:00:00Z",
            "odds": {"home": 1.55, "draw": 4.50, "away": 5.50},
            "decision_mode": "argmax",
        }
        r = self.client.post("/predict", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["match_date"], "2024-04-23")
        self.assertEqual(data["odds_source"], "bookmaker")
        self.assertEqual(len(data["top_factors"]), 5)

        r_debut = self.client.post(
            "/predict",
            json={"home_team": "Brentford", "away_team": "Arsenal", "match_date": "2021-08-13"},
        )
        self.assertEqual(r_debut.status_code, 200)
        self.assertGreaterEqual(len(r_debut.json()["warnings"]), 1)

        r_batch = self.client.post(
            "/predict/batch",
            json={
                "matches": [
                    {"home_team": "Man City", "away_team": "Liverpool", "match_date": "2023-11-25"},
                    {"home_team": "Manchester United", "away_team": "Nottingham Forest"},
                ]
            },
        )
        self.assertEqual(r_batch.status_code, 200)
        self.assertEqual(r_batch.json()["count"], 2)

    def test_predict_http_error_codes(self) -> None:
        r_unknown = self.client.post("/predict", json={"home_team": "Real Madrid", "away_team": "Chelsea"})
        self.assertEqual(r_unknown.status_code, 404)

        r_same = self.client.post("/predict", json={"home_team": "Arsenal", "away_team": "arsenal"})
        self.assertEqual(r_same.status_code, 400)

        r_date = self.client.post(
            "/predict", json={"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "bad-date"}
        )
        self.assertEqual(r_date.status_code, 400)

        r_odds_low = self.client.post(
            "/predict",
            json={
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "odds": {"home": 0.8, "draw": 3.5, "away": 4.0},
            },
        )
        self.assertEqual(r_odds_low.status_code, 422)

        r_odds_extreme = self.client.post(
            "/predict",
            json={
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "odds": {"home": 1e308, "draw": 3.5, "away": 4.0},
            },
        )
        self.assertEqual(r_odds_extreme.status_code, 422)

        r_batch_err = self.client.post(
            "/predict/batch",
            json={
                "matches": [
                    {"home_team": "Arsenal", "away_team": "Chelsea"},
                    {"home_team": "FakeFC", "away_team": "Chelsea"},
                ]
            },
        )
        self.assertEqual(r_batch_err.status_code, 404)
        self.assertEqual(r_batch_err.json()["detail"]["match_index"], 1)

    def test_model_metrics_compact_and_full(self) -> None:
        r_compact = self.client.get("/model/metrics")
        self.assertEqual(r_compact.status_code, 200)
        compact = r_compact.json()
        self.assertIn("test_results", compact)
        self.assertNotIn("calibration_bins", compact["test_results"][0])

        r_full = self.client.get("/model/metrics", params={"include_bins": "true"})
        self.assertEqual(r_full.status_code, 200)
        self.assertIn("calibration_bins", r_full.json()["test_results"][0])

    def test_latency_slas_single_and_batch50(self) -> None:
        _ = self.client.post("/predict", json={"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2024-04-23"})

        t0 = time.perf_counter()
        for _ in range(5):
            r1 = self.client.post(
                "/predict",
                json={"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2024-04-23"},
            )
            self.assertEqual(r1.status_code, 200)
        avg_single_ms = ((time.perf_counter() - t0) / 5.0) * 1000.0
        self.assertLess(avg_single_ms, 150.0, msg=f"Latencia single muy alta: {avg_single_ms:.1f} ms")

        t1 = time.perf_counter()
        r50 = self.client.post(
            "/predict/batch",
            json={
                "matches": [{"home_team": "Arsenal", "away_team": "Chelsea", "match_date": "2024-04-23"}] * 50
            },
        )
        batch50_ms = (time.perf_counter() - t1) * 1000.0
        self.assertEqual(r50.status_code, 200)
        self.assertLess(batch50_ms, 1500.0, msg=f"Latencia batch 50 muy alta: {batch50_ms:.1f} ms")


if __name__ == "__main__":
    unittest.main()

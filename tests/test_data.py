"""Pruebas unitarias de ingesta, consolidación sin huecos y búsqueda Elo causal."""

from __future__ import annotations

import unittest

import pandas as pd

from src.config import PROSPECTIVE_SEASONS, TEST_SEASONS, TRAIN_SEASONS, VAL_SEASONS
from src.data import load_unified_matches


class TestDataIngestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.df_unified, cls.elo_lookup = load_unified_matches(include_prospective=True)

    def test_no_duplicate_matches(self) -> None:
        dups = int(self.df_unified.duplicated(subset=["MatchDate", "HomeTeam", "AwayTeam"]).sum())
        self.assertEqual(dups, 0)

    def test_chronological_sorting(self) -> None:
        dates = self.df_unified["MatchDate"]
        self.assertTrue(dates.is_monotonic_increasing)

    def test_zero_gaps_across_25_epl_seasons(self) -> None:
        seasons_25 = list(TRAIN_SEASONS) + list(VAL_SEASONS) + list(TEST_SEASONS)
        counts = self.df_unified[self.df_unified["Season"].isin(seasons_25)]["Season"].value_counts()
        self.assertEqual(len(counts), 25)
        for season in seasons_25:
            self.assertEqual(int(counts[season]), 380, msg=f"Temporada {season} incompleta")

    def test_prospective_2025_26_season_present(self) -> None:
        prosp = self.df_unified[self.df_unified["Season"].isin(PROSPECTIVE_SEASONS)]
        self.assertEqual(len(prosp), 380)

    def test_zero_missing_elo_after_causal_lookup(self) -> None:
        self.assertEqual(int(self.df_unified["HomeElo"].isna().sum()), 0)
        self.assertEqual(int(self.df_unified["AwayElo"].isna().sum()), 0)

    def test_nottingham_forest_canonical_name_normalized(self) -> None:
        all_teams = set(self.df_unified["HomeTeam"].unique()) | set(self.df_unified["AwayTeam"].unique())
        self.assertIn("Nott'm Forest", all_teams)
        self.assertNotIn("Nottm Forest", all_teams)

    def test_nottingham_forest_elo_not_frozen_in_2025_2026(self) -> None:
        """Verifica corrección de HAL-03: los 41 Elos reales 2025-2026 no quedan congelados en 1731.5."""
        elo_nov_2025 = self.elo_lookup.get_elo("Nott'm Forest", pd.Timestamp("2025-11-01"))
        elo_sep_2026 = self.elo_lookup.get_elo("Nott'm Forest", pd.Timestamp("2026-09-01"))
        self.assertIsNotNone(elo_nov_2025)
        self.assertIsNotNone(elo_sep_2026)
        self.assertNotAlmostEqual(elo_nov_2025, 1731.5, places=1)
        self.assertAlmostEqual(elo_sep_2026, 1785.14, places=2)

    def test_elo_lookup_strict_causality_and_tz_safety(self) -> None:
        self.assertIsNone(self.elo_lookup.get_elo("Arsenal", pd.Timestamp("1999-01-01")))
        elo_2024 = self.elo_lookup.get_elo("Arsenal", pd.Timestamp("2024-04-23"))
        elo_2024_tz = self.elo_lookup.get_elo("Arsenal", "2024-04-23T15:00:00Z")
        self.assertIsNotNone(elo_2024)
        self.assertGreater(elo_2024, 1500.0)
        self.assertEqual(elo_2024, elo_2024_tz)


if __name__ == "__main__":
    unittest.main()

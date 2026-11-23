"""Fechas disponibles, partidos jugados y calendario opcional (api/matches.py)."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from api.matches import available_dates, load_fixtures, matches_on


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "MatchDate": pd.to_datetime(["2025-05-18", "2025-05-25", "2025-05-25", "2025-05-25"]),
            "HomeTeam": ["Arsenal", "Chelsea", "Arsenal", "Liverpool"],
            "AwayTeam": ["Chelsea", "Everton", "Fulham", "Wolves"],
            "FullTimeHomeGoals": [2, 1, 3, 0],
            "FullTimeAwayGoals": [1, 1, 0, 2],
            "FullTimeResult": ["H", "D", "H", "A"],
            "Season": ["2024/25"] * 4,
        }
    )


class TestDates(unittest.TestCase):
    def test_recientes_primero_con_conteo(self) -> None:
        out = available_dates(_history())
        self.assertEqual(out[0], {"date": "2025-05-25", "matches": 3})
        self.assertEqual(out[1], {"date": "2025-05-18", "matches": 1})

    def test_respeta_el_limite(self) -> None:
        self.assertEqual(len(available_dates(_history(), limit=1)), 1)


class TestMatchesOn(unittest.TestCase):
    def test_sin_fecha_devuelve_los_ultimos_partidos_con_su_fecha(self) -> None:
        day, rows = matches_on(_history(), None)
        self.assertIsNone(day)
        self.assertEqual([r["home_team"] for r in rows], ["Arsenal", "Chelsea", "Liverpool", "Arsenal"])
        self.assertEqual([r["date"] for r in rows], ["2025-05-25"] * 3 + ["2025-05-18"])
        self.assertEqual(rows[0]["home_goals"], 3)
        self.assertEqual(rows[2]["result"], "A")

    def test_sin_fecha_respeta_la_cantidad(self) -> None:
        _, rows = matches_on(_history(), None, latest=2)
        self.assertEqual(len(rows), 2)

    def test_con_fecha_devuelve_solo_ese_dia(self) -> None:
        day, rows = matches_on(_history(), "2025-05-18")
        self.assertEqual(day, "2025-05-18")
        self.assertEqual(len(rows), 1)

    def test_fecha_sin_partidos_es_lista_vacia(self) -> None:
        day, rows = matches_on(_history(), "2025-06-01")
        self.assertEqual(day, "2025-06-01")
        self.assertEqual(rows, [])


class TestFixtures(unittest.TestCase):
    def _write(self, text: str) -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / "fixtures.csv"
        p.write_text(text, encoding="utf-8")
        return p

    def test_archivo_inexistente_devuelve_none(self) -> None:
        self.assertIsNone(load_fixtures(Path("no/existe.csv"), date(2025, 5, 25)))

    def test_solo_conserva_partidos_posteriores_al_historial(self) -> None:
        p = self._write(
            "date,home_team,away_team,round\n"
            "2025-05-25,Arsenal,Chelsea,38\n"  # ya está en el historial
            "2025-08-16,Liverpool,Arsenal,1\n"
            "2025-08-16,Chelsea,Everton,\n"
        )
        out = load_fixtures(p, date(2025, 5, 25), known={"Arsenal", "Chelsea", "Liverpool", "Everton"})
        self.assertEqual(len(out["fixtures"]), 2)
        self.assertEqual(out["fixtures"][0]["home_team"], "Chelsea")  # orden por fecha y local
        self.assertEqual(out["fixtures"][1]["round"], "1")
        self.assertIsNone(out["fixtures"][0]["round"])

    def test_cuenta_las_filas_invalidas_sin_fallar(self) -> None:
        p = self._write(
            "date,home_team,away_team\n"
            "no-es-fecha,Arsenal,Chelsea\n"
            "2025-08-16,Arsenal,Arsenal\n"
            "2025-08-16,,Chelsea\n"
            "2025-08-17,Fulham,Wolves\n"
        )
        out = load_fixtures(p, date(2025, 5, 25))
        self.assertEqual(out["skipped"], 3)
        self.assertEqual(len(out["fixtures"]), 1)

    def test_marca_equipos_desconocidos(self) -> None:
        p = self._write("date,home_team,away_team\n2025-08-16,Real Madrid,Arsenal\n")
        out = load_fixtures(p, date(2025, 5, 25), known={"Arsenal"})
        self.assertFalse(out["fixtures"][0]["known"])

    def test_normaliza_alias_de_equipos(self) -> None:
        p = self._write("date,home_team,away_team\n2025-08-16,Spurs,Arsenal\n")
        out = load_fixtures(p, date(2025, 5, 25), normalize=lambda t: {"Spurs": "Tottenham"}.get(t, t))
        self.assertEqual(out["fixtures"][0]["home_team"], "Tottenham")


if __name__ == "__main__":
    unittest.main()

"""Funciones auxiliares del adaptador de la interfaz (api/main.py) que no necesitan el modelo."""

from __future__ import annotations

import unittest

from api.main import _calibration_summary, _outcome_from_label


class TestOutcomeFromLabel(unittest.TestCase):
    def test_traduce_las_tres_etiquetas_del_servicio(self) -> None:
        self.assertEqual(_outcome_from_label("Victoria de Arsenal (Local)"), "home")
        self.assertEqual(_outcome_from_label("Empate"), "draw")
        self.assertEqual(_outcome_from_label("Victoria de Chelsea (Visitante)"), "away")

    def test_etiqueta_desconocida_o_vacia_es_none(self) -> None:
        self.assertIsNone(_outcome_from_label(None))
        self.assertIsNone(_outcome_from_label(""))
        self.assertIsNone(_outcome_from_label("Algo raro"))


class TestCalibrationSummary(unittest.TestCase):
    SUMMARY = {
        "calibration": {
            "temperature": 1.17,
            "bayesian_weights": [1.0, 1.49, 1.08],
            "bayesian_tuning_val": {
                "val_base_accuracy": 0.53, "val_tuned_accuracy": 0.52,
                "val_base_f1_D": 0.05, "val_tuned_f1_D": 0.30, "weights": [1, 1.49, 1.08],
            },
        },
        "test_results": [
            {"model": "Otro"},
            {"model": "Red", "calibration_bins": {"top_label_ece": 0.03, "classwise_ece": {"H": 0.02},
                                                  "classwise_bins": {"H": [{"bin_low": 0.0}]}}},
        ],
    }

    def test_toma_la_fila_del_modelo_desplegado(self) -> None:
        out = _calibration_summary(self.SUMMARY, "Red")
        self.assertEqual(out["top_label_ece"], 0.03)
        self.assertEqual(out["classwise_bins"]["H"][0]["bin_low"], 0.0)
        self.assertEqual(out["temperature"], 1.17)

    def test_solo_conserva_los_campos_de_validacion_necesarios(self) -> None:
        out = _calibration_summary(self.SUMMARY, "Red")
        self.assertEqual(set(out["bayesian_tuning_val"]),
                         {"val_base_accuracy", "val_tuned_accuracy", "val_base_f1_D", "val_tuned_f1_D"})

    def test_sin_datos_de_calibracion_devuelve_none(self) -> None:
        self.assertIsNone(_calibration_summary({"test_results": [{"model": "Red"}]}, "Red"))


if __name__ == "__main__":
    unittest.main()

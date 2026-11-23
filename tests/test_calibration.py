"""Pruebas de calibración probabilística (Temperature Scaling, ECE y umbrales Bayesianos)."""

from __future__ import annotations

import unittest

import numpy as np
from sklearn.metrics import f1_score, log_loss

from src.calibration import (
    apply_temperature_scaling,
    expected_calibration_error,
    fit_bayesian_weights,
    fit_temperature_scaling,
    predict_with_weights,
)


class TestCalibrationAndBayesianThresholds(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(42)
        n = 600
        # Simular probabilidades sobreconfiadas con clase 1 (empate) minoritaria (~24%)
        logits = rng.normal(0.0, 1.3, size=(n, 3))
        logits[:, 0] += 0.55
        logits[:, 1] -= 0.40
        exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        true_probs = exp_l / exp_l.sum(axis=1, keepdims=True)
        self.y_val = np.array([rng.choice(3, p=row) for row in true_probs])

        # Hacer las predicciones deliberadamente sobreconfiadas (T < 1)
        sharp = np.exp(logits * 1.8 - np.max(logits * 1.8, axis=1, keepdims=True))
        self.overconfident_probs = sharp / sharp.sum(axis=1, keepdims=True)

    def test_temperature_scaling_improves_or_preserves_logloss_and_sums_to_one(self) -> None:
        t = fit_temperature_scaling(self.y_val, self.overconfident_probs)
        self.assertGreater(t, 1.0)
        cal = apply_temperature_scaling(self.overconfident_probs, t)
        self.assertTrue(np.allclose(cal.sum(axis=1), 1.0, atol=1e-9))
        ll_before = log_loss(self.y_val, self.overconfident_probs, labels=[0, 1, 2])
        ll_after = log_loss(self.y_val, cal, labels=[0, 1, 2])
        self.assertLessEqual(ll_after, ll_before + 1e-9)

    def test_ece_bounds_and_structure(self) -> None:
        diag = expected_calibration_error(self.y_val, self.overconfident_probs, n_bins=10)
        self.assertGreaterEqual(diag["top_label_ece"], 0.0)
        self.assertLessEqual(diag["top_label_ece"], 1.0)
        self.assertEqual(set(diag["classwise_ece"].keys()), {"H", "D", "A"})
        self.assertEqual(len(diag["top_label_bins"]), 10)

    def test_bayesian_weights_recover_minority_class_f1(self) -> None:
        base_f1 = f1_score(self.y_val, np.argmax(self.overconfident_probs, axis=1), average="macro", zero_division=0)
        weights, meta = fit_bayesian_weights(self.y_val, self.overconfident_probs)
        self.assertEqual(len(weights), 3)
        self.assertEqual(weights[0], 1.0)
        tuned_pred = predict_with_weights(self.overconfident_probs, weights)
        tuned_f1 = f1_score(self.y_val, tuned_pred, average="macro", zero_division=0)
        self.assertGreaterEqual(tuned_f1, base_f1)
        self.assertGreaterEqual(meta["val_tuned_f1_D"], meta["val_base_f1_D"])


if __name__ == "__main__":
    unittest.main()

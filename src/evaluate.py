"""Módulo unificado de evaluación de clasificación y fiabilidad probabilística."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)

from src.calibration import (
    brier_score_multiclass,
    brier_skill_score,
    expected_calibration_error,
    predict_with_weights,
)


def evaluate_predictions(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    model_name: str,
    dummy_brier: Optional[float] = None,
    bayesian_weights: Optional[list[float]] = None,
) -> dict[str, Any]:
    """Calcula métricas completas de clasificación, calibración y matriz de confusión."""
    y_arr = np.asarray(y_true, dtype=int)
    probs = np.asarray(y_probs, dtype=np.float64)
    probs_clean = np.clip(probs, 1e-15, 1.0 - 1e-15)
    probs_clean = probs_clean / probs_clean.sum(axis=1, keepdims=True)

    y_pred = np.argmax(probs_clean, axis=1)

    acc = float(accuracy_score(y_arr, y_pred))
    bal_acc = float(balanced_accuracy_score(y_arr, y_pred))
    macro_f1 = float(f1_score(y_arr, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_arr, y_pred, average="weighted", zero_division=0))

    f1_c = f1_score(y_arr, y_pred, labels=[0, 1, 2], average=None, zero_division=0)
    rec_c = recall_score(y_arr, y_pred, labels=[0, 1, 2], average=None, zero_division=0)
    prec_c = precision_score(y_arr, y_pred, labels=[0, 1, 2], average=None, zero_division=0)

    ll = float(log_loss(y_arr, probs_clean, labels=[0, 1, 2]))
    brier = brier_score_multiclass(y_arr, probs_clean)
    bss = brier_skill_score(brier, dummy_brier) if dummy_brier is not None else 0.0

    cm = confusion_matrix(y_arr, y_pred, labels=[0, 1, 2])
    cm_norm = confusion_matrix(y_arr, y_pred, labels=[0, 1, 2], normalize="true")
    cal_diag = expected_calibration_error(y_arr, probs_clean, n_bins=10)

    mean_pred = [round(float(x), 4) for x in np.mean(probs_clean, axis=0)]
    emp_freq = [round(float(np.mean(y_arr == c)), 4) for c in (0, 1, 2)]

    result: dict[str, Any] = {
        "model": model_name,
        "n_samples": int(len(y_arr)),
        "accuracy": round(acc, 6),
        "balanced_accuracy": round(bal_acc, 6),
        "macro_f1": round(macro_f1, 6),
        "weighted_f1": round(weighted_f1, 6),
        "f1_H": round(float(f1_c[0]), 6),
        "f1_D": round(float(f1_c[1]), 6),
        "f1_A": round(float(f1_c[2]), 6),
        "rec_H": round(float(rec_c[0]), 6),
        "rec_D": round(float(rec_c[1]), 6),
        "rec_A": round(float(rec_c[2]), 6),
        "prec_H": round(float(prec_c[0]), 6),
        "prec_D": round(float(prec_c[1]), 6),
        "prec_A": round(float(prec_c[2]), 6),
        "draws_predicted": int(cm[:, 1].sum()),
        "log_loss": round(ll, 6),
        "brier_score": round(brier, 6),
        "brier_skill_score": round(bss, 6),
        "top_label_ece": cal_diag["top_label_ece"],
        "top_label_mce": cal_diag["top_label_mce"],
        "mean_classwise_ece": cal_diag["mean_classwise_ece"],
        "classwise_ece": cal_diag["classwise_ece"],
        "mean_predicted_probs": mean_pred,
        "empirical_freqs": emp_freq,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_norm": [[round(float(v), 6) for v in row] for row in cm_norm],
        "calibration_bins": cal_diag,
    }

    if bayesian_weights is not None:
        y_pred_bay = predict_with_weights(probs_clean, bayesian_weights)
        f1_b = f1_score(y_arr, y_pred_bay, labels=[0, 1, 2], average=None, zero_division=0)
        rec_b = recall_score(y_arr, y_pred_bay, labels=[0, 1, 2], average=None, zero_division=0)
        prec_b = precision_score(y_arr, y_pred_bay, labels=[0, 1, 2], average=None, zero_division=0)
        cm_b = confusion_matrix(y_arr, y_pred_bay, labels=[0, 1, 2])
        result["bayesian_threshold_metrics"] = {
            "weights": [round(float(w), 4) for w in bayesian_weights],
            "accuracy": round(float(accuracy_score(y_arr, y_pred_bay)), 6),
            "balanced_accuracy": round(float(balanced_accuracy_score(y_arr, y_pred_bay)), 6),
            "macro_f1": round(float(f1_score(y_arr, y_pred_bay, average="macro", zero_division=0)), 6),
            "f1_H": round(float(f1_b[0]), 6),
            "f1_D": round(float(f1_b[1]), 6),
            "f1_A": round(float(f1_b[2]), 6),
            "rec_D": round(float(rec_b[1]), 6),
            "prec_D": round(float(prec_b[1]), 6),
            "draws_predicted": int(cm_b[:, 1].sum()),
            "confusion_matrix": cm_b.tolist(),
        }

    return result

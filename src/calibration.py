"""Calibración probabilística (Temperature Scaling), umbrales Bayesianos y métricas ECE/Brier."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss

from src.config import CLASS_CODES


def apply_temperature_scaling(probs: np.ndarray, temperature: float) -> np.ndarray:
    """
    Aplica Temperature Scaling sobre probabilidades Softmax mediante log-probabilidades:
    p_cal = softmax(log(p) / T). Para T=1.0 conserva la distribución original.
    """
    if temperature <= 0.0:
        raise ValueError("La temperatura debe ser estrictamente positiva.")
    probs_arr = np.asarray(probs, dtype=np.float64)
    if probs_arr.ndim == 1:
        probs_arr = probs_arr.reshape(1, -1)
    log_p = np.log(np.clip(probs_arr, 1e-12, 1.0))
    scaled = log_p / float(temperature)
    scaled = scaled - np.max(scaled, axis=1, keepdims=True)
    exp_s = np.exp(scaled)
    return exp_s / np.sum(exp_s, axis=1, keepdims=True)


def fit_temperature_scaling(y_val: np.ndarray, probs_val: np.ndarray) -> float:
    """Ajusta el escalar de temperatura T exclusivamente sobre el conjunto de validación."""

    def _objective(temp: float) -> float:
        cal = apply_temperature_scaling(probs_val, temp)
        return float(log_loss(y_val, cal, labels=[0, 1, 2]))

    res = minimize_scalar(_objective, bounds=(0.25, 5.0), method="bounded")
    best_t = float(res.x)
    # Garantizar que nunca empeore respecto a T=1.0
    if _objective(1.0) <= _objective(best_t):
        return 1.0
    return best_t


def predict_with_weights(probs: np.ndarray, weights: np.ndarray | list[float]) -> np.ndarray:
    """Clasificación por regla Bayesiana ponderada: argmax_c (w_c * p_c)."""
    w = np.asarray(weights, dtype=np.float64).reshape(1, -1)
    weighted = np.asarray(probs, dtype=np.float64) * w
    return np.argmax(weighted, axis=1)


def fit_bayesian_weights(
    y_val: np.ndarray,
    probs_val: np.ndarray,
    min_accuracy_ratio: float = 0.98,
) -> tuple[list[float], dict[str, Any]]:
    """
    Optimiza pesos de decisión [1.0, w_D, w_A] exclusivamente en Validación para mitigar
    el colapso de la clase minoritaria Empate (D) maximizando Macro-F1 sujeto a una
    cota mínima de exactitud global (min_accuracy_ratio * acc_argmax).
    """
    base_pred = np.argmax(probs_val, axis=1)
    base_acc = float(accuracy_score(y_val, base_pred))
    base_mf1 = float(f1_score(y_val, base_pred, average="macro", zero_division=0))
    base_f1_d = float(f1_score(y_val, base_pred, average=None, zero_division=0)[1])

    min_acc = base_acc * min_accuracy_ratio
    best_score = (base_mf1, base_f1_d, base_acc)
    best_w = [1.0, 1.0, 1.0]

    # Búsqueda gruesa en malla sobre Val
    for wd in np.arange(1.00, 2.35, 0.05):
        for wa in np.arange(0.80, 1.45, 0.05):
            w = [1.0, float(wd), float(wa)]
            pred = predict_with_weights(probs_val, w)
            acc = float(accuracy_score(y_val, pred))
            if acc < min_acc:
                continue
            mf1 = float(f1_score(y_val, pred, average="macro", zero_division=0))
            f1_d = float(f1_score(y_val, pred, average=None, zero_division=0)[1])
            score = (mf1, f1_d, acc)
            if score > best_score:
                best_score = score
                best_w = [round(x, 4) for x in w]

    # Refinamiento fino alrededor del óptimo en malla
    center_d, center_a = best_w[1], best_w[2]
    for wd in np.arange(max(1.0, center_d - 0.05), center_d + 0.051, 0.01):
        for wa in np.arange(max(0.7, center_a - 0.05), center_a + 0.051, 0.01):
            w = [1.0, float(wd), float(wa)]
            pred = predict_with_weights(probs_val, w)
            acc = float(accuracy_score(y_val, pred))
            if acc < min_acc:
                continue
            mf1 = float(f1_score(y_val, pred, average="macro", zero_division=0))
            f1_d = float(f1_score(y_val, pred, average=None, zero_division=0)[1])
            score = (mf1, f1_d, acc)
            if score > best_score:
                best_score = score
                best_w = [round(x, 4) for x in w]

    final_pred = predict_with_weights(probs_val, best_w)
    meta = {
        "weights": best_w,
        "min_accuracy_guardrail": round(min_acc, 4),
        "val_base_accuracy": round(base_acc, 4),
        "val_base_macro_f1": round(base_mf1, 4),
        "val_base_f1_D": round(base_f1_d, 4),
        "val_tuned_accuracy": round(float(accuracy_score(y_val, final_pred)), 4),
        "val_tuned_balanced_accuracy": round(float(balanced_accuracy_score(y_val, final_pred)), 4),
        "val_tuned_macro_f1": round(float(f1_score(y_val, final_pred, average="macro", zero_division=0)), 4),
        "val_tuned_f1_D": round(float(f1_score(y_val, final_pred, average=None, zero_division=0)[1]), 4),
    }
    return best_w, meta


def brier_score_multiclass(y_true: np.ndarray, probs: np.ndarray) -> float:
    """Puntuación de Brier multiclase: media de suma cuadrática sobre las 3 clases."""
    y_oh = np.eye(3, dtype=np.float64)[y_true]
    return float(np.mean(np.sum((np.asarray(probs, dtype=np.float64) - y_oh) ** 2, axis=1)))


def brier_skill_score(brier: float, reference_brier: float) -> float:
    """Brier Skill Score relativo a un modelo de referencia (1 - BS / BS_ref)."""
    if reference_brier <= 0.0:
        return 0.0
    return float(1.0 - (brier / reference_brier))


def expected_calibration_error(
    y_true: np.ndarray,
    probs: np.ndarray,
    n_bins: int = 10,
) -> dict[str, Any]:
    """
    Calcula ECE/MCE sobre predicción principal (top-label) y curvas de confiabilidad
    (reliability bins) por cada clase (H, D, A).
    """
    probs_arr = np.asarray(probs, dtype=np.float64)
    y_arr = np.asarray(y_true, dtype=int)
    n = len(y_arr)

    confidences = np.max(probs_arr, axis=1)
    predictions = np.argmax(probs_arr, axis=1)
    accuracies = (predictions == y_arr).astype(np.float64)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    top_ece = 0.0
    top_mce = 0.0
    top_bins: list[dict[str, Any]] = []

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        if i == 0:
            mask = (confidences >= low) & (confidences <= high)
        else:
            mask = (confidences > low) & (confidences <= high)
        cnt = int(np.sum(mask))
        if cnt > 0:
            avg_conf = float(np.mean(confidences[mask]))
            avg_acc = float(np.mean(accuracies[mask]))
            gap = abs(avg_acc - avg_conf)
            top_ece += (cnt / n) * gap
            top_mce = max(top_mce, gap)
            top_bins.append(
                {
                    "bin_low": round(float(low), 2),
                    "bin_high": round(float(high), 2),
                    "count": cnt,
                    "mean_confidence": round(avg_conf, 4),
                    "empirical_accuracy": round(avg_acc, 4),
                    "gap": round(gap, 4),
                }
            )
        else:
            top_bins.append(
                {
                    "bin_low": round(float(low), 2),
                    "bin_high": round(float(high), 2),
                    "count": 0,
                    "mean_confidence": None,
                    "empirical_accuracy": None,
                    "gap": None,
                }
            )

    classwise_ece: dict[str, float] = {}
    classwise_bins: dict[str, list[dict[str, Any]]] = {}
    for cls_idx, cls_code in enumerate(CLASS_CODES):
        cls_probs = probs_arr[:, cls_idx]
        cls_true = (y_arr == cls_idx).astype(np.float64)
        c_ece = 0.0
        c_bins: list[dict[str, Any]] = []
        for i in range(n_bins):
            low, high = bin_edges[i], bin_edges[i + 1]
            mask = (cls_probs >= low) & (cls_probs <= high) if i == 0 else (cls_probs > low) & (cls_probs <= high)
            cnt = int(np.sum(mask))
            if cnt > 0:
                avg_p = float(np.mean(cls_probs[mask]))
                emp_f = float(np.mean(cls_true[mask]))
                gap = abs(emp_f - avg_p)
                c_ece += (cnt / n) * gap
                c_bins.append(
                    {
                        "bin_low": round(float(low), 2),
                        "bin_high": round(float(high), 2),
                        "count": cnt,
                        "mean_predicted_prob": round(avg_p, 4),
                        "empirical_frequency": round(emp_f, 4),
                        "gap": round(gap, 4),
                    }
                )
            else:
                c_bins.append(
                    {
                        "bin_low": round(float(low), 2),
                        "bin_high": round(float(high), 2),
                        "count": 0,
                        "mean_predicted_prob": None,
                        "empirical_frequency": None,
                        "gap": None,
                    }
                )
        classwise_ece[cls_code] = round(float(c_ece), 5)
        classwise_bins[cls_code] = c_bins

    return {
        "top_label_ece": round(float(top_ece), 5),
        "top_label_mce": round(float(top_mce), 5),
        "mean_classwise_ece": round(float(np.mean(list(classwise_ece.values()))), 5),
        "classwise_ece": classwise_ece,
        "top_label_bins": top_bins,
        "classwise_bins": classwise_bins,
    }

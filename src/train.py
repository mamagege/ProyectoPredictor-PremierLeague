"""Pipeline reproducible de entrenamiento, selección en Validación, calibración y persistencia atómica."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
import tensorflow as tf
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from tensorflow import keras

from src.calibration import (
    apply_temperature_scaling,
    fit_bayesian_weights,
    fit_temperature_scaling,
)
from src.config import (
    CALIBRATION_PATH,
    FEATURE_NAMES_PATH,
    MODEL_PATH,
    MODELS_DIR,
    PREPROCESSOR_PATH,
    PROSPECTIVE_SEASONS,
    SCALER_PATH,
    SEED,
    TARGET_MAP,
    TEST_SEASONS,
    TRAIN_SEASONS,
    TRAINING_SUMMARY_PATH,
    VAL_SEASONS,
)
from src.data import load_unified_matches
from src.evaluate import evaluate_predictions
from src.features import (
    FEATURE_NAMES,
    NON_MARKET_FEATURE_NAMES,
    CausalPreprocessor,
    FeatureStateEngine,
)
from src.models import (
    build_compact_deep_mlp,
    build_deep_mlp_hito2,
    build_residual_deep_mlp,
    set_deterministic_seed,
)

logger = logging.getLogger(__name__)


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def _atomic_write_joblib(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    try:
        joblib.dump(obj, tmp_name)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def _atomic_save_keras(path: Path, model: keras.Model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem + "_", suffix=".keras", dir=str(path.parent))
    os.close(fd)
    try:
        model.save(tmp_name)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def _train_keras_candidate(
    name: str,
    model_fn,
    X_train: np.ndarray,
    y_train_cat: np.ndarray,
    X_val: np.ndarray,
    y_val_cat: np.ndarray,
    y_val: np.ndarray,
    learning_rate: float = 1e-3,
    batch_size: int = 64,
    epochs: int = 120,
) -> dict[str, Any]:
    set_deterministic_seed(SEED)
    model = model_fn(X_train.shape[1])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    cb_list = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=18,
            restore_best_weights=True,
            verbose=0,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=6,
            min_lr=1e-5,
            verbose=0,
        ),
    ]
    history = model.fit(
        X_train,
        y_train_cat,
        validation_data=(X_val, y_val_cat),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=cb_list,
        verbose=0,
    )
    probs_val = model.predict(X_val, verbose=0)
    val_ll = float(log_loss(y_val, np.clip(probs_val, 1e-15, 1.0 - 1e-15), labels=[0, 1, 2]))
    best_epoch = int(np.argmin(history.history["val_loss"])) + 1
    return {
        "name": name,
        "model": model,
        "history": {k: [round(float(v), 6) for v in vals] for k, vals in history.history.items()},
        "epochs_trained": len(history.history["loss"]),
        "best_epoch": best_epoch,
        "val_loss": val_ll,
        "train_loss_final": float(history.history["loss"][best_epoch - 1]),
        "val_loss_history_best": float(min(history.history["val_loss"])),
        "learning_rate": learning_rate,
        "total_params": int(model.count_params()),
    }


def _tune_logistic_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[LogisticRegression, float, float]:
    best_c = 1.0
    best_ll = float("inf")
    best_model = None
    for c_val in (0.005, 0.01, 0.05, 0.1, 0.5, 1.0):
        clf = LogisticRegression(C=c_val, max_iter=1500, random_state=SEED)
        clf.fit(X_train, y_train)
        probs_val = clf.predict_proba(X_val)
        ll = float(log_loss(y_val, probs_val, labels=[0, 1, 2]))
        if ll < best_ll:
            best_ll = ll
            best_c = c_val
            best_model = clf
    assert best_model is not None
    return best_model, best_c, best_ll


def _tune_hist_gradient_boosting(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[HistGradientBoostingClassifier, dict[str, Any], float]:
    best_cfg: dict[str, Any] = {}
    best_ll = float("inf")
    best_model = None
    grid = [
        {"max_iter": mi, "max_depth": md, "learning_rate": lr, "l2_regularization": l2, "min_samples_leaf": msl}
        for mi in (60, 100, 150)
        for md in (3, 4)
        for lr in (0.03, 0.05)
        for l2 in (1.0, 5.0)
        for msl in (30, 60)
    ]
    for cfg in grid:
        clf = HistGradientBoostingClassifier(
            early_stopping=False,
            random_state=SEED,
            **cfg,
        )
        clf.fit(X_train, y_train)
        probs_val = clf.predict_proba(X_val)
        ll = float(log_loss(y_val, probs_val, labels=[0, 1, 2]))
        if ll < best_ll:
            best_ll = ll
            best_cfg = cfg
            best_model = clf
    assert best_model is not None
    return best_model, best_cfg, best_ll


def run_training_pipeline(remove_legacy_models: bool = True) -> dict[str, Any]:
    """Ejecuta el entrenamiento completo y persiste artefactos sincronizados en models/."""
    set_deterministic_seed(SEED)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Cargando e integrando datasets históricos y prospectivos...")
    df_unified, _ = load_unified_matches(include_prospective=True)
    print(f"   Partidos totales consolidados: {len(df_unified)} ({df_unified['MatchDate'].min().date()} a {df_unified['MatchDate'].max().date()})")

    print("2. Calculando 45 características estrictamente pre-partido (FeatureStateEngine)...")
    df_raw = FeatureStateEngine.compute_batch_features(df_unified)

    train_mask = df_raw["Season"].isin(TRAIN_SEASONS).to_numpy()
    val_mask = df_raw["Season"].isin(VAL_SEASONS).to_numpy()
    test_mask = df_raw["Season"].isin(TEST_SEASONS).to_numpy()
    prosp_mask = df_raw["Season"].isin(PROSPECTIVE_SEASONS).to_numpy()

    y_all = df_raw["FullTimeResult"].map(TARGET_MAP).to_numpy(dtype=int)
    y_train, y_val, y_test, y_prosp = y_all[train_mask], y_all[val_mask], y_all[test_mask], y_all[prosp_mask]

    print(
        f"   Partición estricta -> Train: {len(y_train)}, Val: {len(y_val)}, "
        f"Test: {len(y_test)}, Prospectivo 2025/26: {len(y_prosp)}"
    )

    print("3. Ajustando CausalPreprocessor exclusivamente en Train...")
    preprocessor = CausalPreprocessor(feature_names=list(FEATURE_NAMES))
    preprocessor.fit(df_raw.loc[train_mask], y_train)

    df_final_all = preprocessor.finalize_features_df(df_raw)
    X_train = preprocessor.transform_df(df_raw.loc[train_mask])
    X_val = preprocessor.transform_df(df_raw.loc[val_mask])
    X_test = preprocessor.transform_df(df_raw.loc[test_mask])
    X_prosp = preprocessor.transform_df(df_raw.loc[prosp_mask])

    y_train_cat = keras.utils.to_categorical(y_train, num_classes=3)
    y_val_cat = keras.utils.to_categorical(y_val, num_classes=3)

    # Probabilidades implícitas de mercado (Bet365 / fallback Elo)
    mkt_cols = ["ProbMarket_Home", "ProbMarket_Draw", "ProbMarket_Away"]
    mkt_val = df_final_all.loc[val_mask, mkt_cols].to_numpy(dtype=np.float64)
    mkt_test = df_final_all.loc[test_mask, mkt_cols].to_numpy(dtype=np.float64)
    mkt_prosp = df_final_all.loc[prosp_mask, mkt_cols].to_numpy(dtype=np.float64)

    print("4. Entrenando y ajustando modelos de referencia en Validación...")
    dummy = DummyClassifier(strategy="prior")
    dummy.fit(X_train, y_train)

    lr_clf, best_lr_c, lr_val_ll = _tune_logistic_regression(X_train, y_train, X_val, y_val)
    print(f"   Regresión Logística mejor C={best_lr_c} (val_loss={lr_val_ll:.4f})")

    hgb_clf, best_hgb_cfg, hgb_val_ll = _tune_hist_gradient_boosting(X_train, y_train, X_val, y_val)
    print(f"   HistGradientBoosting mejor cfg={best_hgb_cfg} (val_loss={hgb_val_ll:.4f})")

    print("5. Entrenando arquitecturas candidatas Deep MLP (selección estricta por val_loss)...")
    candidates = [
        _train_keras_candidate(
            "Deep_MLP_Hito2",
            build_deep_mlp_hito2,
            X_train,
            y_train_cat,
            X_val,
            y_val_cat,
            y_val,
            learning_rate=1e-3,
        ),
        _train_keras_candidate(
            "Compact_Deep_MLP",
            lambda d: build_compact_deep_mlp(d, l2_reg=2e-3),
            X_train,
            y_train_cat,
            X_val,
            y_val_cat,
            y_val,
            learning_rate=1e-3,
        ),
        _train_keras_candidate(
            "Residual_Deep_MLP_3L",
            lambda d: build_residual_deep_mlp(
                d,
                hidden_units=(64, 32, 16),
                dropouts=(0.35, 0.25, 0.15),
                l2_linear=1e-2,
                l2_deep=3e-3,
                name="Residual_Deep_MLP_3L",
            ),
            X_train,
            y_train_cat,
            X_val,
            y_val_cat,
            y_val,
            learning_rate=8e-4,
        ),
        _train_keras_candidate(
            "Residual_Deep_MLP_4L",
            lambda d: build_residual_deep_mlp(
                d,
                hidden_units=(128, 64, 32, 16),
                dropouts=(0.35, 0.30, 0.20, 0.10),
                l2_linear=1e-2,
                l2_deep=4e-3,
                name="Residual_Deep_MLP_4L",
            ),
            X_train,
            y_train_cat,
            X_val,
            y_val_cat,
            y_val,
            learning_rate=8e-4,
        ),
    ]

    for cand in candidates:
        print(
            f"   -> {cand['name']:24s} | params={cand['total_params']:5d} | "
            f"best_epoch={cand['best_epoch']:2d}/{cand['epochs_trained']:2d} | val_loss={cand['val_loss']:.5f}"
        )

    winner = min(candidates, key=lambda c: c["val_loss"])
    winner_model: keras.Model = winner["model"]
    print(f"   Modelo neuronal seleccionado por Val Loss: {winner['name']} ({winner['val_loss']:.5f})")

    print("6. Calibrando probabilidades (Temperature Scaling) y umbrales Bayesianos en Validación...")
    probs_val_winner_raw = winner_model.predict(X_val, verbose=0)
    probs_test_winner_raw = winner_model.predict(X_test, verbose=0)
    probs_prosp_winner_raw = winner_model.predict(X_prosp, verbose=0)

    temperature = fit_temperature_scaling(y_val, probs_val_winner_raw)
    probs_val_winner_cal = apply_temperature_scaling(probs_val_winner_raw, temperature)
    probs_test_winner_cal = apply_temperature_scaling(probs_test_winner_raw, temperature)
    probs_prosp_winner_cal = apply_temperature_scaling(probs_prosp_winner_raw, temperature)

    bayesian_weights, bayesian_meta = fit_bayesian_weights(y_val, probs_val_winner_cal)
    print(f"   Temperature T = {temperature:.4f} | Pesos Bayesianos = {bayesian_weights}")

    print("7. Ejecutando estudio de ablación (sin cuotas de mercado, 40 variables deportivas)...")
    X_train_nm = preprocessor.transform_df(df_raw.loc[train_mask], selected_features=NON_MARKET_FEATURE_NAMES)
    X_val_nm = preprocessor.transform_df(df_raw.loc[val_mask], selected_features=NON_MARKET_FEATURE_NAMES)
    X_test_nm = preprocessor.transform_df(df_raw.loc[test_mask], selected_features=NON_MARKET_FEATURE_NAMES)
    X_prosp_nm = preprocessor.transform_df(df_raw.loc[prosp_mask], selected_features=NON_MARKET_FEATURE_NAMES)

    ablation_res = _train_keras_candidate(
        "Ablation_NoMarket_ResMLP",
        lambda d: build_residual_deep_mlp(
            d,
            hidden_units=(64, 32, 16),
            dropouts=(0.35, 0.25, 0.15),
            l2_linear=1e-2,
            l2_deep=3e-3,
            name="Ablation_NoMarket_ResMLP",
        ),
        X_train_nm,
        y_train_cat,
        X_val_nm,
        y_val_cat,
        y_val,
        learning_rate=8e-4,
    )
    ablation_model: keras.Model = ablation_res["model"]
    probs_val_ablation = ablation_model.predict(X_val_nm, verbose=0)
    probs_test_ablation = ablation_model.predict(X_test_nm, verbose=0)
    probs_prosp_ablation = ablation_model.predict(X_prosp_nm, verbose=0)

    print("8. Evaluando conjunto completo de modelos en Val, Test y Prospectivo 2025/26...")

    def _eval_split(y_true: np.ndarray, X_split: np.ndarray, mkt_split: np.ndarray, probs_win_raw: np.ndarray, probs_win_cal: np.ndarray, probs_abl: np.ndarray) -> list[dict[str, Any]]:
        dummy_probs = dummy.predict_proba(X_split)
        dummy_eval = evaluate_predictions(y_true, dummy_probs, "Dummy (Prior/Mayoría)")
        dummy_brier = dummy_eval["brier_score"]

        hito2_mlp = candidates[0]["model"]
        results = [
            dummy_eval,
            evaluate_predictions(y_true, mkt_split, "Bet365 (Cuotas Implícitas)", dummy_brier=dummy_brier),
            evaluate_predictions(y_true, lr_clf.predict_proba(X_split), f"Regresión Logística (C={best_lr_c})", dummy_brier=dummy_brier),
            evaluate_predictions(y_true, hgb_clf.predict_proba(X_split), "HistGradientBoosting (Tuned Val)", dummy_brier=dummy_brier),
            evaluate_predictions(y_true, hito2_mlp.predict(X_split, verbose=0), "Deep MLP Hito 2 (128-64-32-16)", dummy_brier=dummy_brier),
            evaluate_predictions(y_true, probs_win_raw, f"{winner['name']} (Sin Calibrar)", dummy_brier=dummy_brier),
            evaluate_predictions(
                y_true,
                probs_win_cal,
                f"{winner['name']} (Calibrado T={temperature:.3f})",
                dummy_brier=dummy_brier,
                bayesian_weights=bayesian_weights,
            ),
            evaluate_predictions(y_true, probs_abl, "Ablación Sin Cuotas (40 vars)", dummy_brier=dummy_brier),
        ]
        return results

    val_results = _eval_split(y_val, X_val, mkt_val, probs_val_winner_raw, probs_val_winner_cal, probs_val_ablation)
    test_results = _eval_split(y_test, X_test, mkt_test, probs_test_winner_raw, probs_test_winner_cal, probs_test_ablation)
    prosp_results = _eval_split(y_prosp, X_prosp, mkt_prosp, probs_prosp_winner_raw, probs_prosp_winner_cal, probs_prosp_ablation)

    print("\n=== RESULTADOS EN TEST SET (2021/22–2024/25, n=1520) ===")
    for r in test_results:
        line = (
            f"  {r['model']:38s} | Acc={r['accuracy']:.4f} | LL={r['log_loss']:.4f} | "
            f"Brier={r['brier_score']:.4f} | BSS={r['brier_skill_score']:+.4f} | "
            f"ECE={r['top_label_ece']:.4f} | F1-D={r['f1_D']:.4f}"
        )
        if "bayesian_threshold_metrics" in r:
            bm = r["bayesian_threshold_metrics"]
            line += f" | Bay[Acc={bm['accuracy']:.4f}, MacF1={bm['macro_f1']:.4f}, F1-D={bm['f1_D']:.4f}]"
        print(line)

    print("\n=== RESULTADOS PROSPECTIVOS 2025/26 (n=380, NUNCA VISTOS) ===")
    for r in prosp_results:
        line = (
            f"  {r['model']:38s} | Acc={r['accuracy']:.4f} | LL={r['log_loss']:.4f} | "
            f"Brier={r['brier_score']:.4f} | ECE={r['top_label_ece']:.4f} | F1-D={r['f1_D']:.4f}"
        )
        if "bayesian_threshold_metrics" in r:
            bm = r["bayesian_threshold_metrics"]
            line += f" | Bay[Acc={bm['accuracy']:.4f}, MacF1={bm['macro_f1']:.4f}, F1-D={bm['f1_D']:.4f}]"
        print(line)

    trained_at = datetime.now(timezone.utc).isoformat()
    model_version = "3.0.0-hito3-backend"

    calibration_payload = {
        "model_version": model_version,
        "selected_architecture": winner["name"],
        "temperature": round(float(temperature), 6),
        "bayesian_weights": [round(float(w), 4) for w in bayesian_weights],
        "bayesian_tuning_val": bayesian_meta,
        "seed": SEED,
        "trained_at_utc": trained_at,
    }

    winner_test_entry = next(r for r in test_results if "Calibrado" in r["model"])
    summary_payload = {
        "model_version": model_version,
        "trained_at_utc": trained_at,
        "seed": SEED,
        "environment": {
            "tensorflow": tf.__version__,
            "keras": keras.__version__,
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "dataset_splits": {
            "total_matches_loaded": int(len(df_raw)),
            "train_seasons": list(TRAIN_SEASONS),
            "train_matches": int(len(y_train)),
            "val_seasons": list(VAL_SEASONS),
            "val_matches": int(len(y_val)),
            "test_seasons": list(TEST_SEASONS),
            "test_matches": int(len(y_test)),
            "prospective_seasons": list(PROSPECTIVE_SEASONS),
            "prospective_matches": int(len(y_prosp)),
            "n_features": len(FEATURE_NAMES),
            "train_priors": [round(float(x), 6) for x in preprocessor.train_priors_],
        },
        "selected_architecture": winner["name"],
        "epochs_trained": winner["epochs_trained"],
        "best_epoch": winner["best_epoch"],
        "total_params": winner["total_params"],
        "train_loss_final": round(winner["train_loss_final"], 6),
        "val_loss_best": round(winner["val_loss"], 6),
        "calibration": calibration_payload,
        "candidate_models_val_selection": [
            {
                "name": c["name"],
                "total_params": c["total_params"],
                "best_epoch": c["best_epoch"],
                "epochs_trained": c["epochs_trained"],
                "val_loss": round(c["val_loss"], 6),
                "learning_rate": c["learning_rate"],
            }
            for c in candidates
        ],
        "baseline_tuning": {
            "logistic_regression_best_C": best_lr_c,
            "hist_gradient_boosting_best_params": best_hgb_cfg,
        },
        "val_results": val_results,
        "test_results": test_results,
        "prospective_2025_26_results": prosp_results,
        "confusion_matrix": winner_test_entry["confusion_matrix"],
        "confusion_matrix_norm": winner_test_entry["confusion_matrix_norm"],
    }

    print("\n9. Guardando artefactos sincronizados de forma atómica en models/...")
    _atomic_save_keras(MODEL_PATH, winner_model)
    _atomic_write_joblib(SCALER_PATH, preprocessor.scaler_)
    _atomic_write_joblib(PREPROCESSOR_PATH, preprocessor)
    _atomic_write_json(FEATURE_NAMES_PATH, list(FEATURE_NAMES))
    _atomic_write_json(CALIBRATION_PATH, calibration_payload)
    _atomic_write_json(TRAINING_SUMMARY_PATH, summary_payload)

    if remove_legacy_models:
        for legacy_name in ("deep_mlp_3layers.keras", "deep_mlp_4layers.keras"):
            legacy_path = MODELS_DIR / legacy_name
            if legacy_path.exists():
                legacy_path.unlink()
                print(f"   Eliminado artefacto obsoleto huérfano: {legacy_path.name}")

    print("Entrenamiento y persistencia completados correctamente.")
    return summary_payload


if __name__ == "__main__":
    run_training_pipeline()

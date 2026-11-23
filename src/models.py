"""Definición de arquitecturas neuronales (Keras) y utilidades de determinismo."""

from __future__ import annotations

import logging
import os
import random

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, regularizers

from src.config import SEED

logger = logging.getLogger(__name__)


def set_deterministic_seed(seed: int = SEED) -> None:
    """Configura semillas y determinismo de operadores para reproducibilidad científica."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception as exc:
        logger.warning("No se pudo habilitar determinismo estricto de TF: %s", exc)


def build_deep_mlp_hito2(input_dim: int) -> keras.Model:
    """Arquitectura original del Hito 2 (128-64-32-16) para comparativa de referencia."""
    return keras.Sequential(
        [
            layers.Input(shape=(input_dim,), name="Input_Features"),
            layers.Dense(128, activation="relu", kernel_regularizer=regularizers.l2(1e-4), name="Dense_128"),
            layers.BatchNormalization(name="BatchNorm_1"),
            layers.Dropout(0.25, name="Dropout_1"),
            layers.Dense(64, activation="relu", kernel_regularizer=regularizers.l2(1e-4), name="Dense_64"),
            layers.BatchNormalization(name="BatchNorm_2"),
            layers.Dropout(0.20, name="Dropout_2"),
            layers.Dense(32, activation="relu", kernel_regularizer=regularizers.l2(1e-4), name="Dense_32"),
            layers.Dropout(0.15, name="Dropout_3"),
            layers.Dense(16, activation="relu", name="Dense_16"),
            layers.Dense(3, activation="softmax", name="Output_Softmax"),
        ],
        name="Deep_MLP_Hito2",
    )


def build_compact_deep_mlp(input_dim: int, l2_reg: float = 1e-3) -> keras.Model:
    """Deep MLP regularizado (64-32-16) adaptado a señal tabular ruidosa."""
    return keras.Sequential(
        [
            layers.Input(shape=(input_dim,), name="Input_Features"),
            layers.Dense(64, activation="relu", kernel_regularizer=regularizers.l2(l2_reg), name="Dense_64"),
            layers.BatchNormalization(name="BatchNorm_1"),
            layers.Dropout(0.35, name="Dropout_1"),
            layers.Dense(32, activation="relu", kernel_regularizer=regularizers.l2(l2_reg), name="Dense_32"),
            layers.BatchNormalization(name="BatchNorm_2"),
            layers.Dropout(0.25, name="Dropout_2"),
            layers.Dense(16, activation="relu", kernel_regularizer=regularizers.l2(l2_reg), name="Dense_16"),
            layers.Dropout(0.15, name="Dropout_3"),
            layers.Dense(3, activation="softmax", name="Output_Softmax"),
        ],
        name="Compact_Deep_MLP",
    )


def build_residual_deep_mlp(
    input_dim: int,
    hidden_units: tuple[int, ...] = (64, 32, 16),
    dropouts: tuple[float, ...] = (0.35, 0.25, 0.15),
    l2_linear: float = 5e-3,
    l2_deep: float = 2e-3,
    name: str = "Residual_Deep_MLP",
) -> keras.Model:
    """
    Deep MLP con conexión residual lineal directa en logits (Wide & Deep / ResMLP).
    Conserva la señal probabilística de entrada y deja que las capas profundas aprendan
    correcciones no lineales sin degradar la calibración base.
    """
    inp = layers.Input(shape=(input_dim,), name="Input_Features")

    linear_logits = layers.Dense(
        3,
        activation=None,
        kernel_regularizer=regularizers.l2(l2_linear),
        name="Linear_Skip_Logits",
    )(inp)

    x = inp
    for idx, (units, drop) in enumerate(zip(hidden_units, dropouts), start=1):
        x = layers.Dense(
            units,
            activation="relu",
            kernel_regularizer=regularizers.l2(l2_deep),
            name=f"ResDeep_Dense_{idx}_{units}",
        )(x)
        x = layers.BatchNormalization(name=f"ResDeep_BN_{idx}")(x)
        if drop > 0.0:
            x = layers.Dropout(drop, name=f"ResDeep_Drop_{idx}")(x)

    deep_logits = layers.Dense(
        3,
        activation=None,
        kernel_initializer="zeros",
        kernel_regularizer=regularizers.l2(l2_deep),
        name="Deep_Residual_Logits",
    )(x)

    combined_logits = layers.Add(name="Combined_Logits")([linear_logits, deep_logits])
    output = layers.Activation("softmax", name="Output_Softmax")(combined_logits)

    return keras.Model(inputs=inp, outputs=output, name=name)

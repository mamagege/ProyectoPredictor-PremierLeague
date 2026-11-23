# Sistema Predictor de Resultados EPL — Backend (PTIA Hito 3)

**Institución:** Escuela Colombiana de Ingeniería Julio Garavito  
**Curso:** Proyecto Transversal en Inteligencia Artificial (PTIA) — Grupo 04  
**Integrantes:** Juan Diego Gaitán, José Alejandro Martínez, Oscar David Lasso, Carlos Andrés Sánchez  
**Rama:** `feat/hito3-backend` (versión de modelo `3.0.0-hito3-backend`)

---

## Arquitectura del Backend

El backend fue refactorizado y blindado en una arquitectura modular con fuente única de verdad para garantizar **cero fuga de datos**, **paridad exacta entre entrenamiento e inferencia** (`atol=1e-9`) y **reproducibilidad determinista**:

```text
├── src/
│   ├── config.py          # Rutas portables, particiones temporales, normalización y alias de clubes
│   ├── data.py            # Consolidación 2000–2026 sin huecos (9,900 partidos) y búsqueda causal Elo O(log n)
│   ├── features.py        # FeatureStateEngine (45 vars pre-partido) y CausalPreprocessor (ajustado solo en Train)
│   ├── models.py          # Arquitecturas Keras (Deep MLP Hito 2, Compact MLP, Residual Deep MLP) y determinismo
│   ├── calibration.py     # Temperature Scaling, optimización de umbrales Bayesianos, ECE/MCE y Brier Skill Score
│   ├── evaluate.py        # Evaluación multiclase completa y diagnósticos por clase/decil
│   ├── train.py           # Pipeline CLI reproducible con persistencia atómica en models/
│   └── api.py             # API REST FastAPI con CORS, Pydantic v2 y precarga en lifespan
├── prediction_service.py  # Fachada retrocompatible (EPLPredictor / predecir_partido) con caché singleton
├── models/
│   ├── best_deep_mlp.keras
│   ├── preprocessor.pkl
│   ├── scaler.pkl
│   ├── feature_names.json
│   ├── calibration.json
│   └── training_summary.json
├── tests/                 # Suite de 33 pruebas unitarias, integración y bordes (data, features, calibration, service, api)
├── datasets/              # Fuentes históricas tabulares EPL (2000–2026)
└── requirements.txt       # Dependencias exactas fijadas
```

---

## Mejoras Clave Implementadas respecto al Hito 2

1. **Consolidación de datos sin huecos (`src/data.py`):** Se corrigen los 120 partidos faltantes en `epl_final.csv` usando `PremierLeague.csv` como base completa (`2000/01–2024/25`: 25 temporadas × 380 partidos = **9,500 partidos**), más **400 partidos prospectivos** de `Matches.csv (E0)` (`2025/26`: 380 partidos + inicio `2026/27`: 20) y ratings Elo causales desde `EloRatings.csv` (`0` nulos).
2. **Cero fuga de información y paridad exacta (`src/features.py`):**
   - Imputaciones de Elo, fallback Elo→Mercado (`LogisticRegression`) y `StandardScaler` viven dentro de `CausalPreprocessor`, ajustado **exclusivamente** sobre `Train` (`2000/01–2016/17`, 6,460 partidos).
   - Se eliminó la redundancia `Form5 == 5 * RollingPts5` ($r = 0.98$) y se añadieron forma por sede (`VenuePts5`, `VenueGD5`), entropía/margen del mercado y H2H suavizado por Dirichlet (**45 características**).
   - Corregido el bug de arrastre de `SeasonPts`/`SeasonGD` en Jornada 1, el lag de 1 partido en Elo/Form y el rechazo de nombres en minúsculas.
3. **Arquitectura y calibración real (`src/models.py`, `src/calibration.py`):**
   - Selección estricta sobre `Val` (`2017/18–2020/21`, 1,520 partidos): **`Residual_Deep_MLP_3L`** (6,189 parámetros).
   - **Temperature Scaling** ajustado en `Val` ($T = 1.1723$).
   - **Umbrales Bayesianos** ($w = [1.0, 1.49, 1.08]$) optimizados en `Val` con restricción de exactitud (`min_accuracy_ratio=0.98`).

---

## Resultados Verificados y Reproducibles (`models/training_summary.json`)

### Conjunto de Prueba (`2021/22–2024/25`, $n = 1,520$)

| Modelo | Accuracy | Macro F1 | F1 Empate (`D`) | Log Loss | Brier Score | BSS | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dummy (Prior/Mayoría) | 44.54% | 20.54% | 0.00% | 1.0687 | 0.6465 | 0.0000 | 0.0195 |
| Bet365 (Cuotas Implícitas) | 56.91% | 42.18% | 0.00% | 0.9458 | 0.5598 | +0.1340 | 0.0306 |
| Regresión Logística (`C=0.01`) | 56.91% | 42.80% | 2.23% | 0.9495 | 0.5621 | +0.1304 | 0.0328 |
| HistGradientBoosting (Tuned Val) | 56.51% | 42.21% | 1.11% | 0.9541 | 0.5645 | +0.1268 | 0.0240 |
| Deep MLP Hito 2 (`128-64-32-16`) | 55.72% | 41.62% | 0.56% | 0.9569 | 0.5674 | +0.1223 | 0.0248 |
| **Residual Deep MLP 3L (`argmax`, Cal. $T=1.172$)** | **56.71%** | **45.47%** | **10.92%** | **0.9516** | **0.5631** | **+0.1289** | 0.0312 |
| **Residual Deep MLP 3L (Umbral Bayesiano)** | 52.11% | **48.39%** | **27.53%** | **0.9516** | **0.5631** | **+0.1289** | 0.0312 |
| Ablación Sin Cuotas (40 vars deportivas) | 54.74% | 41.78% | 3.74% | 0.9726 | 0.5770 | +0.1074 | 0.0275 |

### Conjunto Prospectivo Out-of-Time (`2025/26`, $n = 380$ nunca vistos)

| Modelo | Accuracy | Macro F1 | F1 Empate (`D`) | Log Loss | Brier Score | ECE |
|---|---:|---:|---:|---:|---:|---:|
| Dummy (Prior/Mayoría) | 42.63% | 19.93% | 0.00% | 1.0823 | 0.6556 | 0.0385 |
| Bet365 (Cuotas Implícitas) | 48.95% | 36.52% | 0.00% | 1.0185 | 0.6115 | 0.0490 |
| Regresión Logística (`C=0.01`) | 48.42% | 35.84% | 0.00% | 1.0383 | 0.6236 | 0.0665 |
| HistGradientBoosting (Tuned Val) | 46.84% | 36.00% | 3.54% | 1.0386 | 0.6233 | 0.0581 |
| **Residual Deep MLP 3L (`argmax`, Cal. $T=1.172$)** | 46.84% | **37.20%** | **6.61%** | **1.0326** | **0.6192** | **0.0500** |
| **Residual Deep MLP 3L (Umbral Bayesiano)** | 46.32% | **43.04%** | **25.91%** | **1.0326** | **0.6192** | **0.0500** |

---

## Comandos de Uso

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Reentrenar y regenerar artefactos en `models/`
> **Nota de compatibilidad:** No ejecutar la celda de entrenamiento del notebook heredado (`Proyecto_Red_Neuronal_Profunda_EPL.ipynb`, configurado con 40 características) para evitar sobrescribir `models/best_deep_mlp.keras` (45 características). El servicio valida esta compatibilidad automáticamente al arrancar.
```bash
python -m src.train
```

### 3. Ejecutar servicio CLI de predicción
```bash
python prediction_service.py
```

### 4. Levantar API REST (FastAPI)
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```
Endpoints disponibles (documentación interactiva en `/docs`, orígenes CORS configurables vía `CORS_ALLOW_ORIGINS`):
- `GET /health` — Estado del servicio, versión, conteo de features y última fecha histórica.
- `GET /teams` — Catálogo de clubes EPL reconocidos.
- `GET /teams/{team_name}/stats?match_date=YYYY-MM-DD&venue=home|away` — Estadísticas pre-partido causales (acepta ISO-8601 con zona horaria).
- `POST /predict` — Predicción probabilística individual (`argmax` / `bayesian`, cuotas acotadas `(1.0, 1000]`, debutantes soportados y `top_factors`).
- `POST /predict/batch` — Predicción vectorizada por lote (1 a 50 partidos, con reporte de `match_index` ante errores).
- `GET /model/metrics?include_bins=false` — Ledger de métricas (`Val`, `Test`, `Prospective 2025/26`, calibración y matrices; usar `include_bins=true` para bins completos de confiabilidad).

### 5. Ejecutar suite completa de pruebas
```bash
python -m unittest discover -s tests -v
```

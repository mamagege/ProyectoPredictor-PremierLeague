# AUDITORÍA TÉCNICA INDEPENDIENTE Y VALIDACIÓN DE CUMPLIMIENTO DEL BACKEND — HITO 3
## Sistema Predictor de Resultados en Partidos de Fútbol (PTIA, Grupo 04)

**Rama auditada:** `feat/hito3-backend` (commit `e6136f6`)  
**Rama base de comparación (Hito 2):** `main` (commit `fe7ebab`)  
**Modalidad:** Auditoría de solo lectura (sin modificaciones al código, datasets, modelos ni dependencias).  
**Fecha de auditoría:** 22 de noviembre de 2026.

---

## 1. Resumen ejecutivo

Se ejecutó una auditoría técnica independiente y de aceptación sobre el Backend del **Sistema Predictor de Resultados en Partidos de Fútbol (English Premier League — EPL)** desarrollado en la rama `feat/hito3-backend` (commit `e6136f6`). El análisis incluyó revisión directa del árbol completo de archivos, contraste entre `main` y `feat/hito3-backend`, inspección estática de los 10 módulos Python del backend, verificación de los artefactos serializados en `models/`, ejecución íntegra de la suite de 26 pruebas existentes y ejecución de 18 pruebas adversariales adicionales de bordes, contratos, latencia y regresiones.

### Conclusiones principales
1. **Bloqueo por ausencia de especificación oficial del Hito 3:** No existe en el repositorio ni en el workspace ningún documento oficial del Hito 3 (enunciado, guía del curso, rúbrica de evaluación ni retroalimentación escrita del Hito 2). Por rigor metodológico y jerarquía de fuentes, los 3 requisitos normativos propios del Hito 3 quedan en estado **`BLOQUEADO`** y el veredicto de aceptación oficial es **`NO CONCLUYENTE`**.
2. **Progreso técnico real en `feat/hito3-backend`:** La refactorización resolvió problemas críticos heredados del Hito 2: consolidó 9,900 partidos sin huecos (`2000–2026`), eliminó la fuga en imputaciones globales, garantizó paridad matemática exacta (`atol=1e-9`) entre entrenamiento e inferencia mediante `FeatureStateEngine` y `CausalPreprocessor`, reemplazó los artefactos huérfanos por persistencia atómica sincronizada (`diff = 0.0` frente a `models/training_summary.json`), introdujo calibración por `Temperature Scaling` (`T = 1.172273`) y umbrales Bayesianos (`[1.0, 1.49, 1.08]`), expuso una API REST en FastAPI (`src/api.py`) y pasó sus 26 pruebas unitarias/integración (`20.549 s`).
3. **Defectos técnicos comprobados que impiden un aprobado técnico aun sin guía oficial:** Al someter el backend a pruebas adversariales fuera de la suite optimista de los desarrolladores, **se demostraron fallos reales**:
   - **`HAL-02` (ALTA):** Fechas ISO-8601 con zona horaria (ej. `"2024-04-23T15:00:00Z"`, estándar en frontends JS) provocan un `TypeError` no controlado en `prediction_service.py:201-210` y devuelven **`HTTP 500 Internal Server Error`** en `POST /predict` y `GET /teams/{team_name}/stats`.
   - **`HAL-03` (ALTA):** `src/data.py:29-38` corrompe silenciosamente todos los **41 registros de Elo de `Nott'm Forest`** entre `2025-01-01` y `2026-09-01`, dejándolos congelados en **`1731.5`** en lugar de los valores reales `1758.31`–`1792.37` (a causa de `drop_duplicates(subset=["club", "date"], keep="last")` tras normalizar `"Nottm Forest"`).
   - **`HAL-04` (ALTA):** Regresiones de contrato en `prediction_service.py` respecto a `main` (eliminación de `get_latest_team_stats`, `get_h2h_stats`, `TEAM_ALIASES`, atributos `epl/matches/matches_e0/prem` y claves `Forma5_Local`/`Forma5_Visitante`) e incompatibilidad destructiva latente con `Proyecto_Red_Neuronal_Profunda_EPL.ipynb` (40 vs. 45 características).
   - **Otros defectos y observaciones:** latencia de `347.0 ms` por `/predict` y **`16,726.6 ms` (~16.7 s)** por lote de 50 partidos (`HAL-05`), fuga menor de fechas en `season_bounds` (`HAL-06`), bloqueo `HTTP 404` a clubes debutantes como `Brentford` el `2021-08-13` (`HAL-07`), brecha pendiente del modelo en Test frente a Regresión Logística y Bet365 (`HAL-08`), ausencia total de `logging` estructurado (`HAL-09`) y endurecimiento pendiente de API/CORS/concurrencia (`HAL-10`).

---

## 2. Documentos oficiales analizados

| Documento / Fuente | Ubicación | Naturaleza | Hallazgos documentales relevantes |
|---|---|---|---|
| Informe oficial del Hito 2 | [Hito2Proyecto.pdf](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/Hito2Proyecto.pdf) (14 págs.) | Entregable académico previo (Grupo 04, 09-oct-2026) | Define problema multiclase 1X2 prepartido en EPL (pese a errata `"Fútbol Español"` en portada pág. 1), causalidad temporal estricta, zero data leakage, calibración probabilística, servicio modular `prediction_service.py`, Deep MLP Softmax y objetivos cuantitativos (superar Dummy y modelos de referencia, Log Loss `< 1.00`, Brier `< 0.60`, sensibilidad al empate). |
| Documentación técnica del backend | [README.md](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/README.md) (125 líneas) | Documentación técnica en `feat/hito3-backend` | Documenta arquitectura `src/`, flujo de comandos (`train`, `prediction_service.py`, `uvicorn src.api:app`, `unittest`), endpoints de FastAPI y tablas de resultados en Val, Test y Prospectivo `2025/26`. |
| Guía oficial / Rúbrica del Hito 3 | **NO DISPONIBLE** | Requisito normativo faltante | Ausente en la raíz, subdirectorios, historial Git y metadatos del workspace. |
| Retroalimentación docente del Hito 2 | **NO DISPONIBLE** | Requisito normativo faltante | No existe archivo de comentarios o correcciones solicitadas para el Hito 3. |

> **Regla de jerarquía aplicada:** Al no existir documento oficial del Hito 3 ni retroalimentación escrita del Hito 2, `Hito2Proyecto.pdf` constituye la única fuente académica oficial vigente para validar continuidad, restricciones metodológicas y no regresión, mientras que `README.md` y el código en `feat/hito3-backend` describen lo implementado por el equipo. No se convierten las recomendaciones de ingeniería en obligaciones académicas inventadas.

---

## 3. Alcance exacto del Backend en el Hito 3

Con base en `Hito2Proyecto.pdf`, la evolución observada entre `main` (`fe7ebab`) y `feat/hito3-backend` (`e6136f6`), y la arquitectura del repositorio:

### Dentro del alcance del Backend (auditado)
1. **Ingesta y consolidación histórica de datos (`src/data.py`):** carga, normalización de clubes y fechas, cruce de fuentes CSV (`PremierLeague.csv`, `Matches.csv`, `EloRatings.csv`) y búsqueda Elo causal.
2. **Ingeniería de características y preprocesamiento causal (`src/features.py`):** cálculo prepartido de variables sin fuga temporal, ajuste exclusivo en entrenamiento (`CausalPreprocessor`) y transformación idéntica en entrenamiento e inferencia.
3. **Modelado, calibración y evaluación (`src/models.py`, `src/calibration.py`, `src/evaluate.py`, `src/train.py`):** definición y entrenamiento reproducible de redes neuronales Keras y baselines, ajuste de `Temperature Scaling` y umbrales Bayesianos en validación, métricas de clasificación y calibración, y serialización atómica en `models/`.
4. **Servicio de inferencia (`prediction_service.py`):** clase `EPLPredictor`, función retrocompatible `predecir_partido`, caché singleton y validación de entradas.
5. **Capa de exposición HTTP / API REST (`src/api.py`):** endpoints FastAPI (`/health`, `/teams`, `/teams/{team_name}/stats`, `/predict`, `/predict/batch`, `/model/metrics`), esquemas Pydantic v2, CORS y códigos HTTP.
6. **Dependencias y pruebas automatizadas (`requirements.txt`, `tests/`):** reproducibilidad del entorno y verificación automática.

### Fuera del alcance del Backend (excluido por alcance explícito)
- Interfaz gráfica / Frontend web o móvil (no existe en el repositorio y fue expresamente excluido del encargo de backend).
- Actualización editorial de `Hito2Proyecto.pdf` o refactorización del notebook exploratorio `Proyecto_Red_Neuronal_Profunda_EPL.ipynb` (salvo verificar compatibilidad y riesgos de regresión sobre artefactos compartidos).

---

## 4. Matriz maestra de requisitos

### 4.1. Requisitos oficiales normativos del Hito 3 (Faltantes en el repositorio)

| ID | Requisito oficial | Fuente | Descripción | Obligatoriedad | Criterio de aceptación |
|---|---|---|---|---|---|
| **REQ-H3-01** | Especificación funcional oficial del Backend para el Hito 3 | Guía oficial del Hito 3 *(ausente)* | Lista oficial de funcionalidades backend exigidas para el tercer hito (ej. API, despliegue, explicabilidad, interfaz de consumo). | Obligatoria *(no verificable)* | Definido en guía oficial del Hito 3 *(no disponible)*. |
| **REQ-H3-02** | Rúbrica y umbrales de evaluación del Hito 3 | Rúbrica oficial del curso PTIA *(ausente)* | Criterios de calificación, ponderaciones y entregables mínimos para nota máxima. | Obligatoria *(no verificable)* | Definido en rúbrica del Hito 3 *(no disponible)*. |
| **REQ-H3-03** | Atención a observaciones docentes del Hito 2 | Retroalimentación oficial del Hito 2 *(ausente)* | Correcciones técnicas o metodológicas solicitadas tras la sustentación del Hito 2. | Obligatoria *(no verificable)* | Evidencia de cierre de observaciones del profesor *(no disponible)*. |

### 4.2. Requisitos técnicos y metodológicos del Backend (trazables a Hito 2 y arquitectura implementada)

| ID | Requisito técnico / compromiso | Fuente | Descripción | Obligatoriedad | Criterio de aceptación |
|---|---|---|---|---|---|
| **REQ-BK-01** | Ingesta y consolidación íntegra de datos EPL | `Hito2Proyecto.pdf` pág. 9; `README.md` | Integrar las fuentes tabulares EPL sin duplicados, con fechas válidas, nombres normalizados y ratings Elo íntegros sin corrupción. | Obligatoria | 0 duplicados por `(MatchDate, HomeTeam, AwayTeam)`, 25 temporadas completas de 380 partidos + prospectivo `2025/26`, 0 nulos de Elo y fidelidad exacta de ratings frente a `EloRatings.csv` / `Matches.csv`. |
| **REQ-BK-02** | Ingeniería de características causal y paridad entrenamiento/inferencia | `Hito2Proyecto.pdf` págs. 5–9; `README.md` | Generar variables estrictamente prepartido (`MatchDate < target_date`) con idéntica fórmula en entrenamiento e inferencia. | Obligatoria | Diferencia `<= 1e-9` entre batch y servicio puntual en partidos históricos/Jornada 1; cero fuga de información futura en construcción de features y temporadas. |
| **REQ-BK-03** | Partición temporal estricta y aislamiento del escalador | `Hito2Proyecto.pdf` págs. 6–9 | Separar cronológicamente Train/Val/Test (y prospectivo) y ajustar imputadores/escalador exclusivamente en Train. | Obligatoria | `scaler.n_samples_seen_ == n_train`; alterar registros de Val/Test no cambia `mean_`, `scale_` ni priors. |
| **REQ-BK-04** | Modelo neuronal multiclase Softmax entrenado y reproducible | `Hito2Proyecto.pdf` págs. 6, 8, 10 | Entrenar Deep MLP con salida de 3 probabilidades sumando 1.0 y ejecución determinista verificable. | Obligatoria | Modelo `.keras` carga sin error, recibe `(None, d)`, retorna `(None, 3)` finitas con suma 1.0 y reproduce exactamente `training_summary.json`. |
| **REQ-BK-05** | Desempeño competitivo frente a baselines de referencia | `Hito2Proyecto.pdf` pág. 6 | Superar Dummy (`Log Loss < 1.00`, `Brier < 0.60`) y superar los modelos de referencia en exactitud y fiabilidad probabilística. | Obligatoria (según compromiso Hito 2) | Superar Dummy, Regresión Logística, HistGradientBoosting y cuotas implícitas Bet365 en Test/Prospectivo, o documentar honestamente el alcance real sin contradicciones. |
| **REQ-BK-06** | Calibración probabilística y sensibilidad al empate | `Hito2Proyecto.pdf` pág. 6; `README.md` | Probabilidades calibradas (`ECE`, `Brier`, `Log Loss`) y superación del colapso `F1-D = 0.00` mediante calibración Bayesiana ajustada en Val. | Obligatoria | `Temperature Scaling` y pesos Bayesianos ajustados solo en `Val`; mejora verificada de `F1-D` y `Macro-F1` en `Test` y `2025/26`. |
| **REQ-BK-07** | Servicio predictivo Python confiable (`prediction_service.py`) | `Hito2Proyecto.pdf` págs. 6, 9; `README.md` | Exponer `EPLPredictor` y `predecir_partido` con caché, validación de equipos/fechas/cuotas, cálculo causal y manejo seguro de errores. | Obligatoria | Maneja alias, minúsculas, fechas ISO válidas/inválidas, cuotas válidas/inválidas y debutantes sin excepciones no controladas. |
| **REQ-BK-08** | API REST FastAPI con contratos y errores HTTP semánticos | `src/api.py`; `README.md` | Exponer endpoints `/health`, `/teams`, `/teams/{name}/stats`, `/predict`, `/predict/batch`, `/model/metrics` con validación Pydantic y respuestas HTTP coherentes. | Obligatoria (alcance backend Hito 3) | Códigos `200`/`400`/`404`/`422` consistentes; nunca `500` ante entradas de cliente; esquema OpenAPI válido. |
| **REQ-BK-09** | Rendimiento y latencia operativa del servicio y API | Estándar Backend / `src/api.py` batch hasta 50 | Responder inferencias puntuales y lotes de hasta 50 partidos en tiempos interactivos sin recomputar historiales completos innecesariamente. | Opcional / Recomendación técnica | Inferencia puntual en decenas de milisegundos y lote de 50 partidos en tiempo sub-segundo o acotado sin bloqueo severo. |
| **REQ-BK-10** | Persistencia atómica y sincronización de artefactos | `src/train.py`; `models/` | Persistir modelo, preprocesador, escalador, nombres de features, calibración y métricas sincronizados sin huérfanos. | Obligatoria | Todos los archivos en `models/` pertenecen a la misma corrida y sus hashes/métricas coinciden exactamente. |
| **REQ-BK-11** | Gestión reproducible de dependencias | `requirements.txt` | Declarar versiones exactas compatibles con el entorno de ejecución. | Obligatoria | `requirements.txt` coincide con versiones instaladas y probadas. |
| **REQ-BK-12** | Estrategia de pruebas automatizadas y cobertura de bordes | `tests/` | Validar unidad, integración, causalidad, calibración, servicio y API sin falsos positivos. | Obligatoria | Pruebas cubren casos nominales, de borde, regresiones y errores con ejecución reproducible. |
| **REQ-BK-13** | Ausencia de regresiones respecto al Hito 2 (`main`) | Regla de continuidad (`main` -> `feat/hito3-backend`) | Conservar compatibilidad de contratos públicos previos y no romper artefactos usados por entregables existentes. | Obligatoria | Firmas, claves de respuesta previas y compatibilidad con `Proyecto_Red_Neuronal_Profunda_EPL.ipynb` preservadas o documentadas con adaptadores. |

---

## 5. Arquitectura Backend encontrada

### 5.1. Evolución comprobada en Git (`main` vs `feat/hito3-backend`)
- **`main` (pre-Hito 3, commit `fe7ebab`):** Contenía únicamente un script plano `prediction_service.py` (415 líneas), el notebook monolítico `Proyecto_Red_Neuronal_Profunda_EPL.ipynb`, 6 CSVs en `datasets/`, artefactos desincronizados en `models/` (incluidos los huérfanos `deep_mlp_3layers.keras` y `deep_mlp_4layers.keras`), `Hito2Proyecto.pdf` y `README.md`.
- **`feat/hito3-backend` (commit `e6136f6`):** Modificó/agregó 26 archivos (`+13,297 / -498` líneas), introduciendo el paquete `src/` (8 módulos), `tests/` (6 archivos), `requirements.txt`, `models/preprocessor.pkl`, `models/calibration.json`, eliminando los 2 modelos `.keras` huérfanos y reescribiendo `prediction_service.py`, `README.md` y los artefactos en `models/`.

### 5.2. Mapa real de componentes del Backend

```text
Datasets CSV (datasets/)
  ├── PremierLeague.csv ──┐
  ├── Matches.csv (E0) ───┼──► src/data.py (load_unified_matches, EloLookup)
  └── EloRatings.csv ─────┘         │
                                    ▼
                           src/features.py (FeatureStateEngine, CausalPreprocessor [45 features])
                                    │
          ┌─────────────────────────┴──────────────────────────┐
          ▼                                                    ▼
   src/train.py                                      prediction_service.py
   ├── src/models.py (4 arquitecturas Keras)         ├── EPLPredictor (singleton get_predictor)
   ├── src/calibration.py (T-Scaling + Bayes)        ├── predecir_partido(...)
   ├── src/evaluate.py (Acc, LL, Brier, ECE, F1)     └── carga models/* + datasets/*
   └── Persistencia atómica -> models/*                        │
                                                               ▼
                                                     src/api.py (FastAPI + Pydantic v2)
                                                     ├── GET  /health
                                                     ├── GET  /teams
                                                     ├── GET  /teams/{team_name}/stats
                                                     ├── POST /predict
                                                     ├── POST /predict/batch
                                                     └── GET  /model/metrics
```

| Componente | Archivo | Responsabilidad real | Estado Hito 2 vs Hito 3 |
|---|---|---|---|
| Configuración | [src/config.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/config.py) (185 líneas) | Rutas portables, `SEED=42`, splits temporales, `TEAM_ALIASES` y normalización de equipos/temporadas. | Nuevo (Hito 3) |
| Datos | [src/data.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/data.py) (189 líneas) | Unificación de 9,900 partidos (`2000–2026`) y búsqueda `EloLookup`. | Nuevo (Hito 3) |
| Features y preproc. | [src/features.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py) (606 líneas) | Motor único de 45 variables prepartido y `CausalPreprocessor` con fallback Elo→Mercado. | Nuevo (Hito 3) |
| Modelos | [src/models.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/models.py) (112 líneas) | Determinismo y arquitecturas Keras (`Deep_MLP_Hito2`, `Compact_Deep_MLP`, `Residual_Deep_MLP`). | Nuevo (Hito 3) |
| Calibración | [src/calibration.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/calibration.py) (235 líneas) | `Temperature Scaling`, pesos Bayesianos, `ECE`/`MCE` y `Brier Skill Score`. | Nuevo (Hito 3) |
| Evaluación | [src/evaluate.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/evaluate.py) (112 líneas) | Evaluación integral por split y modo Bayesiano. | Nuevo (Hito 3) |
| Entrenamiento | [src/train.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py) (514 líneas) | Orquestación CLI reproducible, tuning en Val, ablación sin cuotas y guardado atómico. | Nuevo (Hito 3) |
| Servicio Python | [prediction_service.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py) (471 líneas) | Fachada de inferencia con caché singleton, validación y `top_factors`. | Reescrito (Hito 2 -> Hito 3) |
| API HTTP | [src/api.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py) (185 líneas) | Servicio REST FastAPI con precarga en `lifespan` y CORS abierto. | Nuevo (Hito 3) |
| Artefactos | `models/` (6 archivos) | Modelo Keras `Residual_Deep_MLP_3L` (6,189 params), `preprocessor.pkl`, `scaler.pkl`, `feature_names.json`, `calibration.json`, `training_summary.json`. | Regenerado (Hito 3) |

---

## 6. Auditoría individual de cada requisito

### REQ-H3-01, REQ-H3-02 y REQ-H3-03 — Requisitos oficiales del Hito 3
- **Estado:** **`BLOQUEADO`** (los 3 requisitos).
- **Evidencia:** Búsqueda completa en todo el repositorio, árbol de directorios y commits de Git. No existen guías, rúbricas ni comentarios del Hito 2. No es posible validar si el Backend cumple con entregables específicos exigidos por el docente (p. ej., contenedorización Docker, persistencia en base de datos, autenticación, interfaz web específica, etc.).

### REQ-BK-01 — Ingesta y consolidación íntegra de datos EPL
- **Estado:** **`DEFECTUOSO`**
- **Implementación:** [src/data.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/data.py#L21-L189).
- **Lo positivo verificado:** Consolida exactamente 9,500 partidos de `PremierLeague.csv` (`2000/01–2024/25`, 25 temporadas × 380 exactos) más 400 de `Matches.csv` (`2025/26`: 380; `2026/27`: 20), con 0 duplicados y 0 nulos de Elo.
- **Defecto demostrado (`HAL-03`):** En [src/data.py:29-38](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/data.py#L29-L38), `load_elo_ratings()` normaliza `"Nottm Forest"` → `"Nott'm Forest"` en la línea 30 **antes** de ordenar por `["club", "date"]` y aplicar `.drop_duplicates(subset=["club", "date"], keep="last")` en la línea 35. En el archivo crudo `EloRatings.csv`, coexisten **dos series para Nottingham Forest**:
  - `"Nottm Forest"` (`547` filas, `2000-07-01` a `2026-09-01`), cuyo valor queda congelado en **`1731.5`** desde `2025-01-01` hasta `2026-09-01`.
  - `"Nott'm Forest"` (`41` filas, `2025-01-01` a `2026-09-01`), que contiene los ratings reales actualizados (`1758.31`–`1792.37`).
  Al reemplazar el nombre antes de deduplicar y estar `"Nottm Forest"` después de `"Nott'm Forest"` en el CSV, `keep="last"` **elimina sistemáticamente los 41 ratings reales y conserva los congelados a `1731.5`**. Esto se comprobó tanto en `Matches.csv` (`2025-11-01: 1758.31 vs 1731.5`, `2026-02-01: 1781.43 vs 1731.5`, `2026-03-15: 1759.01 vs 1731.5`) como en `GET /teams/Nott'm Forest/stats` (`"elo": 1731.5` al `2026-09-07`).

### REQ-BK-02 — Ingeniería de características causal y paridad entrenamiento/inferencia
- **Estado:** **`PARCIALMENTE CUMPLIDO`**
- **Implementación:** [src/features.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L1-L606), [prediction_service.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L325-L341).
- **Verificado:** Las pruebas de paridad `test_exact_batch_vs_single_inference_parity` y `test_season_stats_reset_on_matchday_one` pasan con `atol=1e-9` sobre 7 partidos variados (incluido Jornada 1 `2024-08-17` y julio `2020`).
- **Incumplimientos parciales encontrados:**
  1. **Fuga menor de rangos de temporada (`HAL-06`):** En [src/features.py:505-510](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L505-L510), `season_bounds = df_history.groupby("Season")["MatchDate"].agg(["min", "max"])` lee todo `df_history` sin filtrar `MatchDate < target_ts`, conociendo el rango completo de fin de temporada incluso si la fecha objetivo es anterior al último partido cargado.
  2. **Asimetría con debutantes (`HAL-07`):** En entrenamiento (`FeatureStateEngine.compute_batch_features`), un equipo en su debut EPL (ej. `Brentford` el `2021-08-13`) recibe defaults neutros (`1.3`, `11.5`, `4.2`, `7.0`) y se entrena/evalúa normalmente; sin embargo, `prediction_service.py:334-339` rechaza con `HTTP 404` (`insufficient_history`) cualquier consulta donde `home_history_matches == 0` o `away_history_matches == 0`.

### REQ-BK-03 — Partición temporal estricta y aislamiento del escalador
- **Estado:** **`CUMPLIDO Y VERIFICADO`**
- **Implementación:** [src/config.py:42-53](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/config.py#L42-L53), [src/features.py:109-143](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L109-L143), [src/train.py:173-199](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py#L173-L199).
- **Evidencia:** Partición estricta `Train: 6,460 (2000/01–2016/17)`, `Val: 1,520 (2017/18–2020/21)`, `Test: 1,520 (2021/22–2024/25)`, `Prospectivo: 380 (2025/26)`. Inspección directa de `models/scaler.pkl` confirma `n_features_in_ = 45` y `n_samples_seen_ = 6460.0`. `test_zero_leakage_in_preprocessor` corrompe Val/Test (`HomeElo=9999.0`, `Odds_H=1.05`) y demuestra invariancia exacta (`atol=1e-12`).

### REQ-BK-04 — Modelo neuronal multiclase Softmax entrenado y reproducible
- **Estado:** **`CUMPLIDO Y VERIFICADO`**
- **Implementación:** [src/models.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/models.py#L16-L112), [src/train.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py#L81-L135).
- **Evidencia:** `models/best_deep_mlp.keras` (`142,227` bytes) carga limpio como `Residual_Deep_MLP_3L` con `input=(None, 45)`, `output=(None, 3)` (`Output_Softmax`), `6,189` parámetros. La reevaluación independiente sobre `Test` frente a `models/training_summary.json` arrojó diferencia **`0.0`** en Accuracy (`0.567105`), Log Loss (`0.9516xx`), Brier Score (`0.5631xx`) y F1-D Bayesiano (`0.275281`).

### REQ-BK-05 — Desempeño del modelo neuronal superando a los modelos de referencia
- **Estado:** **`PARCIALMENTE CUMPLIDO`**
- **Evidencia contrastada en [models/training_summary.json](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/models/training_summary.json):**
  - En **Test (`2021/22–2024/25`, $n=1,520$):** `Residual_Deep_MLP_3L (Calibrado T=1.172)` logra `Acc=56.71%`, `Log Loss=0.9516`, `Brier=0.5631`, `Macro-F1=45.47%`, superando a **Dummy** (`44.54%`, `1.0687`, `0.6465`), **Deep MLP Hito 2** (`55.72%`, `0.9569`, `0.5674`) e **HistGradientBoosting** (`56.51%`, `0.9541`, `0.5645`). **Sin embargo, NO supera** en exactitud ni Log Loss/Brier a **Regresión Logística `C=0.01`** (`Acc=56.91%`, `LL=0.9495`, `Brier=0.5621`) ni a **Bet365 implícito** (`Acc=56.91%`, `LL=0.9458`, `Brier=0.5598`).
  - En **Prospectivo (`2025/26`, $n=380$):** `Residual_Deep_MLP_3L` (`LL=1.0317`, `Brier=0.6187`, `ECE=0.0501`) supera a **Regresión Logística** (`LL=1.0376`, `Brier=0.6231`, `ECE=0.0745`) e **HistGradientBoosting** (`LL=1.0388`, `Brier=0.6234`, `ECE=0.0583`) en calibración y error probabilístico, aunque queda por debajo de **Bet365** (`Acc=48.95%` vs `46.84%`, `LL=1.0185`) y de Regresión Logística en `Accuracy` (`48.68%` vs `46.84%`).
  - Además, `Hito2Proyecto.pdf` (pág. 6 y 10) sigue declarando `40` características y arquitectura `128-64-32-16`, mientras el modelo actual usa `45` características y arquitectura `Residual_Deep_MLP_3L` (`64-32-16` + skip lineal).

### REQ-BK-06 — Calibración probabilística y sensibilidad al empate
- **Estado:** **`CUMPLIDO Y VERIFICADO`**
- **Implementación:** [src/calibration.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/calibration.py#L14-L235), [src/evaluate.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/evaluate.py#L24-L112).
- **Evidencia:** `Temperature Scaling` (`T = 1.172273`) y multiplicadores Bayesianos (`[1.0, 1.49, 1.08]`) ajustados estrictamente sobre `Val`. Reduce `Log Loss` en `Val` (`0.9579 -> 0.9544`), `Test` (`0.9525 -> 0.9516`) y `2025/26` (`1.0405 -> 1.0317`), reduciendo `ECE` en `2025/26` de `0.0825` a `0.0501`. Con decisión Bayesiana, `F1-D` sube a **`27.53%`** en Test (`Macro-F1 = 48.39%`, el mayor del benchmark) y **`26.67%`** en `2025/26` (`Macro-F1 = 42.93%`). *(Nota técnica menor: en Test el `top_label_ece` pasa de `0.0282` a `0.0312` tras `T=1.172`, aunque mejora `Log Loss` y `Brier Score`).*

### REQ-BK-07 — Servicio predictivo Python confiable (`prediction_service.py`)
- **Estado:** **`DEFECTUOSO`**
- **Implementación:** [prediction_service.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L75-L457).
- **Defectos comprobados:**
  1. **`TypeError` no capturado (`HAL-02`):** `_parse_date("2024-04-23T15:00:00Z")` (líneas 201–210) retorna un `Timestamp` con zona horaria `UTC`, porque `.normalize()` conserva `tz=UTC`. Luego `FeatureStateEngine.compute_single_match_features` compara `df_history["MatchDate"] < target_ts` (`datetime64[ns]` naive vs `Timestamp` tz-aware), lanzando `TypeError: Invalid comparison between dtype=datetime64[ns] and Timestamp`.
  2. **Bloqueo de debutantes (`HAL-07`):** Rechaza partidos de debut EPL (`Brentford`, `2021-08-13`) con `insufficient_history`.
  3. **Regresión de contrato Hito 2 (`HAL-04`):** Eliminó métodos y claves existentes en `main`.
  4. **Elo corrupto para `Nott'm Forest` (`HAL-03`):** Heredado de `src/data.py`.

### REQ-BK-08 — API REST FastAPI (`src/api.py`) con contratos, validaciones y manejo de errores HTTP
- **Estado:** **`DEFECTUOSO`**
- **Implementación:** [src/api.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py#L15-L185).
- **Defectos comprobados mediante `TestClient(app, raise_server_exceptions=False)`:**
  1. **`HTTP 500 Internal Server Error` (`HAL-02`):** `POST /predict` con `match_date="2024-04-23T15:00:00Z"` y `GET /teams/arsenal/stats?match_date=2024-04-23T15:00:00Z` fallan con `HTTP 500` porque `prediction_service.py` lanza `TypeError` y `src/api.py:128` solo captura `ValueError`.
  2. **Validación incompleta de cuotas extremas (`HAL-10`):** `OddsInput` solo exige `gt=1.0`, aceptando `1e308` (`HTTP 200`), lo que vuelve `1/odds` indistinguible de `0.0`.
  3. **Manejo rígido en `/predict/batch` (`HAL-10`):** Ante 1 partido inválido en un lote de `N`, aborta todo el lote sin indicar el índice del elemento fallido.

### REQ-BK-09 — Rendimiento y latencia operativa del servicio y API
- **Estado:** **`DEFECTUOSO`**
- **Evidencia medida directamente (`TestClient` sobre servidor precargado):**
  - `POST /predict` promedio (5 ejecuciones): **`347.0 ms`** por solicitud.
  - `POST /predict/batch` (50 partidos): **`16,726.6 ms`** (~16.73 segundos).
- **Causa en código:** En cada predicción individual, `FeatureStateEngine.compute_single_match_features` ([src/features.py:512-565](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L512-L565)) recorre los ~900 partidos históricos de cada equipo con `itertuples()` desde 2000 aunque solo necesita los últimos 5 partidos (`k=5`), la temporada vigente y los últimos 10 H2H; y `predict_batch` ([src/api.py:158-173](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py#L158-L173)) ejecuta 50 llamadas secuenciales a `model.predict()` en lugar de inferencia en lote.

### REQ-BK-10 — Persistencia atómica y sincronización de artefactos
- **Estado:** **`CUMPLIDO Y VERIFICADO`**
- **Implementación:** [src/train.py:45-78](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py#L45-L78), `models/`.
- **Evidencia:** Escritos mediante `tempfile.mkstemp` + `os.replace`. Se comprobó que `models/` contiene únicamente los 6 artefactos sincronizados (`best_deep_mlp.keras`, `calibration.json`, `feature_names.json`, `preprocessor.pkl`, `scaler.pkl`, `training_summary.json`), que `preprocessor.feature_names == feature_names.json`, que `scaler == preprocessor.scaler_`, y que los 2 modelos huérfanos anteriores fueron eliminados.

### REQ-BK-11 — Gestión reproducible de dependencias
- **Estado:** **`CUMPLIDO Y VERIFICADO`**
- **Implementación:** [requirements.txt](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/requirements.txt).
- **Evidencia:** Fija exactamente las 11 librerías y versiones presentes en el entorno (`numpy==2.3.5`, `pandas==2.3.3`, `scipy==1.17.1`, `scikit-learn==1.9.0`, `tensorflow==2.21.0`, `keras==3.15.1`, `joblib==1.5.3`, `fastapi==0.139.2`, `uvicorn==0.51.0`, `pydantic==2.12.0`, `httpx==0.28.1`).

### REQ-BK-12 — Suite de pruebas automatizadas y cobertura de bordes
- **Estado:** **`PARCIALMENTE CUMPLIDO`**
- **Implementación:** `tests/` (6 archivos, 26 pruebas).
- **Evidencia:** Las 26 pruebas existentes ejecutaron y pasaron en `20.549 s`. Sin embargo, dejaron sin cubrir fallos reales demostrados por esta auditoría: fechas ISO con zona horaria (`Z` / `+00:00`), frescura de Elo de `Nott'm Forest` en `2025–2026`, equipos debutantes, cotas superiores de cuotas, regresión de contrato Hito 2 y pruebas de latencia/concurrencia.

### REQ-BK-13 — Ausencia de regresiones frente al Hito 2 (`main`)
- **Estado:** **`DEFECTUOSO`**
- **Evidencia contrastada entre `main:prediction_service.py` y `feat/hito3-backend:prediction_service.py`:**
  1. Se eliminaron métodos y atributos públicos de `EPLPredictor`: `get_latest_team_stats`, `get_h2h_stats`, `TEAM_ALIASES`, `epl`, `matches`, `matches_e0`, `prem`.
  2. Se eliminaron las claves `Forma5_Local` y `Forma5_Visitante` dentro de `contexto_prepartido` en la respuesta JSON de `predict_match`.
  3. **Regresión latente con el notebook:** `Proyecto_Red_Neuronal_Profunda_EPL.ipynb` (Celdas 14, 18, 20 y 32) sigue intacto desde `main` con 40 características; si alguien ejecuta sus celdas hasta la 20, `ModelCheckpoint('models/best_deep_mlp.keras')` sobrescribirá el modelo de 45 características del backend con uno de 40 incompatibles con `preprocessor.pkl` y `feature_names.json`; además su Celda 32 espera el contrato de salida de `prediction_service.py`.

---

## 7. Validación funcional

- **Lógica de negocio:** Los cálculos de puntos, goles, tiros, forma de sede (`VenuePts5`, `VenueGD5`), días de descanso (`[1, 30]`), acumulados por temporada (con reseteo en Jornada 1 y manejo de temporada `2019/20` extendida a julio 2020) y H2H suavizado por Dirichlet coinciden exactamente entre entrenamiento e inferencia en los casos nominales probados. Sin embargo, los casos límite de **fechas con zona horaria** (`TypeError`) y **clubes debutantes** (`404`) rompen la robustez esperada, y los datos de Elo de **`Nott'm Forest`** posteriores a `2025-01-01` son incorrectos.
- **APIs y contratos:** Las 6 rutas FastAPI responden y exponen `/openapi.json` válido. Los errores Pydantic devuelven `422`, equipo desconocido `404` y equipo igual/fecha sin `T...Z` `400`. No obstante, las fechas ISO-UTC (`Z`) producen `500`, `OddsInput` permite `1e308` y `GET /model/metrics` devuelve sin filtrar `277,460 bytes` (incluyendo los 10 bins por clase de 3 splits).
- **Persistencia y datos:** No se usa base de datos transaccional sino archivos CSV estáticos + artefactos serializados en `models/` en memoria. La consistencia entre `scaler.pkl`, `preprocessor.pkl`, `feature_names.json`, `calibration.json`, `best_deep_mlp.keras` y `training_summary.json` es íntegra (`diff = 0.0`).
- **Integraciones:** No hay integraciones con servicios externos; la comunicación API → `prediction_service.py` → `src/` es local e interna.

---

## 8. Validación de Machine Learning relacionada con Backend

1. **Fuentes y características:** Las 3 fuentes usadas (`PremierLeague.csv`, `Matches.csv`, `EloRatings.csv`) generan 45 variables numéricas bien ordenadas y validadas como finitas (`np.all(np.isfinite(X_all))`). La eliminación de `Form5 == 5 * RollingPts5` corrigió la colinealidad del 97.98% del Hito 2. El fallo de deduplicación de `Nott'm Forest` en `EloRatings.csv` degrada las features `HomeElo`/`AwayElo`/`DiffElo`/`EloProb_Home` para ~60 partidos de `Nott'm Forest` en `2024/25–2026/27` y futuras predicciones de ese equipo.
2. **Entrenamiento y reproducibilidad:** `Residual_Deep_MLP_3L` (`6,189` params) se selecciona por `val_loss` en `Val` con determinismo activo (`SEED=42`). Se verificó carga sin errores y consistencia de versiones (`tensorflow 2.21.0`, `keras 3.15.1`, `scikit-learn 1.9.0`).
3. **Inferencia:** Genera 3 probabilidades Softmax válidas post-calibradas por `Temperature Scaling` (`T = 1.172273`) que suman `1.0` (`"100.0 %"`), maneja ausencia de cuotas mediante `LogisticRegression` Elo→Mercado ajustada en `Train`, y ofrece explicación direccional (`top_factors`) con semántica corregida para `ProbMarket_Draw`, `MarketEntropy` y `MarketFavMargin`.
4. **Evaluación y honestidad científica:** Todas las métricas reportadas en `README.md` coinciden exactamente con `models/training_summary.json` y con la reevaluación de `models/best_deep_mlp.keras` (`0.0` diferencia). No existe manipulación del conjunto `Test` ni del prospectivo `2025/26`.

---

## 9. Resultados de pruebas

### 9.1. Suite automatizada existente (ejecutada en esta auditoría)

| Prueba / Suite | Requisito relacionado | Resultado esperado | Resultado obtenido | Estado | Evidencia |
|---|---|---|---|---|---|
| `test_data.py` (7 pruebas) | `REQ-BK-01` | Integridad CSVs, 25 temporadas × 380, `2025/26` = 380, 0 nulos Elo, orden y `Nott'm Forest` | 7/7 `ok` | **Ejecutada y aprobada** *(no detecta congelamiento `1731.5`)* | `python -m unittest discover -s tests -v` (`Ran 26 tests in 20.549s`) |
| `test_features.py` (3 pruebas) | `REQ-BK-02`, `REQ-BK-03` | Paridad batch vs single (`atol=1e-9`), reseteo Jornada 1, cero fuga en `CausalPreprocessor` | 3/3 `ok` | **Ejecutada y aprobada** | `python -m unittest discover -s tests -v` |
| `test_calibration.py` (3 pruebas) | `REQ-BK-06` | `T-Scaling` mejora/preserva `log_loss`, suma `1.0`, `ECE` acotado, pesos Bayesianos mejoran `F1-D` | 3/3 `ok` | **Ejecutada y aprobada** | `python -m unittest discover -s tests -v` |
| `test_service.py` (8 pruebas) | `REQ-BK-07` | Singleton rápido, minúsculas/alias, Jornada 1, suma 100%, modo Bayesiano, errores básicos, `top_factors` | 8/8 `ok` | **Ejecutada y aprobada** | `python -m unittest discover -s tests -v` |
| `test_api.py` (5 pruebas) | `REQ-BK-08` | `/health`, `/teams`, `/teams/arsenal/stats`, `/predict`, `/predict/batch`, `/model/metrics`, `400/404/422` | 5/5 `ok` | **Ejecutada y aprobada** | `python -m unittest discover -s tests -v` |

### 9.2. Pruebas adversariales independientes ejecutadas por el auditor

| Escenario adversarial probado | Requisito relacionado | Resultado esperado | Resultado obtenido | Estado | Evidencia |
|---|---|---|---|---|---|
| `POST /predict` con `match_date="2024-04-23T15:00:00Z"` | `REQ-BK-07`, `REQ-BK-08` | `200` (o `400` controlado) | **`HTTP 500 Internal Server Error`** | **Ejecutada y FALLIDA** | `TestClient` (`task-146`) |
| `GET /teams/arsenal/stats?match_date=2024-04-23T15:00:00Z` | `REQ-BK-07`, `REQ-BK-08` | `200` (o `400` controlado) | **`HTTP 500 Internal Server Error`** | **Ejecutada y FALLIDA** | `TestClient` (`task-146`) |
| `EPLPredictor.predict_match` con `"2024-04-23T15:00:00Z"` | `REQ-BK-07` | Éxito o dict `status="error"` | **`TypeError` no capturado** | **Ejecutada y FALLIDA** | `task-146` (`[PY] tz->UNHANDLED TypeError`) |
| Frescura de Elo de `Nott'm Forest` en `2025–2026` | `REQ-BK-01` | Coincidir con `Matches.csv` (`1758.31`–`1792.37`) | Congelado en **`1731.5`** en 41 fechas | **Ejecutada y FALLIDA** | `GET /teams/Nott'm Forest/stats` + análisis CSV |
| Debut EPL `Brentford vs Arsenal` (`2021-08-13`) vía `/predict` | `REQ-BK-02`, `REQ-BK-07` | Predicción con priors neutros consistente con entrenamiento | **`HTTP 404`** (`insufficient_history`) | **Ejecutada y FALLIDA** | `TestClient` (`task-146`) |
| Cuotas extremas `odds={"home": 1e308, "draw": 3.5, "away": 4.0}` | `REQ-BK-08` | Rechazo por cota absurda (`422`) | **`HTTP 200`** (aceptado como `bookmaker`) | **Ejecutada y FALLIDA** | `TestClient` (`task-146`) |
| `POST /predict` con `match_date=""`, `"   "`, `"2024-02-30"` | `REQ-BK-08` | `400 invalid_date` | `400 invalid_date` | **Ejecutada y aprobada** | `TestClient` (`task-146`) |
| `POST /predict` con `match_date="1995-01-01"` | `REQ-BK-08` | `404 insufficient_history` | `404 insufficient_history` | **Ejecutada y aprobada** | `TestClient` (`task-146`) |
| `POST /predict` con `odds=1.0`, `decision_mode="invalid"`, `home_team=true` | `REQ-BK-08` | `422` Pydantic | `422` en los 3 casos | **Ejecutada y aprobada** | `TestClient` (`task-146`) |
| `POST /predict/batch` con `0` o `51` partidos, y fallo parcial | `REQ-BK-08` | `422` en `0`/`51`; fallo controlado en parcial | `422` en `0`/`51`; `404` global en parcial | **Ejecutada (parcial observada)** | `TestClient` (`task-146`) |
| `GET /teams/Nott'm Forest/stats` y preflight `OPTIONS /predict` | `REQ-BK-08` | `200` + header CORS | `200`, `ACAO: *` | **Ejecutada y aprobada** | `TestClient` (`task-146`) |
| `predict_match` con `NaN`, `Inf`, `True` en `odds` | `REQ-BK-07` | `invalid_odds` | `invalid_odds` en los 3 casos | **Ejecutada y aprobada** | `task-146` (`[PY]`) |
| Regresión de contrato Python Hito 2 vs `main` | `REQ-BK-13` | Métodos/claves previas conservadas | Faltan 7 atributos/métodos y 2 claves JSON | **Ejecutada y FALLIDA** | `task-146` (`CONTRACT REGRESSION CHECK`) |
| Latencia `/predict` (media 5) y `/predict/batch` (50 partidos) | `REQ-BK-09` | Respuesta ágil en producción | **`347.0 ms`** (single), **`16,726.6 ms`** (batch 50) | **Ejecutada y FALLIDA** | `task-146` (`LATENCY BENCHMARK`) |
| Pruebas de concurrencia multi-hilo en carga / arranque | `REQ-BK-09` | Singleton thread-safe | No ejecutada (riesgo observado en código) | **Prueba no existente** | Inspección `prediction_service.py:427-432` |

---

## 10. Auditoría de seguridad y calidad

| Aspecto | Hallazgo objetivo | Clasificación |
|---|---|---|
| **Separación de responsabilidades y modularidad** | Buena separación en `src/` (`config`, `data`, `features`, `models`, `calibration`, `evaluate`, `train`, `api`). Sin código duplicado entre batch e inferencia dentro de `src/`. | Fortaleza |
| **Manejo de excepciones** | `prediction_service.py:15` ejecuta `warnings.filterwarnings("ignore")` global al importar (oculta advertencias útiles de versión/deprecación); `src/models.py:24` usa `except Exception: pass` silencioso; `prediction_service.py:201-210` no atrapa `TypeError` posterior con fechas tz-aware. | Defecto / Mejora |
| **Logging y observabilidad** | `logging=False` en los **10** archivos Python (`src/*.py` y `prediction_service.py`). No hay bitácora estructurada de requests, tiempos ni errores de servidor (`500`). | Recomendación técnica |
| **Seguridad CORS y configuración** | `src/api.py:66-72` fija `allow_origins=["*"]` hardcoded sin variable de entorno configurable. No existen secretos expuestos en el código. | Recomendación técnica |
| **Concurrencia** | `get_predictor()` (`prediction_service.py:427-432`) no usa `threading.Lock`; bajo múltiples peticiones simultáneas antes de completar `lifespan` o en uso directo multi-hilo podría instanciar dos veces `EPLPredictor`. | Riesgo técnico bajo–medio |
| **Dependencias** | `requirements.txt` al día con versiones exactas. No se ejecutó auditoría CVE externa (`pip-audit`) por no estar instalada ni corresponder modificar dependencias. | Limitación registrada |

---

## 11. Análisis de regresiones

Comparación directa de `feat/hito3-backend` (`e6136f6`) frente a `main` (`fe7ebab`):

1. **Contratos de `prediction_service.py` rotos respecto a `main`:**
   - **Métodos y atributos removidos en `EPLPredictor`:** `get_latest_team_stats`, `get_h2h_stats`, `TEAM_ALIASES` (movido a `src.config`), `epl`, `matches`, `matches_e0`, `prem`.
   - **Claves removidas en `predict_match()["contexto_prepartido"]`:** `Forma5_Local` y `Forma5_Visitante` (reemplazadas por `RollingPts5_Local` y `RollingPts5_Visitante`).
   - **Incidencia:** Cualquier código externo, prueba heredada o interfaz que consultara `contexto_prepartido['Forma5_Local']` o `predictor.get_latest_team_stats(...)` fallará con `KeyError` / `AttributeError`.
2. **Desincronización destructiva con `Proyecto_Red_Neuronal_Profunda_EPL.ipynb`:**
   - El notebook en `feat/hito3-backend` permanece igual que en `main` (40 features, modelo de 4 capas). Su Celda 32 (`predecir_partido`) aún funciona porque solo accede a `probabilities`, `suma_probabilidades`, `pronostico_mas_probable`, `Elo_Local` y `Elo_Visitante`, **pero** su Celda 20 guarda en `'models/best_deep_mlp.keras'` (40 features), lo cual destruiría la compatibilidad del Backend de 45 features si se reejecutara el notebook.
3. **Cambio positivo respecto a Hito 2:** Se corrigieron regresiones graves de datos/lógica del Hito 2 (arrastre de `SeasonPts` en Jornada 1, lag en `Elo`/`Form`, rechazo de minúsculas y ausencia de 120 partidos históricos).

---

## 12. Matriz final de cumplimiento

| ID | Requisito | Implementación | Archivos | Pruebas | Evidencia | Estado | Observaciones |
|---|---|---|---|---|---|---|---|
| `REQ-H3-01` | Especificación funcional oficial Hito 3 | No verificable | N/A (falta doc) | Ninguna | Búsqueda completa repo | **BLOQUEADO** | Falta guía oficial Hito 3 |
| `REQ-H3-02` | Rúbrica y umbrales Hito 3 | No verificable | N/A (falta doc) | Ninguna | Búsqueda completa repo | **BLOQUEADO** | Falta rúbrica Hito 3 |
| `REQ-H3-03` | Correcciones feedback docente Hito 2 | No verificable | N/A (falta doc) | Ninguna | Búsqueda completa repo | **BLOQUEADO** | Falta retroalimentación Hito 2 |
| `REQ-BK-01` | Ingesta y consolidación EPL íntegra | Parcialmente rota en Elo | [src/data.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/data.py) | `test_data.py` + probe CSV | 9,900 partidos; pero 41 Elos de `Nott'm Forest` congelados en `1731.5` | **DEFECTUOSO** | Bug `drop_duplicates(keep='last')` tras reemplazar nombre |
| `REQ-BK-02` | Features causales y paridad Train=Inf | Implementado con brechas | [src/features.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py), [prediction_service.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py) | `test_features.py` + probe debut | Paridad `atol=1e-9`; fuga menor en `season_bounds`; debutantes bloqueados | **PARCIALMENTE CUMPLIDO** | Falta filtrar `MatchDate < target_ts` en `season_bounds` y unificar debutantes |
| `REQ-BK-03` | Split cronológico y `StandardScaler` Train | Completo | [src/config.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/config.py), [src/features.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py) | `test_features.py` | `n_samples_seen_ == 6460`, invarianza ante corrupción de Test | **CUMPLIDO Y VERIFICADO** | Sin observaciones bloqueantes |
| `REQ-BK-04` | Modelo Deep MLP Softmax reproducible | Completo | [src/models.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/models.py), [src/train.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py) | Check de reproducción | `best_deep_mlp.keras` reproduce `0.0` diff contra `training_summary.json` | **CUMPLIDO Y VERIFICADO** | `Residual_Deep_MLP_3L` (6,189 params) |
| `REQ-BK-05` | Superar baselines (compromiso Hito 2) | Supera varios, no a todos | [src/train.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py), [models/training_summary.json](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/models/training_summary.json) | Evaluación reproducible | En Test supera Dummy/Hito2/HGB, pero pierde vs LogReg y Bet365 | **PARCIALMENTE CUMPLIDO** | En 2025/26 sí supera a LogReg y HGB en LL/Brier/ECE |
| `REQ-BK-06` | Calibración y sensibilidad al empate | Completo | [src/calibration.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/calibration.py), [src/evaluate.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/evaluate.py) | `test_calibration.py` + `training_summary.json` | `T=1.172`, pesos `[1.0, 1.49, 1.08]` en Val; Test `F1-D=27.53%`, `MacF1=48.39%` | **CUMPLIDO Y VERIFICADO** | En Test `top_label_ece` sube levemente `0.0282->0.0312` |
| `REQ-BK-07` | Servicio predictivo Python confiable | Con crash tz-aware y regresiones | [prediction_service.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py) | `test_service.py` + probes | Lanza `TypeError` no capturado con `"2024-04-23T15:00:00Z"` | **DEFECTUOSO** | Crashea en fechas ISO con zona horaria |
| `REQ-BK-08` | API REST FastAPI y manejo HTTP | Con `HTTP 500` tz-aware y cota `odds` | [src/api.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py) | `test_api.py` + probes `TestClient` | Devuelve `HTTP 500` en `/predict` y `/teams/.../stats` con `Z`; acepta `1e308` | **DEFECTUOSO** | Violación crítica de contrato REST ante fechas UTC |
| `REQ-BK-09` | Rendimiento y latencia operativa | O(N) por fila en inferencia | [src/features.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py), [src/api.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py) | Benchmark `TestClient` | `347.0 ms` (`/predict`), `16,726.6 ms` (`/predict/batch` 50) | **DEFECTUOSO** | Lote 50 toma ~16.7 s en una sola petición |
| `REQ-BK-10` | Persistencia atómica y sincronización | Completo | [src/train.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py), `models/` | Inspección binaria/JSON | 6 archivos sincronizados, huérfanos eliminados | **CUMPLIDO Y VERIFICADO** | Sin observaciones |
| `REQ-BK-11` | Gestión reproducible de dependencias | Completo | [requirements.txt](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/requirements.txt) | Verificación de versiones | 11 paquetes fijados exactos | **CUMPLIDO Y VERIFICADO** | Sin `pip-audit` de CVEs |
| `REQ-BK-12` | Pruebas automatizadas y cobertura bordes | Incompleta en bordes críticos | `tests/` | `unittest` (26 OK) vs probes | Faltan tests de tz-aware, Elo Forest, debutantes, latencia, concurrencia | **PARCIALMENTE CUMPLIDO** | 26 pruebas existentes pasan, pero dejaron bugs sin detectar |
| `REQ-BK-13` | Ausencia de regresiones vs Hito 2 | Rompe contrato Hito 2 | [prediction_service.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py), [Proyecto_Red_Neuronal_Profunda_EPL.ipynb](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/Proyecto_Red_Neuronal_Profunda_EPL.ipynb) | Diff + scan estático | 7 atributos/métodos removidos, 2 claves JSON cambiadas, notebook incompatible | **DEFECTUOSO** | Riesgo de sobrescribir modelo si se corre notebook |

### Resumen cuantitativo de la matriz
- **Total de requisitos Backend listados:** **16** (100.00%)
  - **Cumplidos y verificados:** **5** (**31.25%**) — `REQ-BK-03`, `REQ-BK-04`, `REQ-BK-10`, `REQ-BK-11`, `REQ-BK-06`
  - **Implementados, pero no verificados:** **0** (**0.00%**)
  - **Parcialmente cumplidos:** **3** (**18.75%**) — `REQ-BK-02`, `REQ-BK-05`, `REQ-BK-12`
  - **No cumplidos:** **0** (**0.00%**)
  - **Defectuosos:** **5** (**31.25%**) — `REQ-BK-01`, `REQ-BK-07`, `REQ-BK-08`, `REQ-BK-09`, `REQ-BK-13`
  - **Bloqueados (sin doc. oficial Hito 3):** **3** (**18.75%**) — `REQ-H3-01`, `REQ-H3-02`, `REQ-H3-03`
  - **No aplica:** **0** (**0.00%**)
- *(Sobre los 13 requisitos técnicos evaluables sin guía oficial: **38.46%** cumplidos y verificados, **23.08%** parcialmente cumplidos, **38.46%** defectuosos).*

---

## 13. Hallazgos y defectos

### HAL-01 — Ausencia total de documentación oficial del Hito 3
- **Descripción:** No existen la guía oficial, rúbrica de evaluación ni retroalimentación del Hito 2 en el repositorio ni workspace.
- **Evidencia:** Inventario completo de directorio raíz, historial Git (`a47dc11` a `e6136f6`) y ramas (`main`, `feat/hito3-backend`).
- **Archivo y ubicación:** Raíz del repositorio (documento faltante).
- **Requisito afectado:** `REQ-H3-01`, `REQ-H3-02`, `REQ-H3-03`.
- **Impacto:** Impide verificar cumplimiento normativo de entregables obligatorios del Hito 3.
- **Severidad:** **CRÍTICA**
- **Riesgo académico:** Posible omisión de requisitos obligatorios evaluados en la rúbrica del Hito 3 (ej. despliegue, explicabilidad formal, integración con frontend, etc.).
- **Riesgo técnico:** Trabajar sobre supuestos sin contrato académico explícito.
- **Solución recomendada:** Incorporar al repositorio (`docs/`) el enunciado oficial y rúbrica del Hito 3 junto con la retroalimentación del Hito 2 y revalidar la matriz contra cada ítem.

### HAL-02 — `TypeError` no controlado y `HTTP 500` ante fechas ISO-8601 con zona horaria
- **Descripción:** Fechas válidas ISO-8601 con sufijo `Z` o desplazamiento horario (ej. `"2024-04-23T15:00:00Z"`, común en JavaScript/TypeScript `new Date().toISOString()`) hacen fallar `prediction_service.py` con `TypeError` y provocan `HTTP 500 Internal Server Error` en FastAPI.
- **Evidencia:** Prueba adversarial `TestClient`: `POST /predict` y `GET /teams/arsenal/stats?match_date=2024-04-23T15:00:00Z` devolvieron `500`; llamada Python lanzó `TypeError: Invalid comparison between dtype=datetime64[ns] and Timestamp`.
- **Archivo y ubicación:** [prediction_service.py:201-210](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L201-L210) (`_parse_date`), [src/features.py:496](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L496) (`df_history["MatchDate"] < target_ts`) y [src/api.py:128-151](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py#L128-L151).
- **Requisito afectado:** `REQ-BK-07`, `REQ-BK-08`.
- **Impacto:** Un cliente web estándar que serialice fechas con `.toISOString()` tumbará el endpoint con error 500.
- **Severidad:** **ALTA**
- **Riesgo académico:** Caída en vivo (error 500) durante la demostración con frontend o Swagger.
- **Riesgo técnico:** Incompatibilidad con clientes REST modernos y ausencia de manejo de excepciones inesperadas en la API.
- **Solución recomendada:** En `_parse_date`, convertir timestamps con zona horaria a naive UTC (`ts.tz_convert("UTC").tz_localize(None)` si `ts.tzinfo is not None`) antes de `.normalize()`.

### HAL-03 — Corrupción silenciosa del Elo de Nottingham Forest (`2025-01-01` a `2026-09-01`)
- **Descripción:** Al normalizar `"Nottm Forest"` a `"Nott'm Forest"` antes de eliminar duplicados con `keep="last"`, la serie congelada de `"Nottm Forest"` (`1731.5`) en `EloRatings.csv` sobreescribe los 41 registros reales y actualizados de `"Nott'm Forest"` (`1758.31`–`1792.37`) entre 2025 y 2026.
- **Evidencia:** Verificación directa sobre `EloRatings.csv`, `Matches.csv` y `GET /teams/Nott'm Forest/stats` (`elo = 1731.5` al `2026-09-07`, frente a `1785.14` en `2026-09-01` en `EloRatings.csv` bajo `"Nott'm Forest"`).
- **Archivo y ubicación:** [src/data.py:29-38](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/data.py#L29-L38) (`load_elo_ratings`).
- **Requisito afectado:** `REQ-BK-01`, `REQ-BK-02`, `REQ-BK-07`.
- **Impacto:** Todos los partidos de Nottingham Forest desde enero de 2025 (en `Test 2024/25`, `Prospectivo 2025/26`, `2026/27` e inferencia actual) reciben un Elo estático erróneo de `1731.5` (desvío hasta ~61 puntos Elo).
- **Severidad:** **ALTA**
- **Riesgo académico:** Falla de calidad de datos verificable en vivo consultando `/teams/Nott'm Forest/stats`.
- **Riesgo técnico:** Sesgo sistemático en las variables `HomeElo`, `AwayElo`, `DiffElo`, `EloProb_Home` y fallback de mercado para ese club.
- **Solución recomendada:** Priorizar los registros cuyo nombre original ya era `"Nott'm Forest"` sobre `"Nottm Forest"` en fechas duplicadas (o deduplicar ordenando por prioridad de fuente antes de `keep="last"`) y reentrenar.

### HAL-04 — Regresión de contrato Python/JSON en `prediction_service.py` y desincronización destructiva con el notebook
- **Descripción:** `prediction_service.py` eliminó atributos/métodos de `main` (`get_latest_team_stats`, `get_h2h_stats`, `TEAM_ALIASES`, `epl`, `matches`, `matches_e0`, `prem`) y cambió claves de `contexto_prepartido` (`Forma5_Local/Visitante` → `RollingPts5_Local/Visitante`). Paralelamente, `Proyecto_Red_Neuronal_Profunda_EPL.ipynb` no fue actualizado y sigue configurado para 40 features apuntando a `models/best_deep_mlp.keras`.
- **Evidencia:** `task-146` (`CONTRACT REGRESSION CHECK` y `NOTEBOOK STATIC COMPATIBILITY SCAN`).
- **Archivo y ubicación:** [prediction_service.py:124-421](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L124-L421), [Proyecto_Red_Neuronal_Profunda_EPL.ipynb](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/Proyecto_Red_Neuronal_Profunda_EPL.ipynb) Celdas 14, 18 y 20.
- **Requisito afectado:** `REQ-BK-13`, `REQ-BK-05`.
- **Impacto:** Rompe consumidores antiguos de `EPLPredictor` y crea riesgo de sobrescritura incompatible de `models/best_deep_mlp.keras` si alguien reejecuta el notebook. Además `Hito2Proyecto.pdf` (40 features, 128-64-32-16) queda desalineado frente al backend (45 features, `Residual_Deep_MLP_3L`).
- **Severidad:** **ALTA**
- **Riesgo académico:** Contradicción entre lo que el notebook/informe dice que entrena y lo que realmente corre en el backend.
- **Riesgo técnico:** Fallo inmediato `ValueError` de dimensiones (`40 vs 45`) si el notebook sobrescribe el modelo.
- **Solución recomendada:** Agregar wrappers/alias retrocompatibles en `EPLPredictor` (si se requiere compatibilidad con Hito 2) y, en la etapa documental/notebook del Hito 3, alinear o delegar el notebook a `src.train`.

### HAL-05 — Latencia elevada en `/predict` (`347 ms`) y crítica en `/predict/batch` (`16.7 s` para 50 partidos)
- **Descripción:** `POST /predict` promedia `347.0 ms` y `POST /predict/batch` con 50 partidos tarda `16,726.6 ms` (~16.73 segundos).
- **Evidencia:** Benchmark cronometrado sobre `TestClient(app)` (`task-146`).
- **Archivo y ubicación:** [src/features.py:512-565](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L512-L565) (`_collect_team_state` itera todo el historial `itertuples()` de 25 años por cada partido) y [src/api.py:154-174](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py#L154-L174) (bucle de 50 llamadas individuales a `model.predict`).
- **Requisito afectado:** `REQ-BK-09`.
- **Impacto:** Bloquea el event loop de FastAPI (`def` síncrono largo en batch) y ofrece experiencia lenta al predecir jornadas completas o simulaciones desde un frontend.
- **Severidad:** **MEDIA**
- **Riesgo académico:** Mala percepción de fluidez al consultar una jornada completa en la sustentación.
- **Riesgo técnico:** Saturación de workers Uvicorn bajo peticiones concurrentes de batch.
- **Solución recomendada:** Preindexar historiales por equipo (o limitar el slice antes de iterar para rolling, conservando conteo vectorizado para `SeasonPts/GD`) y vectorizar la inferencia por lote con una sola llamada a `model.predict(X_batch)`.

### HAL-06 — Fuga menor temporal en `season_bounds` dentro de `compute_single_match_features`
- **Descripción:** La detección del nombre de temporada (`2019/20` vs `2020/21`) evalúa `min`/`max` de `MatchDate` por temporada sobre todo `df_history`, incluyendo fechas futuras respecto a `target_ts`.
- **Evidencia:** Inspección directa de [src/features.py:505-510](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L505-L510).
- **Archivo y ubicación:** [src/features.py:503-510](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py#L503-L510).
- **Requisito afectado:** `REQ-BK-02`.
- **Impacto:** No altera cálculos fuera de fechas fronterizas de julio 2020 y no filtra resultados futuros, pero viola estrictamente el principio de no consultar `df_history >= target_ts`.
- **Severidad:** **MEDIA** (bajo impacto práctico, rigor formal).
- **Riesgo académico:** Objeción en revisión de código sobre causalidad temporal estricta.
- **Riesgo técnico:** Dependencia implícita del límite máximo futuro de una temporada en `df_history`.
- **Solución recomendada:** Inferir la temporada únicamente desde `hist_before` (`MatchDate < target_ts`) o reglas explícitas de calendario sin leer filas `>= target_ts`.

### HAL-07 — Rechazo `HTTP 404` a clubes recién ascendidos o en su debut EPL
- **Descripción:** `prediction_service.py` bloquea la predicción con `insufficient_history` (`HTTP 404`) si un equipo tiene `0` partidos previos en `df_history` antes de `match_date` (ej. `Brentford` en la Jornada 1 de `2021/22`, `2021-08-13`), mientras que el pipeline de entrenamiento (`FeatureStateEngine.compute_batch_features`) sí procesó ese partido usando los valores iniciales neutros y `EloRatings.csv`.
- **Evidencia:** Probe `Brentford debut EPL 2021-08-13` devolvió `HTTP 404` (`task-146`).
- **Archivo y ubicación:** [prediction_service.py:334-339](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L334-L339) y [prediction_service.py:166-167](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L166-L167).
- **Requisito afectado:** `REQ-BK-02`, `REQ-BK-07`.
- **Impacto:** Impide predecir la primera jornada de un equipo recién ascendido que figura en `known_teams` y ya posee rating en `EloRatings.csv`.
- **Severidad:** **MEDIA**
- **Riesgo académico:** Contradicción entre soporte en evaluación batch y rechazo en inferencia online.
- **Riesgo técnico:** Errores innecesarios al simular temporadas completas desde la Jornada 1.
- **Solución recomendada:** Si `elo_lookup` ya posee Elo válido para el debutante o `match_date >= min_history_date`, permitir la predicción emitiendo un `warning` de historial rodante vacío en lugar de bloquear con `404` (reservando `404` para fechas anteriores al historial EPL como `1995-01-01`).

### HAL-08 — Brecha frente a Regresión Logística y Bet365 en Test y leve aumento de `ECE` en Test tras Temperature Scaling
- **Descripción:** El modelo seleccionado (`Residual_Deep_MLP_3L`) mejora sustancialmente al del Hito 2 y supera a `HistGradientBoosting` en Test y a `Regresión Logística` + `HGB` en `2025/26` (`Log Loss`/`Brier`/`ECE`), pero en Test (`n=1,520`) aún queda detrás de Regresión Logística (`56.91%`, LL `0.9495`) y de Bet365 (`56.91%`, LL `0.9458`). Asimismo, `T = 1.172273` reduce `Log Loss` y `Brier` en Test, pero eleva levemente `top_label_ece` de `0.0282` a `0.0312`.
- **Evidencia:** [models/training_summary.json](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/models/training_summary.json).
- **Archivo y ubicación:** [src/models.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/models.py), [src/train.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py), [models/training_summary.json](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/models/training_summary.json).
- **Requisito afectado:** `REQ-BK-05`, `REQ-BK-06`.
- **Impacto:** Aunque los resultados son científicamente honestos y reales, no cumplen literalmente el compromiso absoluto del Hito 2 de superar a todos los modelos de referencia en exactitud y fiabilidad probabilística.
- **Severidad:** **MEDIA**
- **Riesgo académico:** Pregunta directa en sustentación sobre por qué el modelo lineal (`C=0.01`) sigue igualando o superando levemente en `Test` al Deep MLP.
- **Riesgo técnico:** Alta eficiencia del mercado de apuestas en datos tabulares agregados limita la ganancia no lineal sin features adicionales (ej. `xG`, alineaciones o mercado de cierre/apertura).
- **Solución recomendada:** Reformular explícitamente en la documentación del Hito 3 la hipótesis frente al mercado eficiente (y destacar la ganancia en `2025/26`, `Macro-F1` y calibración) o explorar regularización/features adicionales en `Val` si se busca superar a LogReg en `Val`/`Test`.

### HAL-09 — Ausencia de `logging` estructurado y supresión global de advertencias
- **Descripción:** Ninguno de los 10 archivos Python del backend utiliza el módulo estándar `logging`; `prediction_service.py:15` oculta todas las advertencias del proceso con `warnings.filterwarnings("ignore")` y `src/models.py:24-25` silencia cualquier excepción al activar determinismo.
- **Evidencia:** Escaneo estático (`task-149`).
- **Archivo y ubicación:** [prediction_service.py:15](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L15), [src/models.py:22-25](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/models.py#L22-L25).
- **Requisito afectado:** Calidad de software y observabilidad.
- **Impacto:** Dificulta diagnosticar errores en producción (como los `500` de `HAL-02`) o fallos de determinismo/versiones.
- **Severidad:** **MEDIA** *(recomendación de calidad)*
- **Riesgo académico:** Bajo.
- **Riesgo técnico:** Pérdida de trazabilidad operativa en despliegue.
- **Solución recomendada:** Introducir `logging` estándar configurable y eliminar `warnings.filterwarnings("ignore")` global.

### HAL-10 — Endurecimiento operativo de FastAPI (cota superior de cuotas, batch parcial, CORS, singleton lock y `/model/metrics`)
- **Descripción:** Conjunto de debilidades menores de diseño API: (a) `OddsInput` acepta `1e308`; (b) `/predict/batch` falla todo el lote sin devolver el índice del partido erróneo; (c) `allow_origins=["*"]` está fijo sin configuración por entorno; (d) `get_predictor()` carece de `threading.Lock`; (e) `GET /model/metrics` transfiere `277,460 bytes` completos en cada consulta.
- **Evidencia:** Probes `TestClient` (`task-146`) e inspección de [src/api.py:15-185](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py#L15-L185) y [prediction_service.py:424-439](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py#L424-L439).
- **Requisito afectado:** `REQ-BK-08`, calidad/seguridad API.
- **Impacto:** Respuestas poco informativas en errores batch, exposición excesiva de payload y ausencia de control de orígenes en despliegue real.
- **Severidad:** **BAJA–MEDIA**
- **Riesgo académico:** Bajo en entorno académico local; medio si la rúbrica del Hito 3 exige despliegue en nube.
- **Riesgo técnico:** Problemas menores de integración frontend o concurrencia inicial.
- **Solución recomendada:** Acotar `OddsInput(..., le=1000.0)`, agregar soporte de detalle por índice en `/predict/batch`, parametrizar `CORS_ALLOW_ORIGINS` por variable de entorno, proteger `get_predictor()` con `threading.Lock` y ofrecer parámetro `?include_bins=false` en `/model/metrics`.

---

## 14. Plan de correcciones (NO implementado — ordenado por prioridad y dependencias)

1. **Prioridad 0 — Desbloqueo normativo (`HAL-01`):**
   - Obtener e incorporar guía oficial, rúbrica de calificación del Hito 3 y retroalimentación docente del Hito 2.
   - Reevaluar si se requieren nuevos endpoints, despliegue, base de datos o análisis de explicabilidad formal (ej. SHAP).
2. **Prioridad 1 — Correcciones críticas de integridad y estabilidad (`HAL-02`, `HAL-03`, `HAL-04`):**
   - **C1 (`HAL-02`):** Normalizar fechas tz-aware a UTC naive en `_parse_date` (`prediction_service.py`) y capturar excepciones inesperadas limpiamente en `src/api.py` (nunca `500` por formato de entrada).
   - **C2 (`HAL-03`):** Corregir `load_elo_ratings` en `src/data.py` para conservar los registros reales de `"Nott'm Forest"` (2025–2026) por encima de los congelados de `"Nottm Forest"`, añadir prueba unitaria de regresión (`elo > 1740` en `2026-09-01`) y **reentrenar** mediante `python -m src.train` una vez corregido `C2`.
   - **C3 (`HAL-04`):** Decidir compatibilidad con Hito 2 (agregar adaptadores si aún se consumen `Forma5_*` o `get_latest_team_stats`) y proteger `models/best_deep_mlp.keras` evitando sobrescritura desde el notebook viejo.
3. **Prioridad 2 — Rendimiento y consistencia causal (`HAL-05`, `HAL-06`, `HAL-07`):** *(depende de C2 si cambia índice de datos)*
   - **C4 (`HAL-05`):** Preindexar historiales por club y vectorizar `predict_batch` para bajar `/predict` a `<50 ms` y `/predict/batch (50)` a `<500 ms`.
   - **C5 (`HAL-06`):** Calcular rango de temporada exclusivamente sobre `hist_before` (`MatchDate < target_ts`).
   - **C6 (`HAL-07`):** Permitir inferencia de equipos debutantes con Elo válido en `EloLookup` emitiendo advertencia explícita.
4. **Prioridad 3 — Endurecimiento, observabilidad y validación (`HAL-08`, `HAL-09`, `HAL-10`):**
   - **C7 (`HAL-10`):** Acotar `OddsInput(gt=1.0, le=1000.0)`, mejorar respuesta de errores en `/predict/batch`, parametrizar CORS y agregar `threading.Lock` en `get_predictor()`.
   - **C8 (`HAL-09`):** Incorporar `logging` estructurado y remover `warnings.filterwarnings("ignore")`.
   - **C9 (`HAL-12` / `HAL-08`):** Ampliar `tests/` con todas las pruebas adversariales hoy ausentes y alinear las afirmaciones métricas finales con el documento del Hito 3.

---

## 15. Veredicto definitivo

### Veredicto formal frente a los requisitos del Hito 3: **`NO CONCLUYENTE`** *(con objeciones técnicas bloqueantes)*

**Justificación estricta basada en la matriz de cumplimiento:**
1. **Imposibilidad normativa de certificar el Hito 3 (`BLOQUEADO`):** Los 3 requisitos oficiales del Hito 3 (`REQ-H3-01` a `REQ-H3-03`, **18.75%** del total) están bloqueados porque no existe guía oficial, rúbrica ni retroalimentación docente en el repositorio. Nadie puede declarar legítimamente que se cumplen requisitos oficiales que no han sido suministrados.
2. **Incumplimiento técnico en componentes ya construidos (`DEFECTUOSO`):** Incluso evaluando exclusivamente los 13 requisitos técnicos auditables del Backend, **5 requisitos (38.46%) son `DEFECTUOSOS`** (`REQ-BK-01`, `REQ-BK-07`, `REQ-BK-08`, `REQ-BK-09`, `REQ-BK-13`), destacando **3 hallazgos de severidad ALTA**: `HTTP 500` con fechas ISO-UTC, corrupción silenciosa del Elo de `Nott'm Forest` en 2025–2026 y regresiones de contrato/desincronización con el notebook del Hito 2. Por consiguiente, **tampoco merece un `APROBADO` técnico en su estado actual** y requiere ejecutar primero el Plan de Correcciones (P0–P2) antes de la entrega final.

---

## 16. Lista de evidencias que respaldan el veredicto

1. **Inspección de estructura e historial Git:** `git branch -a`, `git status -sb`, `git diff --stat main..HEAD`, `git log --all --oneline -n 15`.
2. **Lectura directa del código fuente y documentos:**
   - [Hito2Proyecto.pdf](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/Hito2Proyecto.pdf), [README.md](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/README.md), [requirements.txt](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/requirements.txt).
   - [src/config.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/config.py), [src/data.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/data.py), [src/features.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/features.py), [src/models.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/models.py), [src/calibration.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/calibration.py), [src/evaluate.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/evaluate.py), [src/train.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/train.py), [src/api.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/src/api.py), [prediction_service.py](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/prediction_service.py).
   - [Proyecto_Red_Neuronal_Profunda_EPL.ipynb](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/Proyecto_Red_Neuronal_Profunda_EPL.ipynb) (escaneo de compatibilidad).
3. **Inspección binaria y JSON de artefactos en `models/`:** tamaños exactos, estructura de capas Keras de `best_deep_mlp.keras`, `scaler.n_samples_seen_ == 6460.0`, `calibration.json` y [training_summary.json](file:///c:/Users/José%20Alejandro/Documents/ProyectoPredictor-PremierLeague/models/training_summary.json) (verificación de reproducción exacta `diff = 0.0`).
4. **Ejecución independiente de la suite existente:** `python -m unittest discover -s tests -v` (`Ran 26 tests in 20.549s — OK`).
5. **Ejecución de batería adversarial independiente:**
   - Probes sobre `TestClient(app)` (`18` escenarios de bordes HTTP/Pydantic/fechas/cuotas/CORS) y servicio Python directo.
   - Verificación cruzada entre `EloRatings.csv`, `Matches.csv` y `load_elo_ratings()` demostrando los `41` registros corruptos de `Nott'm Forest`.
   - Benchmark de latencia (`347.0 ms` individual, `16,726.6 ms` lote 50).
   - Verificación de regresión de contrato frente a `main:prediction_service.py`.

---

## 17. Respuesta directa a la pregunta final

> **¿El Backend que tenemos actualmente cumple íntegramente con TODOS los requisitos obligatorios del Hito 3, está correctamente implementado, funciona y cuenta con evidencias suficientes para defenderlo ante el profesor?**

**No.** En su estado actual, **no cumple íntegramente ni está listo para defenderse sin correcciones previas**, por tres razones objetivas demostradas:

1. **No conocemos todos los requisitos obligatorios del Hito 3:** No existe en el repositorio la guía oficial, la rúbrica de calificación ni la retroalimentación del Hito 2. Cualquier afirmación de "100% cumplido" sin contrastar esos documentos sería falsa.
2. **Aunque la arquitectura nueva es sólida y sus 26 pruebas pasan, tiene 3 fallos reales de severidad ALTA ocultos fuera de sus propios tests:** (a) responde `HTTP 500` ante fechas ISO-8601 con zona horaria `Z` estándar en frontends web, (b) corrompe silenciosamente el rating Elo de `Nott'm Forest` en `2025–2026` dejándolo congelado en `1731.5`, y (c) rompió compatibilidad de métodos/claves con el Hito 2 mientras el notebook antiguo sigue desincronizado. Además, el endpoint `/predict/batch` tarda ~16.7 segundos para 50 partidos.
3. **Qué sí es defendible hoy y qué falta para blindarlo:** La base científica y de ML (cero fuga en preprocesamiento, paridad exacta `batch == single`, calibración por `Temperature Scaling`, umbrales Bayesianos reales en `Val`, evaluación en `Test` y en `2025/26`, y persistencia atómica reproducible `0.0` diff) **sí está bien construida y respaldada por evidencia**. Corrigiendo los hallazgos `HAL-02` a `HAL-07` y verificando contra la guía oficial del Hito 3 (`HAL-01`), el Backend quedará genuinamente listo para la máxima calificación.

---

## 18. Adenda de Re-verificación Post-Correcciones (Commit `625c3f8`)

Tras ejecutar el plan de correcciones y reentrenar la rama `feat/hito3-backend`, se realizó una segunda verificación independiente y adversarial sin dar nada por dado:

1. **Cierre de defectos técnicos (`HAL-02` a `HAL-10`):**
   - **`HAL-02` (CORREGIDO):** `POST /predict` y `GET /teams/{team_name}/stats` aceptan sin error fechas ISO-8601 con zona horaria (`Z`, `+05:30`, `-05:00`) devolviendo `HTTP 200`; cero respuestas `HTTP 500`.
   - **`HAL-03` (CORREGIDO):** Los 65 partidos de `Nott'm Forest` desde `2024-12-01` muestran 32 valores Elo distintos (`1711.94`–`1810.10`; `1785.14` al `2026-09-01`), manteniendo `1731.50` únicamente en los 3 partidos históricos reales de dic-2024.
   - **`HAL-04` (CORREGIDO):** Restituidos `EPLPredictor.TEAM_ALIASES`, `get_latest_team_stats`, `get_h2h_stats` y `Forma5_Local`/`Forma5_Visitante` en `contexto_prepartido`; añadida guarda de dimensiones (`45` features) al cargar `best_deep_mlp.keras`.
   - **`HAL-05` (CORREGIDO):** Latencia medida en `TestClient` bajó de `347.0 ms` a **`37.74 ms`** en `/predict` (10 llamadas) y de `16,726.6 ms` a **`214.53 ms`** en `/predict/batch` (50 partidos).
   - **`HAL-06` (CORREGIDO):** Detección causal de temporada sin consultar filas futuras (`2,300` partidos en `2000/01`, `2001/02`, `2019/20`, `2022/23`, `2024/25`, `2025/26`, `2026/27` verificados con **0 discrepancias**, `atol=1e-9`).
   - **`HAL-07` (CORREGIDO):** Clubes debutantes (`Brentford`, `2021-08-13`) predicen en `POST /predict` y `/teams/Brentford/stats` con `HTTP 200` y advertencia explícita.
   - **`HAL-09` y `HAL-10` (CORREGIDOS):** Añadido `logging`, removido `warnings.filterwarnings("ignore")` global, lock en singleton `get_predictor()`, `OddsInput` acotado a `(1.0, 1000.0]`, `match_index` en errores batch, `CORS_ALLOW_ORIGINS` parametrizado y `?include_bins=false|true` en `GET /model/metrics` (`21,478 bytes` compacto vs `131,226 bytes` completo).
2. **Evidencia de re-verificación integral:**
   - `py_compile` aprobado en los 16 archivos Python (`src/`, `tests/`, `prediction_service.py`).
   - Suite `python -m unittest discover -s tests -v`: **33 / 33 pruebas aprobadas** (`22.602 s`).
   - Paridad `predict_matches_batch` vs `predict_match` en 4 escenarios mixtos (`max diff < 1e-5`), reproducibilidad `0.0` diff contra `models/training_summary.json` y cruce exacto 100% con las tablas de `README.md`.
3. **Veredicto actualizado tras las correcciones:**
   - **Estado técnico de ingeniería Backend:** **APROBADO TÉCNICAMENTE** *(todos los defectos técnicos `HAL-02`–`HAL-10` quedaron cerrados y verificados; se mantiene registrada la observación `HAL-08` sobre el techo competitivo frente a Bet365/Regresión Logística en `Test`, documentada con honestidad científica).*
   - **Estado normativo frente a los requisitos oficiales del Hito 3:** Permanece **`NO CONCLUYENTE`** únicamente por **`HAL-01`** (ausencia de la guía y rúbrica oficial del Hito 3 en el repositorio).

# Predictor de Resultados de la Premier League (PTIA — Hito 3)

**Institución:** Escuela Colombiana de Ingeniería Julio Garavito — Departamento de Ingeniería de Sistemas
**Curso:** PTIA — Grupo 04
**Integrantes:** Juan Diego Gaitán, José Alejandro Martínez, Oscar David Lasso, Carlos Andrés Sánchez

Sistema que estima, antes de que empiece un partido de la English Premier League, la probabilidad de **victoria local, empate y victoria visitante** con una red neuronal profunda calibrada. Incluye el modelo entrenado, un servicio de predicción en Python, una API REST y una interfaz web (MVP).

| Entrega | Material |
|---|---|
| Hito 2 — video | https://youtu.be/vJ2x2CfAMa4 |
| Hito 2 — documento | [`docs/Hito2Proyecto.pdf`](docs/Hito2Proyecto.pdf) |
| Hito 3 — video (máx. 10 min) | _pendiente_ |
| Hito 3 — documento | _pendiente_ |

---

## Puesta en marcha (MVP)

**Requisitos:** Python **3.10 a 3.13** (TensorFlow 2.21 no se instala en Python 3.14) y Node.js 20.19 o superior.

```bash
# 1. Entorno de Python (desde la raíz del repositorio)
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Dependencias de la interfaz
npm --prefix frontend ci
```

Levantar la aplicación (dos terminales, desde la raíz):

```bash
python -m uvicorn api.main:app --port 8000     # API que usa la interfaz (tarda unos segundos en cargar el modelo)
npm --prefix frontend run dev                   # Interfaz en http://localhost:5173
```

La interfaz tiene tres pantallas:
- **Predictor:** se eligen local, visitante, fecha (opcional) y cuotas (opcionales). Muestra las tres probabilidades frente a la frecuencia real de cada resultado en los partidos de prueba (2021–25), el estado de cada equipo antes del partido (Elo, forma, goles, descanso, temporada), el historial directo y los avisos del servicio (equipo debutante, fecha posterior a los datos).
- **Modelo:** comparación con los modelos de referencia, matriz de confusión y resumen de cómo se construyó y evaluó.
- **Privacidad:** qué hace la aplicación con los datos que se escriben (no hay cuentas, cookies ni servicios de terceros).

Si la API no responde, cada pantalla muestra el error con un botón para reintentar.

Para diseñar la interfaz sin TensorFlow existe un modo simulado: `EPL_MOCK=1 python -m uvicorn api.main:app --port 8000`.

---

## Estructura del repositorio

```text
├── api/main.py                     # API de la interfaz (FastAPI, rutas /api/*) sobre prediction_service.py
├── frontend/                       # Interfaz web: Vite + React + TypeScript + Tailwind
├── prediction_service.py           # Servicio de inferencia (EPLPredictor, predecir_partido) con caché
├── src/
│   ├── config.py                   # Rutas, particiones temporales y alias de clubes
│   ├── data.py                     # Consolidación 2000–2026 (9.900 partidos) y Elo causal
│   ├── features.py                 # 45 variables pre-partido y preprocesador ajustado solo en entrenamiento
│   ├── models.py                   # Arquitecturas Keras candidatas
│   ├── calibration.py              # Temperature scaling, umbrales bayesianos, ECE y Brier
│   ├── evaluate.py                 # Métricas multiclase
│   ├── train.py                    # Entrenamiento reproducible (python -m src.train)
│   └── api.py                      # API REST completa del backend (rutas sin prefijo, lotes, métricas)
├── models/                         # Artefactos del modelo desplegado
├── tests/                          # Pruebas unitarias, de integración y de las dos APIs
├── datasets/                       # Fuentes tabulares (Kaggle)
├── notebooks/
│   ├── Hito3_Evaluacion_Modelo.ipynb              # Evaluación del modelo del Hito 3 y casos de prueba
│   └── Proyecto_Red_Neuronal_Profunda_EPL.ipynb   # Notebook del Hito 2 (modelo anterior)
├── docs/
│   ├── Hito2Proyecto.pdf                          # Documento entregado en el Hito 2
│   ├── AUDITORIA_INDEPENDIENTE_BACKEND_HITO3.md   # Auditoría técnica del backend
│   └── adr/0001-frontend-y-api.md                 # Decisiones de arquitectura del frontend y la API
├── PRODUCT.md, DESIGN.md           # Contexto de producto y sistema de diseño de la interfaz
├── requirements.txt                # Dependencias del backend y la API
└── requirements-notebook.txt       # Dependencias extra para los notebooks
```

`PRODUCT.md` y `DESIGN.md` quedan en la raíz porque las herramientas de diseño de la interfaz los buscan ahí.

### Dos APIs sobre el mismo servicio

| | `api/main.py` | `src/api.py` |
|---|---|---|
| Uso | La consume la interfaz web | API general del backend (documentación en `/docs`) |
| Rutas | `/api/health`, `/api/teams`, `/api/predict`, `/api/metrics` | `/health`, `/teams`, `/teams/{equipo}/stats`, `/predict`, `/predict/batch`, `/model/metrics` |
| Arranque | `uvicorn api.main:app --port 8000` | `uvicorn src.api:app --port 8000` |

Ambas cargan el mismo `EPLPredictor`, así que devuelven las mismas probabilidades. `src/api.py` acepta orígenes CORS en `CORS_ALLOW_ORIGINS` (separados por coma; por defecto solo la interfaz local).

---

## Modelo

- **Datos:** 2000/01–2024/25 desde `PremierLeague.csv` (25 × 380 partidos) más 2025/26 y el inicio de 2026/27 desde `Matches.csv`; Elo causal desde `EloRatings.csv`.
- **Partición cronológica:** entrenamiento 2000/01–2016/17 (6.460), validación 2017/18–2020/21 (1.520), prueba 2021/22–2024/25 (1.520) y prospectivo 2025/26 (380).
- **Variables:** 45 calculadas solo con información anterior al partido: mercado (probabilidades implícitas, entropía, margen), Elo, forma de 3 y 5 partidos, goles, tiros, rendimiento por sede, descanso, puntos y diferencia de gol de la temporada e historial directo.
- **Red:** `Residual_Deep_MLP_3L` (6.189 parámetros), elegida por *log loss* en validación entre cuatro candidatas.
- **Calibración:** temperature scaling ($T = 1{,}172$) y umbrales bayesianos opcionales ($w = [1{,}0;\ 1{,}49;\ 1{,}08]$), ambos ajustados en validación.

### Resultados en prueba (2021/22–2024/25, 1.520 partidos)

| Modelo | Exactitud | F1 macro | F1 empate | Log loss | Brier |
|---|---:|---:|---:|---:|---:|
| Dummy (clase mayoritaria) | 44,54 % | 20,54 % | 0,00 % | 1,0687 | 0,6465 |
| Bet365 (cuotas implícitas) | 56,91 % | 42,18 % | 0,00 % | 0,9458 | 0,5598 |
| Regresión logística (C = 0,01) | 56,91 % | 42,80 % | 2,23 % | 0,9495 | 0,5621 |
| HistGradientBoosting | 56,51 % | 42,21 % | 1,11 % | 0,9541 | 0,5645 |
| Deep MLP del Hito 2 (128-64-32-16) | 55,72 % | 41,62 % | 0,56 % | 0,9569 | 0,5674 |
| **Residual Deep MLP calibrado (argmax)** | **56,71 %** | **45,47 %** | **10,92 %** | **0,9516** | **0,5631** |
| Residual Deep MLP calibrado (umbrales bayesianos) | 52,11 % | 48,39 % | 27,53 % | 0,9516 | 0,5631 |
| Ablación sin cuotas (40 variables) | 54,74 % | 41,78 % | 3,74 % | 0,9726 | 0,5770 |

La red mejora al modelo del Hito 2 y a HistGradientBoosting, pero queda 0,20 puntos por detrás de Bet365 y de la regresión logística en exactitud. En la temporada 2025/26 todos los modelos bajan (red: 46,84 %, *log loss* 1,0326; Bet365: 48,95 %, 1,0185). El análisis completo y los casos de prueba con partidos reales están en [`notebooks/Hito3_Evaluacion_Modelo.ipynb`](notebooks/Hito3_Evaluacion_Modelo.ipynb).

---

## Otras tareas

```bash
python -m unittest discover -s tests -v      # Pruebas del backend y de las dos APIs
npm --prefix frontend test                    # Pruebas del frontend (Vitest)
npm --prefix frontend run lint                # Linter del frontend
python prediction_service.py                  # Casos de ejemplo por consola
python -m src.train                           # Reentrenar y regenerar models/ (reemplaza el modelo desplegado)
pip install -r requirements-notebook.txt      # Dependencias para abrir los notebooks (matplotlib, seaborn, JupyterLab)
```

Los notebooks se abren desde `notebooks/` y leen datos y modelos de la raíz del repositorio. El del Hito 2 guarda su modelo en `models/hito2/` y no reemplaza el modelo desplegado si se vuelve a ejecutar.

## Fuentes de datos

- Gbor, A. (2025). *Club Football Match Data 2000–2025*. Kaggle — `Matches.csv`, `EloRatings.csv`.
- Hui, M. (2025). *English Premier League (EPL) Match Data 2000–2025*. Kaggle — `epl_final.csv` (solo notebook del Hito 2).
- Nazarenka, A. (2023). *Premier League*. Kaggle — `PremierLeague.csv`.

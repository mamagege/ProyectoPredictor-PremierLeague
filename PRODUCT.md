# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Aficionado curioso de la Premier League (hispanohablante) que quiere ver qué tan probable es cada desenlace de un partido (Victoria Local / Empate / Victoria Visitante) y entender por qué, sin ser experto en machine learning. Secundario: el evaluador del curso PTIA (ECI), que revisa rigor y límites del modelo en la pantalla técnica.

## Product Purpose

Predictor EPL estima la distribución de probabilidad pre-partido del resultado de un encuentro de la English Premier League con una red neuronal profunda (Residual Deep MLP de 3 bloques, softmax de 3 clases calibrada con temperature scaling). El usuario elige equipo local, visitante, fecha opcional y cuotas opcionales; recibe tres probabilidades que suman 100 % y el contexto que las explica (Elo, forma, descanso, historial directo). Éxito: que el usuario lea la incertidumbre, no solo un "ganador".

## Positioning

Muestra probabilidades calibradas y sus límites, no un veredicto. El modelo tiene exactitud 56,7 % y log loss 0,952 en 1.520 partidos nunca vistos (2021/22–2024/25), muy cerca de las cuotas de Bet365 y de la regresión logística (56,9 %) pero sin superarlas, y rara vez marca el empate como lo más probable; la interfaz lo dice abiertamente en lugar de esconderlo.

## Operating Context

Proyecto del curso PTIA, Grupo 04, Escuela Colombiana de Ingeniería Julio Garavito. Hito 2 pide prototipo de interfaz navegable; Hito 3 un MVP funcional con demo en video. El frontend consume una API FastAPI local (`/api/teams`, `/api/predict`, `/api/metrics`) que envuelve `prediction_service.py`. Datos hasta agosto de 2026 (inicio de la temporada 2026/27); la API toma como "actuales" los 20 equipos de la temporada más reciente del historial.

## Capabilities and Constraints

- Entradas: equipo local, equipo visitante, fecha opcional (YYYY-MM-DD), cuotas decimales opcionales [local, empate, visitante], todas > 1,00. Sin cuotas el modelo deriva una probabilidad de mercado desde el Elo; la UI debe decirlo.
- Salidas: probabilidades en %, clase más probable, estado de cada equipo (Elo, forma de 5, goles a favor/en contra, descanso, puntos y diferencia de gol de la temporada), historial directo en %.
- Errores esperables: equipo desconocido, mismo equipo en ambos lados, historial insuficiente antes de la fecha.
- El empate casi nunca es la clase más probable (F1 de empate 0,11 en test con argmax); no presentarlo como fallo.
- Idioma de la interfaz: español. Equipos con nombres canónicos del dataset (Man City, Nott'm Forest, Wolves…).

## Brand Commitments

Producto con identidad propia; la Escuela Colombiana de Ingeniería Julio Garavito aparece de forma discreta como respaldo académico (logo en la plantilla del curso: `Plantilla_Proyectos_PTIA_ECI_LaTeX.zip`, `img/logo_eci.png`). Tono analítico: sin lenguaje de apuestas ni "mejor pick"; las cuotas son un dato de entrada opcional.

## Evidence on Hand

`models/training_summary.json` con benchmark real (Dummy, Bet365, Regresión Logística, HistGradientBoosting, Deep MLP del Hito 2, Residual Deep MLP sin calibrar y calibrado, ablación sin cuotas), matriz de confusión y métricas de test. Datos de 3 fuentes tabulares en `datasets/`. No hay testimonios, usuarios reales ni escudos de clubes con licencia: no inventarlos.

## Product Principles

1. La incertidumbre es el producto: tres probabilidades siempre juntas, nunca un ganador solitario.
2. Honestidad sobre el modelo: límites y métricas visibles, no escondidos en un pie de página.
3. Explicar antes que impresionar: cada número del contexto debe poder leerse sin saber ML.
4. Entrada mínima: dos equipos bastan; fecha y cuotas son opcionales y se indica qué cambia con ellas.
5. Nada de incitar a apostar.

## Accessibility & Inclusion

Contraste y navegación por teclado completos; las probabilidades no dependen solo del color (etiquetas y valores numéricos siempre presentes). Usable en móvil.

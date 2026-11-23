# ADR 0001: frontend, API y sistema de diseño

Estado: aceptado · Fecha: 2026-11-22

## Contexto

El modelo (Deep MLP) y `prediction_service.py` ya existían como backend de ML sin interfaz. El Hito 2 pide un prototipo de interfaz navegable y el Hito 3 un MVP funcional con demo en video. Una persona del equipo asume el frontend.

## Decisiones

1. **API propia en FastAPI (`api/main.py`)** que envuelve `EPLPredictor` y expone `GET /api/teams`, `POST /api/predict`, `GET /api/metrics` y `GET /api/health`. Con `EPL_MOCK=1` funciona sin TensorFlow ni datasets, solo para diseñar la interfaz; las respuestas de ejemplo llevan `mock: true` y la interfaz las etiqueta «Datos de ejemplo».
2. **Frontend en Vite + React + TypeScript + Tailwind 4.** Es una SPA de un solo bundle sin renderizado en servidor: no necesita rutas de servidor y las tres pantallas (Predictor, Modelo, Privacidad) se resuelven con `location.hash`.
3. **Mismo origen.** El frontend llama a `/api/*` y Vite lo reenvía al puerto 8000. No hay cookies ni sesión, así que no hace falta manejo de tokens. CORS solo se permite para `localhost:5173` en desarrollo.
4. **Tokens por rol.** Los colores son canales RGB en `:root` (`--canvas`, `--surface`, `--line`, `--ink`, `--accent`…) y Tailwind los lee como `rgb(var(--x))`; un modo claro solo cambia esos valores. Un solo acento (`accent`) para lo que se puede pulsar y tres colores reservados (`local`, `draw`, `away`) que significan únicamente Local, Empate y Visitante. Los tokens de movimiento (curva y duraciones) viven en el mismo lugar.
5. **Funciones puras en `src/lib/`** (frecuencias, avisos de datos antiguos, comparación, curvas, formato) con pruebas de comportamiento en Vitest. Los componentes solo aplican el resultado.
6. **Cuatro estados por vista:** cargando (cifras pulsantes en la forma del contenido, esqueleto en Modelo), vacío, error con causa y «Reintentar» solo si reintentar puede resolverlo (`ApiRequestError.retriable`), y datos de ejemplo etiquetados. Sin sesión no aplica.
7. **Animación de entrada** (`Intro.tsx`): un solo bucle `requestAnimationFrame` con reloj propio, pausa con la pestaña oculta, sin movimiento con `prefers-reduced-motion` y en cada carga de la página (no se guarda nada en el navegador).
8. **Privacidad real:** la página `#privacidad` describe lo que la aplicación hace: ningún tercero, ninguna cookie ni almacenamiento local, tipografías autoalojadas.
9. **Fechas, partidos y calendario (`api/matches.py`).** `GET /api/dates` lista las fechas con partidos del historial y alimenta el selector de fecha; `GET /api/matches` devuelve los partidos jugados de un día (o los últimos 10) con su resultado real, para comparar el pronóstico con lo que pasó; `GET /api/fixtures` lee un calendario opcional `datasets/fixtures.csv` (columnas `date,home_team,away_team[,round]`, plantilla en `datasets/fixtures.template.csv`) y solo muestra filas posteriores al último partido del historial. Los datos del proyecto solo contienen partidos ya jugados (hasta el 31 de agosto de 2026), así que sin ese archivo los próximos partidos no existen y la interfaz lo dice en lugar de inventarlos.
10. **Capacidades del servicio que la interfaz ahora aprovecha.** `EPLPredictor` ya calculaba el pronóstico con umbrales bayesianos (`pronostico_bayesiano`) y la calibración del modelo (ECE y curvas de confiabilidad en `training_summary.json`), pero el adaptador `api/main.py` los descartaba. Ahora `POST /api/predict` devuelve `predicted_bayesian` y `GET /api/metrics` devuelve un bloque `calibration` del modelo desplegado. La interfaz muestra el pronóstico bayesiano solo cuando difiere del más probable y dibuja el diagrama de confiabilidad en la pantalla Modelo. Las probabilidades son las mismas en ambos modos: cambia únicamente qué resultado se marca como pronóstico discreto.

## Consecuencias

- La API carga TensorFlow y los datasets al arrancar (decenas de segundos); la interfaz muestra «Equipos no disponibles» con reintento mientras tanto.
- El modelo no es el mejor en todas las métricas (la regresión logística lo supera por poco en exactitud y log loss); la pantalla Modelo lo muestra tal cual y explica por qué se usa la red profunda.
- La «frecuencia 2021–25» sale de la matriz de confusión del conjunto de prueba, no de toda la historia.

## Pendientes antes de desplegar

- [ ] Configurar los orígenes CORS de `api/main.py` por variable de entorno (hoy solo `localhost`; `src/api.py` ya usa `CORS_ALLOW_ORIGINS`).
- [ ] Limitar la tasa de peticiones de la API y definir cómo se aloja TensorFlow (memoria y tiempo de arranque).
- [x] Pruebas de la API: `tests/test_frontend_api.py` cubre `api/main.py` con `TestClient` (httpx).
- [ ] Una prueba de extremo a extremo del flujo principal.
- [x] Versión de scikit-learn: el modelo se entrenó con 1.9.0 (`models/training_summary.json`) y `requirements.txt` la fija en 1.9.0.
- [x] README: corregido; el modelo del Hito 3 usa 45 características, igual que `feature_names.json`.
- [ ] Revisar licencias de los tres datasets de Kaggle antes de publicar.
- [ ] Probar en un dispositivo real y con lector de pantalla.

## Trampas que nos costaron tiempo

- `.gitignore` de Python ignora cualquier carpeta `lib/`: se agregó la excepción `!frontend/src/lib/`.
- Un reinicio CSS fuera de `@layer` (`button { color: inherit }`) anula las utilidades de Tailwind: el botón principal salía con texto claro sobre azul. Va en `@layer base`.
- Los textos `sr-only` son absolutos: dentro de una tabla con `overflow-x: auto` ensanchan la página en móvil si el contenedor no es `relative`.
- Las rejillas necesitan `minmax(0, 1fr)` para que las tablas anchas no desborden la columna.
- Git avisa de finales de línea CRLF en Windows; no cambia el contenido pero conviene normalizar antes de editar con reemplazos exactos.

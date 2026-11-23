# Interfaz web del Predictor EPL

Aplicación de una sola página (Vite + React + TypeScript + Tailwind) que consume la API de `api/main.py`. Contexto de producto en [`../PRODUCT.md`](../PRODUCT.md) y sistema de diseño en [`../DESIGN.md`](../DESIGN.md).

## Desarrollo

Desde la raíz del repositorio, con la API levantada en el puerto 8000 (`python -m uvicorn api.main:app --port 8000`):

```bash
npm --prefix frontend ci
npm --prefix frontend run dev      # http://localhost:5173
```

Vite reenvía las peticiones `/api/*` a `http://127.0.0.1:8000` (ver `vite.config.ts`).

## Scripts

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo con recarga en caliente |
| `npm run build` | Revisión de tipos (`tsc -b`) y compilación de producción en `dist/` |
| `npm run lint` | Linter (oxlint) |
| `npm run preview` | Sirve la compilación de `dist/` |

## Estructura

```text
src/
├── api.ts                 # Tipos del contrato con la API y cliente fetch
├── App.tsx                # Navegación entre las pantallas Predictor y Modelo
├── views/
│   ├── PredictorView.tsx  # Formulario + pronóstico + condiciones previas
│   └── ModelView.tsx      # Benchmark, matriz de confusión y metodología
├── components/
│   ├── MatchForm.tsx      # Equipos, fecha y cuotas con validación
│   ├── Forecast.tsx       # Las tres probabilidades frente a la frecuencia histórica
│   ├── Conditions.tsx     # Estado de cada equipo e historial directo
│   └── Intro.tsx          # Animación de entrada (solo en la primera visita)
└── lib/format.ts          # Formato de números y fechas en español
```

Las cifras del modelo (exactitud, partidos de prueba, variables, calibración) se leen de `/api/metrics` en lugar de estar escritas en el código.

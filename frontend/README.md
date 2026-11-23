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
| `npm test` | Pruebas de las funciones de `src/lib/` (Vitest) |
| `npm run preview` | Sirve la compilación de `dist/` |

## Estructura

```text
src/
├── api.ts                 # Tipos del contrato con la API y cliente fetch
├── App.tsx                # Navegación por #hash entre Predictor, Modelo y Privacidad
├── views/
│   ├── PredictorView.tsx  # Formulario + pronóstico + condiciones previas + partidos
│   ├── ModelView.tsx      # Benchmark, matriz de confusión y metodología
│   └── PrivacyView.tsx    # Qué hace la aplicación con los datos
├── components/
│   ├── MatchForm.tsx      # Equipos, fecha (selector de fechas disponibles) y cuotas
│   ├── MatchesPanel.tsx   # Próximos partidos (calendario opcional) y partidos jugados
│   ├── Forecast.tsx       # Las tres probabilidades frente a su frecuencia en 2021–25
│   ├── Conditions.tsx     # Estado de cada equipo e historial directo
│   ├── ErrorNotice.tsx    # Aviso de error con causa y botón «Reintentar»
│   └── Intro.tsx          # Animación de entrada (en cada carga de la página)
└── lib/                   # Funciones puras, sin React
    ├── format.ts          # Números y fechas en español (es-CO)
    ├── rates.ts           # Frecuencia de cada resultado a partir de la matriz de confusión
    ├── stale.ts           # Aviso cuando el último partido de un equipo es muy antiguo
    ├── compare.ts         # Qué equipo va mejor en cada indicador
    ├── matches.ts         # Resultado real y marcador de un partido jugado
    ├── useFetch.ts        # Carga de datos con estado de carga, error y reintento
    ├── bezier.ts          # Curvas cubic-bezier de la intro
    └── lib.test.ts        # Pruebas de todo lo anterior (Vitest)
```

Las decisiones de arquitectura (API propia, mismo origen, tokens de color, estados de cada vista) están en [`../docs/adr/0001-frontend-y-api.md`](../docs/adr/0001-frontend-y-api.md).

Las cifras del modelo (exactitud, partidos de prueba, variables, calibración) se leen de `/api/metrics` en lugar de estar escritas en el código.

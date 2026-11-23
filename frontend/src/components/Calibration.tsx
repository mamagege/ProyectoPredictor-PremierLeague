import type { Calibration as CalibrationData } from '../api'
import { pointRadius, reliabilityPoints } from '../lib/calibration'
import { num2, pct1 } from '../lib/format'

const SERIES = [
  { key: 'H', label: 'Local', color: 'var(--color-local)' },
  { key: 'D', label: 'Empate', color: 'var(--color-draw)' },
  { key: 'A', label: 'Visitante', color: 'var(--color-away)' },
] as const

const W = 440
const H = 350
const L = 52
const R = 16
const T = 12
const B = 48
const PW = W - L - R
const PH = H - T - B
const px = (v: number) => L + v * PW
const py = (v: number) => T + (1 - v) * PH
const TICKS = [0, 0.25, 0.5, 0.75, 1]

function Chart({ c }: { c: CalibrationData }) {
  const bins = c.classwise_bins
  if (!bins) return null
  const series = SERIES.map((s) => ({ ...s, pts: reliabilityPoints(bins[s.key]) }))
  const maxCount = Math.max(1, ...series.flatMap((s) => s.pts.map((p) => p.count)))
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Curvas de calibración por resultado: frecuencia observada frente a la probabilidad que dio el modelo. Cuanto más cerca de la diagonal, mejor calibrado."
      className="h-auto w-full max-w-xl"
    >
      {TICKS.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={py(t)} y2={py(t)} stroke="var(--color-line)" strokeWidth="1" />
          <line y1={T} y2={H - B} x1={px(t)} x2={px(t)} stroke="var(--color-line)" strokeWidth="1" />
          <text x={L - 8} y={py(t) + 4} textAnchor="end" fontSize="13" fill="var(--color-ink-muted)">
            {Math.round(t * 100)} %
          </text>
          <text x={px(t)} y={H - B + 18} textAnchor="middle" fontSize="13" fill="var(--color-ink-muted)">
            {Math.round(t * 100)} %
          </text>
        </g>
      ))}
      {/* Diagonal: calibración perfecta */}
      <line
        x1={px(0)}
        y1={py(0)}
        x2={px(1)}
        y2={py(1)}
        stroke="var(--color-ink-muted)"
        strokeWidth="1.5"
        strokeDasharray="5 5"
      />
      {series.map((s) => (
        <g key={s.key}>
          <polyline
            fill="none"
            stroke={s.color}
            strokeWidth="2.5"
            strokeLinejoin="round"
            points={s.pts.map((p) => `${px(p.x)},${py(p.y)}`).join(' ')}
          />
          {s.pts.map((p) => (
            <circle
              key={p.x}
              cx={px(p.x)}
              cy={py(p.y)}
              r={pointRadius(p.count, maxCount)}
              fill={s.color}
              stroke="var(--color-surface)"
              strokeWidth="1.5"
            >
              <title>{`${s.label}: el modelo dio ${pct1(p.x * 100)} y ocurrió ${pct1(p.y * 100)} (${p.count} partidos)`}</title>
            </circle>
          ))}
        </g>
      ))}
      <text x={px(0.5)} y={H - 6} textAnchor="middle" fontSize="14" fill="var(--color-ink)">
        Probabilidad que dio el modelo
      </text>
      <text transform={`translate(14 ${py(0.5)}) rotate(-90)`} textAnchor="middle" fontSize="14" fill="var(--color-ink)">
        Frecuencia observada
      </text>
    </svg>
  )
}

export default function Calibration({ c }: { c: CalibrationData }) {
  const tune = c.bayesian_tuning_val
  return (
    <section aria-labelledby="calib-title" className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 id="calib-title" className="text-balance font-display text-2xl font-bold leading-tight">
        ¿Son fiables los porcentajes?
      </h2>
      <p className="mt-1 max-w-[65ch] text-base text-ink-muted">
        Cuando el modelo dice 60 %, ese resultado debería ocurrir cerca del 60 % de las veces. Cada punto agrupa partidos
        de prueba con probabilidades parecidas; cuanto más cerca de la diagonal, mejor calibrado.
      </p>

      <div className="mt-5 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
        <div>
          <ul className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-base">
            {SERIES.map((s) => (
              <li key={s.key} className="flex items-center gap-2">
                <span aria-hidden className="size-2.5 rounded-full" style={{ background: s.color }} />
                {s.label}
              </li>
            ))}
            <li className="flex items-center gap-2 text-ink-muted">
              <span aria-hidden className="w-5 border-t-2 border-dashed border-ink-muted" />
              Calibración perfecta
            </li>
          </ul>
          <Chart c={c} />
        </div>

        <dl className="grid gap-4 text-base">
          {c.top_label_ece !== null && (
            <div>
              <dt className="font-bold">Error de calibración (ECE)</dt>
              <dd className="mt-0.5 text-ink-muted">
                {pct1(c.top_label_ece * 100)} en el resultado que el modelo elige
                {c.classwise_ece &&
                  `; por resultado: Local ${pct1(c.classwise_ece.H * 100)}, Empate ${pct1(c.classwise_ece.D * 100)}, Visitante ${pct1(c.classwise_ece.A * 100)}`}
                . Más bajo es mejor.
              </dd>
            </div>
          )}
          {c.temperature !== null && (
            <div>
              <dt className="font-bold">Ajuste por temperatura</dt>
              <dd className="mt-0.5 text-ink-muted">
                T = {num2(c.temperature)}, calculada en validación: suaviza la confianza excesiva de la red.
              </dd>
            </div>
          )}
          {tune?.val_base_f1_D !== undefined && tune.val_tuned_f1_D !== undefined && (
            <div>
              <dt className="font-bold">Umbrales bayesianos (opcionales)</dt>
              <dd className="mt-0.5 text-ink-muted">
                En validación suben el F1 del empate de {pct1(tune.val_base_f1_D * 100)} a {pct1(tune.val_tuned_f1_D * 100)}
                {tune.val_base_accuracy !== undefined && tune.val_tuned_accuracy !== undefined
                  ? ` y bajan la exactitud de ${pct1(tune.val_base_accuracy * 100)} a ${pct1(tune.val_tuned_accuracy * 100)}`
                  : ''}
                . No cambian las probabilidades, solo qué resultado se marca como pronóstico.
              </dd>
            </div>
          )}
        </dl>
      </div>
    </section>
  )
}

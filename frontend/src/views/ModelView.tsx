import { Check } from 'lucide-react'
import type { MetricsResponse, ModelResult } from '../api'
import { num0, num2, pct1 } from '../lib/format'

const CLASSES = ['Local', 'Empate', 'Visitante']

function best(rows: ModelResult[], pick: (r: ModelResult) => number, dir: 'max' | 'min') {
  const vals = rows.map(pick)
  return dir === 'max' ? Math.max(...vals) : Math.min(...vals)
}

function Benchmark({ m }: { m: MetricsResponse }) {
  const rows = m.test_results
  const cols: { label: string; hint: string; pick: (r: ModelResult) => number; fmt: (n: number) => string; dir: 'max' | 'min' }[] = [
    { label: 'Exactitud', hint: 'más alto es mejor', pick: (r) => r.accuracy, fmt: (n) => pct1(n * 100), dir: 'max' },
    { label: 'Log loss', hint: 'más bajo es mejor', pick: (r) => r.log_loss, fmt: (n) => n.toFixed(3).replace('.', ','), dir: 'min' },
    { label: 'Brier', hint: 'más bajo es mejor', pick: (r) => r.brier_score, fmt: (n) => n.toFixed(3).replace('.', ','), dir: 'min' },
    { label: 'F1 del empate', hint: 'más alto es mejor', pick: (r) => r.f1_D, fmt: (n) => pct1(n * 100), dir: 'max' },
  ]
  return (
    <section aria-labelledby="bench-title" className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 id="bench-title" className="font-display text-2xl font-bold leading-tight">Comparación con otros modelos</h2>
      <p className="mt-1 text-ink-muted">Los cuatro se evaluaron sobre los mismos partidos nunca vistos. La marca señala el mejor de cada columna.</p>
      <div className="relative -mx-1 mt-4 overflow-x-auto px-1">
        <table className="w-full min-w-[560px] border-collapse">
          <caption className="sr-only">Métricas de cada modelo en el conjunto de prueba</caption>
          <thead>
            <tr className="border-b border-line text-left text-sm text-ink-muted">
              <th scope="col" className="py-2 pr-3 font-bold">Modelo</th>
              {cols.map((c) => (
                <th key={c.label} scope="col" className="px-2 py-2 text-right font-bold">
                  {c.label}
                  <span className="block font-normal">{c.hint}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const used = r.model.startsWith('Deep MLP')
              return (
                <tr key={r.model} className={`border-b border-line last:border-0 ${used ? 'bg-raised' : ''}`}>
                  <th scope="row" className="py-3 pl-2 pr-3 text-left font-bold">
                    {r.model}
                    {used && <span className="block text-sm font-normal text-ink-muted">El que usa esta aplicación</span>}
                  </th>
                  {cols.map((c) => {
                    const isBest = c.pick(r) === best(rows, c.pick, c.dir)
                    return (
                      <td key={c.label} className={`px-2 py-3 text-right ${isBest ? 'font-bold text-ink' : 'text-ink-muted'}`}>
                        <span className="inline-flex items-center justify-end gap-1.5">
                          {isBest && <Check aria-hidden className="size-4 text-local" />}
                          {c.fmt(c.pick(r))}
                          {isBest && <span className="sr-only"> (mejor)</span>}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-sm text-ink-muted">
        Las diferencias entre los modelos entrenados son pequeñas. Todos mejoran claramente al modelo ingenuo que siempre
        predice victoria local. Esta aplicación usa la red neuronal profunda porque es el componente central del proyecto
        del curso; la regresión logística la supera por poco en exactitud y log loss.
      </p>
    </section>
  )
}

function Confusion({ m }: { m: MetricsResponse }) {
  const cm = m.confusion_matrix
  const norm = m.confusion_matrix_norm
  return (
    <section aria-labelledby="cm-title" className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 id="cm-title" className="font-display text-2xl font-bold leading-tight">Aciertos y errores por resultado</h2>
      <p className="mt-1 text-ink-muted">
        Cada fila es lo que pasó de verdad; cada columna, lo que el modelo marcó como más probable. En cada celda: partidos y
        porcentaje de esa fila.
      </p>
      <div className="relative mt-4 overflow-x-auto">
        <table className="w-full min-w-[420px] border-separate border-spacing-1.5 text-center">
          <caption className="sr-only">Matriz de confusión del modelo en el conjunto de prueba</caption>
          <thead>
            <tr className="text-sm text-ink-muted">
              <td />
              {CLASSES.map((c) => (
                <th key={c} scope="col" className="pb-1 font-bold">Marcó {c.toLowerCase()}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cm.map((row, i) => (
              <tr key={i}>
                <th scope="row" className="pr-2 text-right text-sm font-bold text-ink-muted">Real: {CLASSES[i].toLowerCase()}</th>
                {row.map((v, j) => {
                  const ok = i === j
                  return (
                    <td
                      key={j}
                      className={`rounded-md px-2 py-3 ${ok ? 'border-2 border-ink' : 'border border-line'}`}
                      style={{ background: `color-mix(in srgb, var(--color-ink) ${Math.round(norm[i][j] * 40)}%, var(--color-raised))` }}
                    >
                      <span className="block font-display text-2xl font-bold leading-none">{num0(v)}</span>
                      <span className="mt-1 block text-sm">{pct1(norm[i][j] * 100)}</span>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-sm text-ink-muted">
        Las celdas con borde blanco, en la diagonal, son aciertos; cuanto más claro el fondo, mayor la proporción de esa fila.
        Los empates son difíciles de anticipar: el modelo nunca marcó el empate como lo más probable (columna del medio en
        cero), por eso conviene leer siempre las tres probabilidades y no solo el resultado destacado.
      </p>
    </section>
  )
}

function Method({ m }: { m: MetricsResponse }) {
  const total = m.confusion_matrix.flat().reduce((a, b) => a + b, 0)
  const items = [
    ['Partidos de prueba', `${num0(total)} partidos de 2021 a 2025 que el modelo nunca vio`],
    ['Orden cronológico', 'Entrenamiento 2000–2017, validación 2017–2021, prueba 2021–2025: nada del futuro entra al pasado'],
    ['Variables de entrada', '40 datos previos al partido: Elo, forma, goles, descanso, historial directo y mercado'],
    ['Red neuronal', `${m.selected_architecture}, salida de tres probabilidades; ${num0(m.epochs_trained)} épocas de entrenamiento`],
  ]
  return (
    <section aria-labelledby="method-title" className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 id="method-title" className="font-display text-2xl font-bold leading-tight">Cómo se construyó</h2>
      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        {items.map(([t, d]) => (
          <div key={t}>
            <dt className="font-bold">{t}</dt>
            <dd className="mt-0.5 text-ink-muted">{d}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export default function ModelView({ metrics, error }: { metrics: MetricsResponse | null; error: string | null }) {
  const mlp = metrics?.test_results.find((r) => r.model.startsWith('Deep MLP'))
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-5">
      <header>
        <h1 className="font-display text-4xl font-bold leading-tight sm:text-5xl">Qué tan bien pronostica</h1>
        {mlp && (
          <p className="mt-3 max-w-[65ch] text-lg text-ink-muted">
            Acierta el resultado en {pct1(mlp.accuracy * 100)} de los partidos nunca vistos, frente al{' '}
            {pct1((metrics!.test_results[0].accuracy) * 100)} de un modelo ingenuo que siempre elige victoria local. Más
            que acertar siempre, entrega probabilidades: su log loss es {num2(mlp.log_loss)}.
          </p>
        )}
      </header>
      {error && (
        <p role="alert" className="rounded-md border border-danger/50 bg-danger/10 px-3 py-2 text-danger">
          No se pudieron cargar las métricas: {error}
        </p>
      )}
      {!metrics && !error && <p className="text-ink-muted">Cargando métricas…</p>}
      {metrics && (
        <>
          <Benchmark m={metrics} />
          <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 xl:grid-cols-2">
            <Confusion m={metrics} />
            <Method m={metrics} />
          </div>
        </>
      )}
    </div>
  )
}

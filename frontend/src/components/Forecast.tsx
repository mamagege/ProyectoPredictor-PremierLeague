import { ArrowDown, ArrowUp, Info, TriangleAlert } from 'lucide-react'
import type { Outcome, PredictResponse } from '../api'
import { formatDate, num0, num1, pct1, signed1 } from '../lib/format'

export type BaseRates = Record<Outcome, number>

interface Props {
  result: PredictResponse | null
  previous: PredictResponse | null
  busy: boolean
  error: string | null
  baseRates: BaseRates | null
  accuracy: number | null
  testMatches: number | null
  onOpenModel: () => void
}

const TONE: Record<Outcome, string> = {
  home: 'var(--color-local)',
  draw: 'var(--color-draw)',
  away: 'var(--color-away)',
}
const ORDER: Outcome[] = ['home', 'draw', 'away']

function Row({
  outcome,
  label,
  value,
  base,
  prev,
  index,
  winner,
}: {
  outcome: Outcome
  label: string
  value: number | null
  base: number | null
  prev: number | null
  index: number
  winner: boolean
}) {
  const vsNormal = value !== null && base !== null ? value - base : null
  const vsPrev = value !== null && prev !== null ? value - prev : null
  const whole = value === null ? '–' : num1(value)
  return (
    <li className="py-5 first:pt-0 last:pb-0">
      <div className="flex items-baseline justify-between gap-4">
        <h3 className={`min-w-0 break-words text-base sm:text-lg ${winner ? 'font-bold' : 'text-muted font-bold'}`}>
          <span aria-hidden className="mr-2 inline-block size-2.5 rounded-full align-middle" style={{ background: TONE[outcome] }} />
          {label}
          {winner && <span className="ml-2 text-sm font-normal text-muted">más probable</span>}
        </h3>
        <p className="shrink-0 font-display text-5xl font-bold leading-none sm:text-6xl" style={{ color: value === null ? 'var(--color-line)' : TONE[outcome] }}>
          {whole}
          <span className="ml-1 text-2xl text-muted sm:text-3xl">%</span>
        </p>
      </div>

      {/* Escala 0–100 con la marca de la "normal" histórica */}
      <div
        role="img"
        aria-label={
          value === null
            ? `${label}: sin calcular`
            : `${label}: ${pct1(value)}${base !== null ? `, en los partidos de 2021 a 2025 ocurrió el ${pct1(base)} de las veces` : ''}`
        }
        className="relative mt-3 h-3 rounded-sm bg-raised"
      >
        {value !== null && (
          <div
            className="bar-fill absolute inset-y-0 left-0 rounded-sm"
            style={{ width: `${value}%`, background: TONE[outcome], ['--i' as string]: index }}
          />
        )}
        {base !== null && (
          <span
            aria-hidden
            className="absolute -top-1.5 h-6 w-0.5 rounded-full bg-text"
            style={{ left: `calc(${base}% - 1px)` }}
          />
        )}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        <span>{base !== null ? `Frecuencia 2021–25: ${pct1(base)}` : 'Frecuencia 2021–25: …'}</span>
        {vsNormal !== null && (
          <span className="inline-flex items-center gap-1 text-text">
            {vsNormal >= 0 ? <ArrowUp aria-hidden className="size-3.5" /> : <ArrowDown aria-hidden className="size-3.5" />}
            {signed1(vsNormal)} pts
          </span>
        )}
        {vsPrev !== null && Math.abs(vsPrev) >= 0.05 && (
          <span className="delta-chip inline-flex items-center rounded px-1.5 py-0.5 text-text">
            {signed1(vsPrev)} pts vs. cálculo anterior
          </span>
        )}
      </div>
    </li>
  )
}

const STALE_DAYS = 400

/** Avisos cuando el estado de un equipo viene de datos muy viejos respecto a la fecha del pronóstico. */
function staleWarnings(r: PredictResponse): string[] {
  const ref = new Date(r.match_date ?? r.data_end ?? '')
  if (Number.isNaN(ref.getTime())) return []
  const out: string[] = []
  for (const [team, last] of [
    [r.home_team, r.home_last_match],
    [r.away_team, r.away_last_match],
  ] as const) {
    if (!last) continue
    const days = (ref.getTime() - new Date(last).getTime()) / 86_400_000
    if (days > STALE_DAYS) {
      out.push(`${team} no tiene partidos registrados desde ${formatDate(last)}: su estado viene de datos de esa época.`)
    }
  }
  return out
}

export default function Forecast({ result, previous, busy, error, baseRates, accuracy, testMatches, onOpenModel }: Props) {
  const warnings = result ? [...(result.warnings ?? []), ...staleWarnings(result)] : []
  const samePair =
    result && previous && previous.home_team === result.home_team && previous.away_team === result.away_team
  const prev = samePair ? previous : null

  const labels: Record<Outcome, string> = {
    home: result ? `Victoria de ${result.home_team}` : 'Victoria local',
    draw: 'Empate',
    away: result ? `Victoria de ${result.away_team}` : 'Victoria visitante',
  }

  return (
    <section
      aria-labelledby="forecast-title"
      aria-busy={busy}
      className={`rounded-lg border border-line bg-panel p-5 transition-opacity sm:p-6 ${busy ? 'opacity-60' : ''}`}
    >
      {result && !busy && (
        <p role="status" aria-live="polite" className="sr-only">
          {`Pronóstico ${result.home_team} contra ${result.away_team}: victoria de ${result.home_team} ${pct1(result.probabilities.home)}, empate ${pct1(result.probabilities.draw)}, victoria de ${result.away_team} ${pct1(result.probabilities.away)}.`}
        </p>
      )}
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id="forecast-title" className="font-display text-2xl font-bold leading-tight">
          {result ? `${result.home_team} – ${result.away_team}` : 'Pronóstico del partido'}
        </h2>
        {result && (
          <p className="text-sm text-muted">
            {result.match_date ? formatDate(result.match_date) : 'Datos más recientes disponibles'}
          </p>
        )}
      </div>

      {error ? (
        <div role="alert" className="mt-5 flex gap-3 rounded-md border border-danger/50 bg-danger/10 p-4 text-danger">
          <TriangleAlert aria-hidden className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-bold">No se pudo calcular el pronóstico</p>
            <p className="mt-1 text-sm">{error}</p>
            {error.startsWith('Historial insuficiente') && (
              <p className="mt-2 text-sm text-text">
                Prueba con una fecha posterior (los datos empiezan en agosto de 2000) o deja la fecha vacía.
              </p>
            )}
          </div>
        </div>
      ) : (
        <>
          {!result && (
            <p className="mt-1 text-muted">
              Elige dos equipos y calcula. La marca blanca de cada barra indica con qué frecuencia ocurrió ese resultado en
              los partidos de 2021 a 2025.
            </p>
          )}
          {result && (
            <p className="mt-1 text-muted">
              {result.odds_used
                ? 'Calculado con las cuotas que ingresaste.'
                : 'Sin cuotas: el mercado se estimó a partir del Elo.'}{' '}
              La marca blanca indica con qué frecuencia ocurrió ese resultado en los partidos de 2021 a 2025.
            </p>
          )}

          {warnings.length > 0 && (
            <div role="status" className="mt-4 flex gap-3 rounded-md border border-draw/50 bg-draw/10 p-3 text-sm text-draw">
              <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
              <div>
                {warnings.map((w) => (
                  <p key={w}>{w}</p>
                ))}
                <p className="mt-1 text-text">Tómalo como una estimación poco fiable.</p>
              </div>
            </div>
          )}

          {result && (
            <div
              aria-hidden
              key={`stack-${result.home_team}-${result.away_team}-${result.probabilities.home}`}
              className="mt-6 flex h-4 gap-0.5 overflow-hidden rounded-sm"
            >
              {ORDER.map((o, i) => (
                <div
                  key={o}
                  className="bar-fill"
                  style={{ width: `${result.probabilities[o]}%`, background: TONE[o], ['--i' as string]: i }}
                />
              ))}
            </div>
          )}

          <ul key={result ? `${result.home_team}-${result.away_team}-${result.probabilities.home}` : 'empty'} className="mt-6 divide-y divide-line">
            {ORDER.map((o, i) => (
              <Row
                key={o}
                outcome={o}
                label={labels[o]}
                value={result ? result.probabilities[o] : null}
                base={baseRates ? baseRates[o] : null}
                prev={prev ? prev.probabilities[o] : null}
                index={i}
                winner={result?.predicted === o}
              />
            ))}
          </ul>

          <div className="mt-6 flex gap-3 border-t border-line pt-4 text-sm text-muted">
            <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
            <p>
              Son tres probabilidades que suman 100 %, no un veredicto.
              {accuracy !== null && (
                <>
                  {' '}
                  En {testMatches !== null ? num0(testMatches) : 'los'} partidos nunca vistos el modelo acertó el{' '}
                  {pct1(accuracy * 100)}, y casi nunca marca el empate
                  como lo más probable.{' '}
                  <button type="button" onClick={onOpenModel} className="font-bold text-action underline hover:brightness-125">
                    Ver cómo se evaluó
                  </button>
                </>
              )}
            </p>
          </div>
        </>
      )}
    </section>
  )
}

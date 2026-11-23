import { ArrowDown, ArrowUp, Check, Info, Scale, TriangleAlert, X } from 'lucide-react'
import ErrorNotice from './ErrorNotice'
import type { Outcome, PlayedMatch, PredictResponse } from '../api'
import { formatDate, num0, num1, pct1, signed1 } from '../lib/format'
import { outcomeOf, predictedRight, score } from '../lib/matches'
import type { BaseRates } from '../lib/rates'
import { staleWarnings } from '../lib/stale'

interface Props {
  result: PredictResponse | null
  previous: PredictResponse | null
  busy: boolean
  error: string | null
  baseRates: BaseRates | null
  accuracy: number | null
  testMatches: number | null
  /** Resultado real cuando el partido elegido ya se jugó. */
  actual?: PlayedMatch | null
  onOpenModel: () => void
  /** Presente solo cuando el error se puede reintentar (sin conexión o fallo del servidor). */
  onRetry?: (() => void) | null
}

const TONE: Record<Outcome, string> = {
  home: 'var(--color-local)',
  draw: 'var(--color-draw)',
  away: 'var(--color-away)',
}
const CODE: Record<Outcome, string> = {
  home: '1',
  draw: 'X',
  away: '2',
}
const ORDER: Outcome[] = ['home', 'draw', 'away']

function OutcomeCard({
  outcome,
  label,
  value,
  base,
  prev,
  index,
  winner,
  loading,
}: {
  outcome: Outcome
  label: string
  value: number | null
  base: number | null
  prev: number | null
  index: number
  winner: boolean
  loading: boolean
}) {
  const vsNormal = value !== null && base !== null ? value - base : null
  const vsPrev = value !== null && prev !== null ? value - prev : null
  const whole = value === null ? '–' : num1(value)
  const oddImplied = value && value > 0 ? (100 / value).toFixed(2) : null

  return (
    <li
      className={`flex flex-col justify-between rounded-md border p-3.5 transition-colors ${
        winner ? 'border-accent bg-raised/90' : 'border-line bg-canvas/60'
      }`}
    >
      <div>
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 rounded bg-surface px-2 py-0.5 font-display text-xs font-bold uppercase tracking-wider text-ink-muted">
            <span aria-hidden className="size-2 rounded-full" style={{ background: TONE[outcome] }} />
            {CODE[outcome]}
          </span>
          {winner ? (
            <span className="rounded bg-accent/20 px-2 py-0.5 text-[11px] font-bold text-accent">Más probable</span>
          ) : (
            oddImplied && <span className="text-xs text-ink-muted">~{oddImplied}</span>
          )}
        </div>

        <h3 className="mt-2 truncate text-sm font-bold text-ink" title={label}>
          {label}
        </h3>

        <p
          className={`mt-1 font-display text-4xl font-bold leading-none sm:text-5xl ${
            loading ? 'animate-pulse motion-reduce:animate-none' : ''
          }`}
          style={{ color: value === null ? 'var(--color-line)' : TONE[outcome] }}
        >
          {whole}
          <span className="ml-0.5 text-xl text-ink-muted">%</span>
        </p>
      </div>

      <div>
        {/* Escala 0–100 con la marca de la "normal" histórica */}
        <div
          role="img"
          aria-label={
            value === null
              ? `${label}: sin calcular`
              : `${label}: ${pct1(value)}${
                  base !== null ? `, en los partidos de 2021 a 2025 ocurrió el ${pct1(base)} de las veces` : ''
                }`
          }
          className="relative mt-3 h-2.5 rounded-sm bg-raised"
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
              className="absolute -top-1 h-4 w-0.5 rounded-full bg-ink"
              style={{ left: `calc(${base}% - 1px)` }}
            />
          )}
        </div>

        <div className="mt-2 flex flex-wrap items-center justify-between gap-1 text-xs text-ink-muted">
          <span>{base !== null ? `Liga 21–25: ${pct1(base)}` : 'Liga 21–25: …'}</span>
          {vsNormal !== null && (
            <span className="inline-flex items-center gap-0.5 font-bold text-ink">
              {vsNormal >= 0 ? <ArrowUp aria-hidden className="size-3" /> : <ArrowDown aria-hidden className="size-3" />}
              {signed1(vsNormal)} pts
            </span>
          )}
        </div>
        {vsPrev !== null && Math.abs(vsPrev) >= 0.05 && (
          <div className="mt-1">
            <span className="delta-chip inline-flex items-center rounded px-1.5 py-0.5 text-[11px] text-ink">
              {signed1(vsPrev)} pts vs. anterior
            </span>
          </div>
        )}
      </div>
    </li>
  )
}

export default function Forecast({
  result,
  previous,
  busy,
  error,
  baseRates,
  accuracy,
  testMatches,
  actual,
  onOpenModel,
  onRetry,
}: Props) {
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
      className={`rounded-lg border border-line bg-surface p-4 transition-opacity sm:p-5 ${busy ? 'opacity-60' : ''}`}
    >
      {result && !busy && (
        <p role="status" aria-live="polite" className="sr-only">
          {`Pronóstico ${result.home_team} contra ${result.away_team}: victoria de ${result.home_team} ${pct1(
            result.probabilities.home,
          )}, empate ${pct1(result.probabilities.draw)}, victoria de ${result.away_team} ${pct1(
            result.probabilities.away,
          )}.`}
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-accent">Resultado del Partido · 1X2</span>
          <h2 id="forecast-title" className="text-balance font-display text-2xl font-bold leading-tight">
            {result ? `${result.home_team} vs. ${result.away_team}` : 'Pronóstico del partido'}
          </h2>
        </div>
        {result && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-ink-muted">
            {result.mock && (
              <span className="rounded border border-ink-muted px-1.5 py-0.5 font-bold">Datos de ejemplo</span>
            )}
            <span className="rounded bg-raised px-2.5 py-1 font-bold text-ink">
              {result.match_date ? formatDate(result.match_date) : 'Datos más recientes disponibles'}
            </span>
          </div>
        )}
      </div>

      {error ? (
        <div className="mt-4">
          <ErrorNotice title="No se pudo calcular el pronóstico" message={error} onRetry={onRetry}>
            {error.startsWith('Historial insuficiente') &&
              'Prueba con una fecha posterior (los datos empiezan en agosto de 2000) o deja la fecha vacía.'}
          </ErrorNotice>
        </div>
      ) : (
        <>
          <p className="mt-2.5 text-xs text-ink-muted">
            {!result
              ? 'Elige un partido de la lista inferior o configura cualquier cruce a la izquierda. La marca blanca en cada barra es la media histórica (2021–25).'
              : result.odds_used
                ? 'Calculado con las cuotas ingresadas. La marca blanca indica la frecuencia histórica (2021–25).'
                : 'Sin cuotas: el mercado se estimó a partir del Elo. La marca blanca indica la frecuencia histórica (2021–25).'}
          </p>

          {result && actual && (
            <div
              className={`mt-3 flex items-start gap-2.5 rounded-md border px-3 py-2 text-sm ${
                predictedRight(result.predicted, actual)
                  ? 'border-local/50 bg-local/10 text-ink'
                  : 'border-away/50 bg-away/10 text-ink'
              }`}
            >
              {predictedRight(result.predicted, actual) ? (
                <Check aria-hidden className="mt-0.5 size-4 shrink-0 text-local" />
              ) : (
                <X aria-hidden className="mt-0.5 size-4 shrink-0 text-away" />
              )}
              <span>
                <span className="font-bold">
                  Marcador real: {actual.home_team} {score(actual)} {actual.away_team}.
                </span>{' '}
                El modelo daba como más probable «{labels[result.predicted]}» y{' '}
                {predictedRight(result.predicted, actual) ? 'acertó' : 'no coincidió'} (asignó{' '}
                {pct1(result.probabilities[outcomeOf(actual)])} al resultado que ocurrió).
              </span>
            </div>
          )}

          {warnings.length > 0 && (
            <div role="status" className="mt-3 flex gap-2.5 rounded-md border border-draw/50 bg-draw/10 p-2.5 text-xs text-draw">
              <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
              <div>
                {warnings.map((w) => (
                  <p key={w}>{w}</p>
                ))}
                <p className="mt-0.5 text-ink">Tómalo como una estimación con menor respaldo histórico.</p>
              </div>
            </div>
          )}

          {result && (
            <div
              aria-hidden
              key={`stack-${result.home_team}-${result.away_team}-${result.probabilities.home}`}
              className="mt-3.5 flex h-2.5 gap-0.5 overflow-hidden rounded-sm"
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

          {/* Tarjetas 1 · X · 2 en 3 columnas horizontales como cuotas de apuestas */}
          <ul
            key={result ? `${result.home_team}-${result.away_team}-${result.probabilities.home}` : 'empty'}
            className="mt-3.5 grid grid-cols-1 gap-2.5 sm:grid-cols-3"
          >
            {ORDER.map((o, i) => (
              <OutcomeCard
                key={o}
                outcome={o}
                label={labels[o]}
                value={result ? result.probabilities[o] : null}
                base={baseRates ? baseRates[o] : null}
                prev={prev ? prev.probabilities[o] : null}
                index={i}
                winner={result?.predicted === o}
                loading={busy && !result}
              />
            ))}
          </ul>

          {result?.predicted_bayesian && result.predicted_bayesian !== result.predicted && (
            <div className="mt-3.5 flex items-start gap-2 rounded-md border border-draw/40 bg-draw/10 px-3 py-2 text-xs text-ink">
              <Scale aria-hidden className="mt-0.5 size-4 shrink-0 text-draw" />
              <span>
                Con los <strong>umbrales bayesianos</strong> del modelo (ajustados para detectar más empates), el
                pronóstico discreto sería <span className="font-bold text-draw">«{labels[result.predicted_bayesian]}»</span>,
                aunque «{labels[result.predicted]}» tiene la probabilidad bruta más alta.
              </span>
            </div>
          )}

          <div className="mt-3.5 flex items-center gap-2 border-t border-line/70 pt-2.5 text-xs text-ink-muted">
            <Info aria-hidden className="size-3.5 shrink-0" />
            <p>
              Tres probabilidades que suman 100 %.
              {accuracy !== null && (
                <>
                  {' '}
                  Exactitud en {testMatches !== null ? num0(testMatches) : 'los'} partidos de prueba:{' '}
                  <strong className="text-ink">{pct1(accuracy * 100)}</strong>.{' '}
                  <button type="button" onClick={onOpenModel} className="font-bold text-accent underline hover:brightness-125">
                    Ver evaluación del modelo
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

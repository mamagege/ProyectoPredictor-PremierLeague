import { useEffect, useRef, useState } from 'react'
import { Activity, ShieldAlert } from 'lucide-react'
import {
  api,
  ApiRequestError,
  deployedResult,
  testSize,
  type MatchDay,
  type MetricsResponse,
  type PlayedMatch,
  type PredictRequest,
  type PredictResponse,
  type TeamsResponse,
} from '../api'
import ErrorNotice from '../components/ErrorNotice'
import MatchForm, { type MatchFields } from '../components/MatchForm'
import MatchesPanel, { type PickedMatch } from '../components/MatchesPanel'
import Forecast from '../components/Forecast'
import Conditions from '../components/Conditions'
import { baseRatesFrom } from '../lib/rates'

interface Props {
  teams: TeamsResponse | null
  dates: MatchDay[] | null
  teamsError: string | null
  metrics: MetricsResponse | null
  onOpenModel: () => void
  onRetryTeams: () => void
}

export default function PredictorView({ teams, dates, teamsError, metrics, onOpenModel, onRetryTeams }: Props) {
  const [fields, setFields] = useState<MatchFields>({ home: 'Arsenal', away: 'Man City', date: '' })
  const [actual, setActual] = useState<PlayedMatch | null>(null)
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [previous, setPrevious] = useState<PredictResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retriable, setRetriable] = useState(false)
  const lastRequest = useRef<PredictRequest | null>(null)
  const lastPlayed = useRef<PlayedMatch | null>(null)
  const resultRef = useRef<HTMLDivElement>(null)
  const autoLoaded = useRef(false)

  async function submit(req: PredictRequest, played: PlayedMatch | null = null) {
    lastRequest.current = req
    lastPlayed.current = played
    setBusy(true)
    setError(null)
    try {
      const next = await api.predict(req)
      setPrevious(result)
      setResult(next)
      setActual(played)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error inesperado')
      setRetriable(e instanceof ApiRequestError && e.retriable)
    } finally {
      setBusy(false)
    }
  }

  // Calcula un partido inicial al cargar para que las 3 columnas aprovechen todo el espacio desde el inicio.
  useEffect(() => {
    if (teams && !autoLoaded.current) {
      autoLoaded.current = true
      submit({ home_team: fields.home, away_team: fields.away })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teams])

  // Al tocar un partido: se cargan sus datos en el formulario y se calcula de inmediato.
  function pick(m: PickedMatch) {
    setFields({ home: m.home, away: m.away, date: m.date })
    submit({ home_team: m.home, away_team: m.away, match_date: m.date }, m.actual ?? null)
  }

  const baseRates = baseRatesFrom(metrics)
  const accuracy = deployedResult(metrics)?.accuracy ?? null
  const testMatches = metrics ? testSize(metrics) : null

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[310px_minmax(0,1fr)] xl:grid-cols-[320px_minmax(0,1fr)_390px]">
      <h1 tabIndex={-1} className="sr-only focus:outline-none">
        Predictor de partidos
      </h1>

      {/* Columna izquierda: Configuración de partido y accesos rápidos */}
      <div className="grid gap-3">
        <MatchForm
          {...fields}
          dates={dates}
          teams={teams}
          offline={teamsError !== null}
          busy={busy}
          onChange={(patch) => setFields((f) => ({ ...f, ...patch }))}
          onSubmit={(req) => submit(req)}
        />
        {teamsError && (
          <ErrorNotice message={teamsError} onRetry={onRetryTeams}>
            Si la API no está iniciada, arráncala desde la raíz del repositorio con{' '}
            <code className="font-bold">uvicorn api.main:app --port 8000</code>.
          </ErrorNotice>
        )}

        {/* Atajos rápidos de partidos destacados para evaluar con un clic */}
        <section className="rounded-lg border border-line bg-surface p-3.5">
          <h2 className="flex items-center gap-1.5 font-display text-sm font-bold uppercase tracking-wider text-ink-muted">
            <Activity aria-hidden className="size-3.5 text-accent" />
            Cruces rápidos · Demo
          </h2>
          <div className="mt-2.5 grid gap-1.5 text-xs">
            {[
              { home: 'Arsenal', away: 'Man City', date: '', tag: 'Datos actuales · Bayes Empate' },
              { home: 'Crystal Palace', away: 'Man City', date: '2026-08-28', tag: '28 ago 2026 · Real 1–4' },
              { home: 'Liverpool', away: "Nott'm Forest", date: '2026-08-29', tag: '29 ago 2026 · Real 2–2' },
              { home: 'Arsenal', away: 'Chelsea', date: '2024-04-23', tag: '23 abr 2024 · Caso Hito 3' },
              { home: 'Liverpool', away: "Nott'm Forest", date: '2024-09-14', tag: '14 sep 2024 · Caso Hito 3' },
            ].map((c) => (
              <button
                key={`${c.home}-${c.away}-${c.date}`}
                type="button"
                disabled={busy}
                onClick={() => {
                  setFields({ home: c.home, away: c.away, date: c.date })
                  submit({ home_team: c.home, away_team: c.away, match_date: c.date || undefined })
                }}
                className="flex items-center justify-between rounded border border-line bg-raised/60 px-2.5 py-2 text-left hover:border-accent hover:bg-raised disabled:opacity-50"
              >
                <span className="font-bold text-ink">
                  {c.home} vs. {c.away}
                </span>
                <span className="text-[11px] text-ink-muted">{c.tag}</span>
              </button>
            ))}
          </div>
        </section>
      </div>

      {/* Columna central: Pronóstico 1X2 arriba + Tablero de partidos tipo sportsbook abajo */}
      <div ref={resultRef} className="grid min-w-0 gap-4">
        <Forecast
          result={result}
          previous={previous}
          busy={busy}
          error={error}
          baseRates={baseRates}
          accuracy={accuracy}
          testMatches={testMatches}
          actual={actual}
          onOpenModel={onOpenModel}
          onRetry={retriable ? () => lastRequest.current && submit(lastRequest.current, lastPlayed.current) : null}
        />
        <MatchesPanel
          date={fields.date}
          disabled={busy}
          activePair={result ? { home: result.home_team, away: result.away_team, date: result.match_date } : undefined}
          onPick={pick}
        />
      </div>

      {/* Columna derecha (Cupón / Ficha técnica pre-partido e Historial H2H) */}
      <div className="lg:col-span-2 xl:col-span-1">
        {result && !error ? (
          <Conditions result={result} />
        ) : (
          <section className="rounded-lg border border-line bg-surface p-5 text-center text-sm text-ink-muted">
            <ShieldAlert aria-hidden className="mx-auto size-8 text-ink-muted/60" />
            <p className="mt-2 font-bold text-ink">Ficha técnica pre-partido</p>
            <p className="mt-1">
              Selecciona un evento en la tabla central o calcula un pronóstico para ver la comparativa de Elo, forma,
              goles y el historial directo (H2H).
            </p>
          </section>
        )}
      </div>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'
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
  const [fields, setFields] = useState<MatchFields>({ home: 'Arsenal', away: 'Chelsea', date: '' })
  const [actual, setActual] = useState<PlayedMatch | null>(null)
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [previous, setPrevious] = useState<PredictResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retriable, setRetriable] = useState(false)
  const lastRequest = useRef<PredictRequest | null>(null)
  const lastPlayed = useRef<PlayedMatch | null>(null)
  const resultRef = useRef<HTMLDivElement>(null)

  // En pantallas de una columna el resultado queda debajo del formulario: se desplaza hasta él.
  useEffect(() => {
    if (!result) return
    const stacked = window.matchMedia('(max-width: 1023px)').matches
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    // Una columna: el resultado queda bajo el formulario. Dos columnas: solo si quedó fuera de la vista.
    resultRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: stacked ? 'start' : 'nearest' })
  }, [result])

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

  // Al tocar un partido: se cargan sus datos en el formulario y se calcula de inmediato.
  function pick(m: PickedMatch) {
    setFields({ home: m.home, away: m.away, date: m.date })
    submit({ home_team: m.home, away_team: m.away, match_date: m.date }, m.actual ?? null)
  }

  const baseRates = baseRatesFrom(metrics)
  const accuracy = deployedResult(metrics)?.accuracy ?? null
  const testMatches = metrics ? testSize(metrics) : null

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 lg:grid-cols-[380px_minmax(0,1fr)]">
      <h1 tabIndex={-1} className="sr-only focus:outline-none">
        Predictor de partidos
      </h1>
      <div className="lg:sticky lg:top-5">
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
          <div className="mt-4">
            <ErrorNotice message={teamsError} onRetry={onRetryTeams}>
              Si la API no está iniciada, arráncala desde la raíz del repositorio con{' '}
              <code className="font-bold">uvicorn api.main:app --port 8000</code>.
            </ErrorNotice>
          </div>
        )}
      </div>
      <div ref={resultRef} className="grid scroll-mt-4 grid-cols-[minmax(0,1fr)] gap-5">
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
        {result && !error && <Conditions result={result} />}
      </div>
      <div className="lg:col-span-2">
        <MatchesPanel date={fields.date} disabled={busy} onPick={pick} />
      </div>
    </div>
  )
}

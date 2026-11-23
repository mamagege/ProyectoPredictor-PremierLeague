import { useEffect, useRef, useState } from 'react'
import {
  api,
  ApiRequestError,
  type MetricsResponse,
  type PredictRequest,
  type PredictResponse,
  type TeamsResponse,
} from '../api'
import ErrorNotice from '../components/ErrorNotice'
import MatchForm from '../components/MatchForm'
import Forecast from '../components/Forecast'
import Conditions from '../components/Conditions'
import { baseRatesFrom } from '../lib/rates'

interface Props {
  teams: TeamsResponse | null
  teamsError: string | null
  metrics: MetricsResponse | null
  onOpenModel: () => void
  onRetryTeams: () => void
}

export default function PredictorView({ teams, teamsError, metrics, onOpenModel, onRetryTeams }: Props) {
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [previous, setPrevious] = useState<PredictResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retriable, setRetriable] = useState(false)
  const lastRequest = useRef<PredictRequest | null>(null)
  const resultRef = useRef<HTMLDivElement>(null)

  // En pantallas de una columna el resultado queda debajo del formulario: se desplaza hasta él.
  useEffect(() => {
    if (!result) return
    if (!window.matchMedia('(max-width: 1023px)').matches) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    resultRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
  }, [result])

  async function submit(req: PredictRequest) {
    lastRequest.current = req
    setBusy(true)
    setError(null)
    try {
      const next = await api.predict(req)
      setPrevious(result)
      setResult(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error inesperado')
      setRetriable(e instanceof ApiRequestError && e.retriable)
    } finally {
      setBusy(false)
    }
  }

  const baseRates = baseRatesFrom(metrics)
  const accuracy = metrics ? (metrics.test_results.find((r) => r.model.startsWith('Deep MLP'))?.accuracy ?? null) : null

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 lg:grid-cols-[380px_minmax(0,1fr)]">
      <div className="lg:sticky lg:top-5">
        <MatchForm teams={teams} offline={teamsError !== null} busy={busy} onSubmit={submit} />
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
          onOpenModel={onOpenModel}
          onRetry={retriable ? () => lastRequest.current && submit(lastRequest.current) : null}
        />
        {result && !error && <Conditions result={result} />}
      </div>
    </div>
  )
}

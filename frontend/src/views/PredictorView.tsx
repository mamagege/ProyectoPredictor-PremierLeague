import { useEffect, useRef, useState } from 'react'
import {
  api,
  deployedResult,
  testSize,
  type MetricsResponse,
  type PredictRequest,
  type PredictResponse,
  type TeamsResponse,
} from '../api'
import MatchForm from '../components/MatchForm'
import Forecast, { type BaseRates } from '../components/Forecast'
import Conditions from '../components/Conditions'

interface Props {
  teams: TeamsResponse | null
  teamsError: string | null
  metrics: MetricsResponse | null
  onOpenModel: () => void
}

/** Frecuencia real de cada desenlace en el conjunto de prueba (la "normal"). */
function baseRatesFrom(m: MetricsResponse | null): BaseRates | null {
  if (!m) return null
  const rows = m.confusion_matrix.map((r) => r.reduce((a, b) => a + b, 0))
  const total = rows.reduce((a, b) => a + b, 0)
  if (!total) return null
  return { home: (rows[0] / total) * 100, draw: (rows[1] / total) * 100, away: (rows[2] / total) * 100 }
}

export default function PredictorView({ teams, teamsError, metrics, onOpenModel }: Props) {
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [previous, setPrevious] = useState<PredictResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const resultRef = useRef<HTMLDivElement>(null)

  // En pantallas de una columna el resultado queda debajo del formulario: se desplaza hasta él.
  useEffect(() => {
    if (!result) return
    if (!window.matchMedia('(max-width: 1023px)').matches) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    resultRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
  }, [result])

  async function submit(req: PredictRequest) {
    setBusy(true)
    setError(null)
    try {
      const next = await api.predict(req)
      setPrevious(result)
      setResult(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error inesperado')
    } finally {
      setBusy(false)
    }
  }

  const baseRates = baseRatesFrom(metrics)
  const accuracy = deployedResult(metrics)?.accuracy ?? null
  const testMatches = metrics ? testSize(metrics) : null

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 lg:grid-cols-[380px_minmax(0,1fr)]">
      <div className="lg:sticky lg:top-5">
        <MatchForm teams={teams} offline={teamsError !== null} busy={busy} onSubmit={submit} />
        {teamsError && (
          <p role="alert" className="mt-4 rounded-md border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-danger">
            {teamsError} Inicia la API desde la raíz del repositorio con{' '}
            <code className="font-bold">uvicorn api.main:app --port 8000</code> y recarga la página.
          </p>
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
          onOpenModel={onOpenModel}
        />
        {result && !error && <Conditions result={result} />}
      </div>
    </div>
  )
}

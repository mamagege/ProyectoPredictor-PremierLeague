import { useState } from 'react'
import { api, type MetricsResponse, type PredictRequest, type PredictResponse, type TeamsResponse } from '../api'
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
  const accuracy = metrics ? (metrics.test_results.find((r) => r.model.startsWith('Deep MLP'))?.accuracy ?? null) : null

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 lg:grid-cols-[380px_minmax(0,1fr)]">
      <div className="lg:sticky lg:top-5">
        <MatchForm teams={teams} busy={busy} onSubmit={submit} />
        {teamsError && (
          <p role="alert" className="mt-4 rounded-md border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-danger">
            No se pudo conectar con el servicio de predicción ({teamsError}). Inicia la API con{' '}
            <code className="font-bold">uvicorn api.main:app --port 8000</code>.
          </p>
        )}
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-5">
        <Forecast
          result={result}
          previous={previous}
          busy={busy}
          error={error}
          baseRates={baseRates}
          accuracy={accuracy}
          onOpenModel={onOpenModel}
        />
        {result && !error && <Conditions result={result} />}
      </div>
    </div>
  )
}

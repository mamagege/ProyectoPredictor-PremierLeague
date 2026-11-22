import { useEffect, useState } from 'react'
import { api, type PredictResponse } from './api'

// Placeholder de verificación del pipeline front -> proxy -> API -> modelo.
// La interfaz real se diseña en la siguiente fase.
export default function App() {
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .predict({ home_team: 'Arsenal', away_team: 'Chelsea', match_date: '2024-04-23' })
      .then(setResult)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <main className="p-8 font-sans">
      <h1 className="text-2xl font-semibold">Predictor EPL</h1>
      {error && <p className="text-red-600">{error}</p>}
      {result && (
        <p>
          {result.home_team} {result.probabilities.home}% · Empate {result.probabilities.draw}% ·{' '}
          {result.away_team} {result.probabilities.away}%
        </p>
      )}
    </main>
  )
}

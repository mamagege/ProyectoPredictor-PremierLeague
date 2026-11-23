import type { MetricsResponse, Outcome } from '../api'

export type BaseRates = Record<Outcome, number>

/** Frecuencia real de cada desenlace (%) en el conjunto de prueba, a partir de la matriz de confusión. */
export function baseRatesFrom(m: Pick<MetricsResponse, 'confusion_matrix'> | null): BaseRates | null {
  if (!m) return null
  const rows = m.confusion_matrix.map((r) => r.reduce((a, b) => a + b, 0))
  const total = rows.reduce((a, b) => a + b, 0)
  if (!total) return null
  return { home: (rows[0] / total) * 100, draw: (rows[1] / total) * 100, away: (rows[2] / total) * 100 }
}

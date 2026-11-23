import type { CalibrationBin } from '../api'

export interface ReliabilityPoint {
  /** Probabilidad media que dio el modelo en el tramo (0–1). */
  x: number
  /** Frecuencia con la que el resultado ocurrió de verdad (0–1). */
  y: number
  count: number
}

/** Puntos de una curva de confiabilidad: solo tramos con partidos, ordenados por probabilidad. */
export function reliabilityPoints(bins: CalibrationBin[] | undefined | null): ReliabilityPoint[] {
  return (bins ?? [])
    .filter((b) => b.count > 0)
    .map((b) => ({ x: b.mean_predicted_prob, y: b.empirical_frequency, count: b.count }))
    .sort((a, b) => a.x - b.x)
}

/** Radio del punto: crece con la raíz de los partidos del tramo, entre `min` y `max`. */
export function pointRadius(count: number, maxCount: number, min = 3, max = 8): number {
  if (maxCount <= 0) return min
  return min + (max - min) * Math.sqrt(Math.min(count, maxCount) / maxCount)
}

import type { PredictResponse } from '../api'
import { formatDate } from './format'

export const STALE_DAYS = 400

type Dated = Pick<
  PredictResponse,
  'match_date' | 'data_end' | 'home_team' | 'away_team' | 'home_last_match' | 'away_last_match'
>

/** Avisos cuando el estado de un equipo viene de datos muy viejos respecto a la fecha del pronóstico. */
export function staleWarnings(r: Dated): string[] {
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

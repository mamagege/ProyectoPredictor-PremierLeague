import type { Outcome, PlayedMatch } from '../api'

const BY_LETTER: Record<PlayedMatch['result'], Outcome> = { H: 'home', D: 'draw', A: 'away' }

/** Resultado real del partido como desenlace (local, empate o visitante). */
export const outcomeOf = (m: Pick<PlayedMatch, 'result'>): Outcome => BY_LETTER[m.result]

/** ¿Coincide el desenlace más probable del modelo con lo que pasó? */
export const predictedRight = (predicted: Outcome, m: Pick<PlayedMatch, 'result'>): boolean =>
  predicted === outcomeOf(m)

/** Marcador en el formato «2–1». */
export const score = (m: Pick<PlayedMatch, 'home_goals' | 'away_goals'>): string =>
  `${m.home_goals}–${m.away_goals}`

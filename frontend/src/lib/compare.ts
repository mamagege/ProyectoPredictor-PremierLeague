/** Quién va mejor en un indicador: depende de si más alto o más bajo es mejor. */
export function leader(better: 'high' | 'low' | null, home: number, away: number): 'home' | 'away' | null {
  if (!better || home === away) return null
  const homeWins = better === 'high' ? home > away : home < away
  return homeWins ? 'home' : 'away'
}

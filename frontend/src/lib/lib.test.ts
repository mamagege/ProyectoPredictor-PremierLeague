import { describe, expect, it } from 'vitest'
import { bezier } from './bezier'
import { leader } from './compare'
import { formatDate, num1, pct1, signed1 } from './format'
import { baseRatesFrom } from './rates'
import { staleWarnings } from './stale'

describe('formato es-CO', () => {
  it('usa coma decimal y un decimal fijo', () => {
    expect(num1(58.6)).toBe('58,6')
    expect(num1(25)).toBe('25,0')
    expect(pct1(44.74)).toBe('44,7 %')
  })
  it('marca el signo con el menos tipográfico', () => {
    expect(signed1(13.9)).toBe('+13,9')
    expect(signed1(-16)).toBe('−16,0')
    expect(signed1(0)).toBe('0,0')
  })
  it('escribe la fecha completa en español', () => {
    expect(formatDate('2007-05-13')).toMatch(/13 de mayo de 2007/)
    expect(formatDate(null)).toBe('')
  })
})

describe('frecuencia de cada resultado (matriz de confusión)', () => {
  const m = { confusion_matrix: [[504, 0, 162], [187, 0, 158], [157, 0, 322]] }
  it('suma las filas reales sobre el total de partidos', () => {
    const r = baseRatesFrom(m)!
    expect(r.home).toBeCloseTo(44.7, 1)
    expect(r.draw).toBeCloseTo(23.2, 1)
    expect(r.away).toBeCloseTo(32.1, 1)
    expect(r.home + r.draw + r.away).toBeCloseTo(100, 5)
  })
  it('no inventa datos si faltan o están vacíos', () => {
    expect(baseRatesFrom(null)).toBeNull()
    expect(baseRatesFrom({ confusion_matrix: [[0, 0, 0], [0, 0, 0], [0, 0, 0]] })).toBeNull()
  })
})

describe('aviso de datos antiguos', () => {
  const base = { match_date: null, data_end: '2025-05-05', home_team: 'Charlton', away_team: 'Arsenal' }
  it('avisa de un equipo sin partidos desde hace años', () => {
    const w = staleWarnings({ ...base, home_last_match: '2007-05-13', away_last_match: '2025-05-03' })
    expect(w).toHaveLength(1)
    expect(w[0]).toContain('Charlton')
    expect(w[0]).toContain('13 de mayo de 2007')
  })
  it('no avisa cuando ambos equipos jugaron hace poco', () => {
    expect(staleWarnings({ ...base, home_last_match: '2025-05-01', away_last_match: '2025-05-03' })).toEqual([])
  })
  it('mide contra la fecha pedida, no contra hoy', () => {
    const w = staleWarnings({ ...base, match_date: '2030-01-01', home_last_match: '2025-05-01', away_last_match: '2025-05-03' })
    expect(w).toHaveLength(2)
  })
  it('ignora equipos sin último partido registrado', () => {
    expect(staleWarnings({ ...base, home_last_match: null, away_last_match: null })).toEqual([])
  })
})

describe('quién va mejor', () => {
  it('respeta si más alto o más bajo es mejor', () => {
    expect(leader('high', 3, 1)).toBe('home')
    expect(leader('low', 3, 1)).toBe('away')
  })
  it('no marca ganador en empate ni en indicadores neutros', () => {
    expect(leader('high', 2, 2)).toBeNull()
    expect(leader(null, 9, 1)).toBeNull()
  })
})

describe('curvas cubic-bezier de la intro', () => {
  const easeDash = bezier(0.645, 0.045, 0.355, 1)
  const easeWidth = bezier(0.75, 0.15, 0.15, 1)
  it('parten en 0 y terminan en 1', () => {
    for (const f of [easeDash, easeWidth]) {
      expect(f(0)).toBe(0)
      expect(f(1)).toBe(1)
      expect(f(-0.2)).toBe(0)
      expect(f(1.4)).toBe(1)
    }
  })
  it('son monótonas crecientes', () => {
    for (const f of [easeDash, easeWidth]) {
      let prev = 0
      for (let i = 1; i <= 100; i++) {
        const v = f(i / 100)
        expect(v).toBeGreaterThanOrEqual(prev - 1e-9)
        prev = v
      }
    }
  })
  it('coinciden con los puntos de la curva paramétrica de CSS', () => {
    const point = (t: number, p1: number, p2: number) =>
      3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3
    for (const [f, a, b, c, d] of [
      [easeDash, 0.645, 0.045, 0.355, 1],
      [easeWidth, 0.75, 0.15, 0.15, 1],
    ] as const) {
      for (let t = 0.05; t < 1; t += 0.05) {
        expect(f(point(t, a, c))).toBeCloseTo(point(t, b, d), 3)
      }
    }
  })
  it('la curva lineal es la identidad', () => {
    expect(bezier(0, 0, 1, 1)(0.3)).toBeCloseTo(0.3, 3)
  })
})

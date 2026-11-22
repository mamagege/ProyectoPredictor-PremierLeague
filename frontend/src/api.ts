// Contrato con la API FastAPI (api/main.py)
export type Outcome = 'home' | 'draw' | 'away'

export interface Probabilities {
  home: number
  draw: number
  away: number
}

export interface TeamState {
  elo: number
  form5: number
  rolling_pts5: number
  rolling_gf5: number
  rolling_ga5: number
  rest_days: number
  season_pts: number
  season_gd: number
}

export interface PredictRequest {
  home_team: string
  away_team: string
  match_date?: string
  odds?: [number, number, number]
}

export interface PredictResponse {
  home_team: string
  away_team: string
  match_date: string | null
  probabilities: Probabilities // porcentajes, suman 100
  predicted: Outcome
  odds_used: boolean
  home_state: TeamState
  away_state: TeamState
  h2h: Probabilities
  mock: boolean
}

export interface TeamsResponse {
  season: string
  current: string[]
  all: string[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : 'Error inesperado del servidor'
    throw new Error(detail)
  }
  return body as T
}

export const api = {
  teams: () => request<TeamsResponse>('/api/teams'),
  predict: (body: PredictRequest) =>
    request<PredictResponse>('/api/predict', { method: 'POST', body: JSON.stringify(body) }),
  metrics: () => request<Record<string, unknown>>('/api/metrics'),
}

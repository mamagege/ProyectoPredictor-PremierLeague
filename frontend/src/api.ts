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
  home_last_match: string | null
  away_last_match: string | null
  data_end: string | null
  mock: boolean
}

export interface TeamsResponse {
  season: string
  current: string[]
  all: string[]
}

export interface ModelResult {
  model: string
  accuracy: number
  log_loss: number
  brier_score: number
  f1_D: number
}

export interface MetricsResponse {
  selected_architecture: string
  epochs_trained: number
  test_results: ModelResult[]
  confusion_matrix: number[][]
  confusion_matrix_norm: number[][]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  } catch {
    throw new Error('No hay conexión con el servicio de predicción.')
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    if (typeof body?.detail === 'string') throw new Error(body.detail)
    throw new Error(
      res.status >= 500 ? 'El servicio de predicción no responde.' : 'No se pudo procesar la solicitud. Inténtalo de nuevo.',
    )
  }
  return body as T
}

export const api = {
  teams: () => request<TeamsResponse>('/api/teams'),
  predict: (body: PredictRequest) =>
    request<PredictResponse>('/api/predict', { method: 'POST', body: JSON.stringify(body) }),
  metrics: () => request<MetricsResponse>('/api/metrics'),
}

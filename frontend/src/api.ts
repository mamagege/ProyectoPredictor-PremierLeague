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
  warnings: string[] // avisos del servicio (equipo debutante, fecha posterior a los datos…)
  model_version: string | null
  mock: boolean
}

export interface TeamsResponse {
  season: string
  current: string[]
  all: string[]
  data_end?: string | null // fecha del último partido del historial
}

export interface ModelResult {
  model: string
  n_samples?: number
  accuracy: number
  log_loss: number
  brier_score: number
  f1_D: number
  draws_predicted?: number
}

export interface MetricsResponse {
  model_version: string | null
  selected_architecture: string
  deployed_model: string | null // fila de test_results que corresponde al modelo que sirve la API
  epochs_trained: number
  total_params: number | null
  n_features: number | null
  train_seasons: string[] | null
  val_seasons: string[] | null
  test_seasons: string[] | null
  temperature: number | null
  test_results: ModelResult[]
  prospective_results: ModelResult[]
  confusion_matrix: number[][]
  confusion_matrix_norm: number[][]
}

export interface MatchDay {
  date: string
  matches: number
}

/** Partido ya jugado del historial, con su resultado real. */
export interface PlayedMatch {
  date: string
  home_team: string
  away_team: string
  home_goals: number
  away_goals: number
  result: 'H' | 'D' | 'A'
  season: string | null
}

/** Partido futuro del calendario opcional (no tiene resultado). */
export interface Fixture {
  date: string
  home_team: string
  away_team: string
  round: string | null
  known: boolean
}

export interface FixturesResponse {
  available: boolean
  fixtures: Fixture[]
  skipped: number
  data_end: string
}

/** Error de la API con el estado HTTP (0 = sin conexión). Los 0 y 5xx se pueden reintentar. */
export class ApiRequestError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
  }
  get retriable() {
    return this.status === 0 || this.status >= 500
  }
}

/** Fila del benchmark del modelo en uso (con respaldo para resúmenes antiguos). */
export function deployedResult(m: MetricsResponse | null): ModelResult | null {
  if (!m) return null
  return (
    m.test_results.find((r) => r.model === m.deployed_model) ??
    m.test_results.find((r) => r.model.startsWith('Deep MLP')) ??
    null
  )
}

/** Partidos del conjunto de prueba: n_samples si viene, si no la suma de la matriz de confusión. */
export function testSize(m: MetricsResponse): number {
  return deployedResult(m)?.n_samples ?? m.confusion_matrix.flat().reduce((a, b) => a + b, 0)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  } catch {
    throw new ApiRequestError('No hay conexión con el servicio de predicción.', 0)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    if (typeof body?.detail === 'string') throw new ApiRequestError(body.detail, res.status)
    throw new ApiRequestError(
      res.status >= 500 ? 'El servicio de predicción no responde.' : 'No se pudo procesar la solicitud. Inténtalo de nuevo.',
      res.status,
    )
  }
  return body as T
}

export const api = {
  teams: () => request<TeamsResponse>('/api/teams'),
  predict: (body: PredictRequest) =>
    request<PredictResponse>('/api/predict', { method: 'POST', body: JSON.stringify(body) }),
  metrics: () => request<MetricsResponse>('/api/metrics'),
  dates: () => request<{ dates: MatchDay[] }>('/api/dates').then((r) => r.dates),
  matches: (date?: string) =>
    request<{ date: string | null; matches: PlayedMatch[] }>(date ? `/api/matches?date=${date}` : '/api/matches').then(
      (r) => r.matches,
    ),
  fixtures: () => request<FixturesResponse>('/api/fixtures'),
}

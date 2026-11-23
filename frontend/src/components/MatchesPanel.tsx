import { useCallback, useState } from 'react'
import { Calendar, Flame, Search, Star, Trophy } from 'lucide-react'
import { api, type Fixture, type PlayedMatch } from '../api'
import { formatDate } from '../lib/format'
import { score } from '../lib/matches'
import { useFetch } from '../lib/useFetch'
import ErrorNotice from './ErrorNotice'

export interface PickedMatch {
  home: string
  away: string
  date: string
  /** Resultado real, solo en partidos ya jugados. */
  actual?: PlayedMatch
}

interface Props {
  /** Fecha elegida en el formulario; vacía = los últimos partidos jugados. */
  date: string
  disabled: boolean
  activePair?: { home: string; away: string; date: string | null }
  onPick: (m: PickedMatch) => void
}

function Skeleton() {
  return (
    <ul aria-busy="true" aria-label="Cargando partidos" className="grid gap-1.5 p-3">
      {[0, 1, 2, 3].map((i) => (
        <li key={i} className="h-14 animate-pulse rounded bg-raised motion-reduce:animate-none" />
      ))}
    </ul>
  )
}

export default function MatchesPanel({ date, disabled, activePair, onPick }: Props) {
  const [filter, setFilter] = useState('')
  const [view, setView] = useState<'played' | 'fixtures'>('played')
  const fixtures = useFetch(api.fixtures)
  const loadPlayed = useCallback(() => api.matches(date || undefined), [date])
  const played = useFetch(loadPlayed)

  const q = filter.trim().toLowerCase()
  const playedList = (played.data ?? []).filter(
    (m) => !q || m.home_team.toLowerCase().includes(q) || m.away_team.toLowerCase().includes(q) || m.date.includes(q),
  )
  const fixtureList = (fixtures.data?.fixtures ?? []).filter(
    (f) => !q || f.home_team.toLowerCase().includes(q) || f.away_team.toLowerCase().includes(q) || f.date.includes(q),
  )

  return (
    <section className="overflow-hidden rounded-lg border border-line bg-surface">
      {/* Barra superior estilo Sportsbook / Liga */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-raised/70 px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <Star aria-hidden className="size-4 text-draw" />
          <span className="font-display text-sm font-bold uppercase tracking-wider text-ink">
            Inglaterra · Premier League
          </span>
          <span className="rounded bg-canvas/70 px-2 py-0.5 text-xs font-bold text-ink-muted">
            {date ? formatDate(date) : 'Últimas jornadas'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search aria-hidden className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-muted" />
            <input
              type="search"
              placeholder="Buscar club…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-36 rounded border border-line bg-canvas/80 py-1 pl-7 pr-2 text-xs text-ink placeholder:text-ink-muted focus:w-44 focus:outline-none sm:w-44"
            />
          </div>
          <div className="inline-flex rounded border border-line bg-canvas/70 p-0.5 text-xs font-bold">
            <button
              type="button"
              onClick={() => setView('played')}
              className={`rounded px-2.5 py-1 ${view === 'played' ? 'bg-accent text-canvas' : 'text-ink-muted hover:text-ink'}`}
            >
              Jugados ({played.data?.length ?? 0})
            </button>
            <button
              type="button"
              onClick={() => setView('fixtures')}
              className={`rounded px-2.5 py-1 ${view === 'fixtures' ? 'bg-accent text-canvas' : 'text-ink-muted hover:text-ink'}`}
            >
              Próximos
            </button>
          </div>
        </div>
      </div>

      {/* Cabecera de columnas 1 · X · 2 estilo casa deportiva */}
      <div className="grid grid-cols-[minmax(0,1fr)_186px] items-center border-b border-line bg-canvas/40 px-3.5 py-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-muted sm:grid-cols-[minmax(0,1fr)_225px]">
        <span>Encuentro · Toca para evaluar en el modelo</span>
        <div className="grid grid-cols-3 text-center">
          <span>1</span>
          <span>X</span>
          <span>2</span>
        </div>
      </div>

      {view === 'played' ? (
        <>
          {played.loading && <Skeleton />}
          {played.error && (
            <div className="p-4">
              <ErrorNotice message={played.error} onRetry={played.retry} />
            </div>
          )}
          {played.data && playedList.length === 0 && (
            <p className="p-4 text-sm text-ink-muted">
              No hay partidos registrados para ese filtro o fecha ({date || 'recientes'}). Puedes igual presionar{' '}
              <strong className="text-ink">Calcular pronóstico</strong> en el panel izquierdo para cualquier cruce en esa fecha.
            </p>
          )}
          {playedList.length > 0 && (
            <ul className="divide-y divide-line">
              {playedList.map((m) => {
                const isSelected =
                  activePair?.home === m.home_team && activePair?.away === m.away_team && activePair?.date === m.date
                const res = m.result // 'H' | 'D' | 'A'
                return (
                  <li key={`${m.date}-${m.home_team}-${m.away_team}`}>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => onPick({ home: m.home_team, away: m.away_team, date: m.date, actual: m })}
                      aria-label={`Ver el pronóstico de ${m.home_team} contra ${m.away_team}, ${formatDate(m.date)}. Resultado real ${score(m)}`}
                      className={`grid w-full grid-cols-[minmax(0,1fr)_186px] items-center gap-2 px-3.5 py-2.5 text-left transition-colors hover:bg-raised/70 disabled:opacity-50 sm:grid-cols-[minmax(0,1fr)_225px] ${
                        isSelected ? 'bg-raised/90 ring-1 ring-inset ring-accent' : ''
                      }`}
                    >
                      <div className="min-w-0 pr-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className={`truncate text-sm font-bold ${res === 'H' ? 'text-ink' : 'text-ink-muted'}`}>
                            {m.home_team}
                          </span>
                          <span className="font-display text-sm font-bold text-ink">{m.home_goals}</span>
                        </div>
                        <div className="mt-0.5 flex items-center justify-between gap-2">
                          <span className={`truncate text-sm font-bold ${res === 'A' ? 'text-ink' : 'text-ink-muted'}`}>
                            {m.away_team}
                          </span>
                          <span className="font-display text-sm font-bold text-ink">{m.away_goals}</span>
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-[11px] text-ink-muted">
                          <Calendar aria-hidden className="size-3 text-accent" />
                          <span>{formatDate(m.date)}</span>
                          {m.season && <span>· Temp. {m.season}</span>}
                          <Flame aria-hidden className="size-3 text-draw" />
                        </div>
                      </div>

                      {/* Cajas 1 X 2 estilo Stake */}
                      <div className="grid grid-cols-3 gap-1.5">
                        <div
                          className={`flex flex-col items-center justify-center rounded border py-2 ${
                            res === 'H'
                              ? 'border-local/70 bg-local/15 text-local'
                              : 'border-line bg-canvas/80 text-ink-muted'
                          }`}
                        >
                          <span className="text-[10px] font-bold uppercase">1</span>
                          <span className="font-display text-xs font-bold">{res === 'H' ? 'GANÓ' : 'LOCAL'}</span>
                        </div>
                        <div
                          className={`flex flex-col items-center justify-center rounded border py-2 ${
                            res === 'D'
                              ? 'border-draw/70 bg-draw/15 text-draw'
                              : 'border-line bg-canvas/80 text-ink-muted'
                          }`}
                        >
                          <span className="text-[10px] font-bold uppercase">X</span>
                          <span className="font-display text-xs font-bold">{res === 'D' ? 'EMPATE' : 'EMP'}</span>
                        </div>
                        <div
                          className={`flex flex-col items-center justify-center rounded border py-2 ${
                            res === 'A'
                              ? 'border-away/70 bg-away/15 text-away'
                              : 'border-line bg-canvas/80 text-ink-muted'
                          }`}
                        >
                          <span className="text-[10px] font-bold uppercase">2</span>
                          <span className="font-display text-xs font-bold">{res === 'A' ? 'GANÓ' : 'VIS'}</span>
                        </div>
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </>
      ) : (
        <>
          {fixtures.loading && <Skeleton />}
          {fixtures.error && (
            <div className="p-4">
              <ErrorNotice message={fixtures.error} onRetry={fixtures.retry} />
            </div>
          )}
          {fixtures.data && !fixtures.data.available && (
            <div className="p-4 text-sm text-ink-muted">
              <p className="flex items-center gap-2 font-bold text-ink">
                <Trophy aria-hidden className="size-4 text-accent" />
                Sin calendario futuro en <code className="font-bold">datasets/fixtures.csv</code>
              </p>
              <p className="mt-1">
                Los datos históricos llegan hasta el {formatDate(fixtures.data.data_end)}. Puedes simular cualquier
                partido futuro o histórico eligiendo los dos clubes y la fecha en el panel izquierdo.
              </p>
            </div>
          )}
          {fixtures.data?.available && fixtureList.length === 0 && (
            <p className="p-4 text-sm text-ink-muted">
              El calendario cargado no tiene partidos posteriores al {formatDate(fixtures.data.data_end)}.
            </p>
          )}
          {fixtures.data?.available && fixtureList.length > 0 && (
            <ul className="divide-y divide-line">
              {fixtureList.map((f: Fixture) => (
                <li key={`${f.date}-${f.home_team}-${f.away_team}`}>
                  <button
                    type="button"
                    disabled={disabled || !f.known}
                    onClick={() => onPick({ home: f.home_team, away: f.away_team, date: f.date })}
                    className="grid w-full grid-cols-[minmax(0,1fr)_186px] items-center gap-2 px-3.5 py-2.5 text-left hover:bg-raised/70 disabled:opacity-50 sm:grid-cols-[minmax(0,1fr)_225px]"
                  >
                    <div className="min-w-0 pr-2">
                      <span className="block truncate text-sm font-bold text-ink">{f.home_team}</span>
                      <span className="block truncate text-sm font-bold text-ink">{f.away_team}</span>
                      <span className="mt-1 block text-[11px] text-ink-muted">
                        {formatDate(f.date)}
                        {f.round ? ` · Jornada ${f.round}` : ''}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-1.5">
                      {(['1', 'X', '2'] as const).map((k) => (
                        <div
                          key={k}
                          className="flex flex-col items-center justify-center rounded border border-line bg-canvas/80 py-2 text-accent"
                        >
                          <span className="text-[10px] font-bold">{k}</span>
                          <span className="font-display text-xs font-bold">CALC</span>
                        </div>
                      ))}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}

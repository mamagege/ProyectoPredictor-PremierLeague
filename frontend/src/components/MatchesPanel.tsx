import { useCallback, type ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'
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
  onPick: (m: PickedMatch) => void
}

function Skeleton() {
  return (
    <ul aria-busy="true" aria-label="Cargando partidos" className="mt-4 grid gap-1">
      {[0, 1, 2].map((i) => (
        <li key={i} className="h-14 animate-pulse rounded-md bg-raised motion-reduce:animate-none" />
      ))}
    </ul>
  )
}

function Row({
  title,
  sub,
  right,
  label,
  disabled,
  onClick,
}: {
  title: string
  sub: string
  right: ReactNode
  label: string
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <li className="border-b border-line last:border-0">
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
        className="flex min-h-14 w-full items-center justify-between gap-3 rounded-md px-2 py-2 text-left hover:bg-raised disabled:opacity-50"
      >
        <span className="min-w-0">
          <span className="block break-words font-bold">{title}</span>
          <span className="block text-sm text-ink-muted">{sub}</span>
        </span>
        <span className="shrink-0 text-ink-muted">{right}</span>
      </button>
    </li>
  )
}

function Panel({ title, intro, children }: { title: string; intro: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 className="text-balance font-display text-2xl font-bold leading-tight">{title}</h2>
      <p className="mt-1 text-base text-ink-muted">{intro}</p>
      {children}
    </section>
  )
}

export default function MatchesPanel({ date, disabled, onPick }: Props) {
  const fixtures = useFetch(api.fixtures)
  const loadPlayed = useCallback(() => api.matches(date || undefined), [date])
  const played = useFetch(loadPlayed)

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-5 xl:grid-cols-2">
      <Panel title="Próximos partidos" intro="Toca un partido para calcular su pronóstico.">
        {fixtures.loading && <Skeleton />}
        {fixtures.error && (
          <div className="mt-4">
            <ErrorNotice message={fixtures.error} onRetry={fixtures.retry} />
          </div>
        )}
        {fixtures.data && !fixtures.data.available && (
          <p className="mt-4 text-base text-ink-muted">
            Aún no hay un calendario de partidos futuros cargado: los datos llegan hasta el{' '}
            {formatDate(fixtures.data.data_end)} y todos esos partidos ya se jugaron. Para ver los próximos, el equipo
            puede cargar un calendario en <code className="font-bold">datasets/fixtures.csv</code> (hay una plantilla
            con las columnas).
          </p>
        )}
        {fixtures.data?.available && fixtures.data.fixtures.length === 0 && (
          <p className="mt-4 text-base text-ink-muted">
            El calendario cargado no tiene partidos posteriores al {formatDate(fixtures.data.data_end)}.
          </p>
        )}
        {fixtures.data?.available && fixtures.data.fixtures.length > 0 && (
          <ul className="mt-4">
            {fixtures.data.fixtures.map((f: Fixture) => (
              <Row
                key={`${f.date}-${f.home_team}-${f.away_team}`}
                title={`${f.home_team} – ${f.away_team}`}
                sub={`${formatDate(f.date)}${f.round ? ` · Jornada ${f.round}` : ''}${f.known ? '' : ' · equipo sin historial'}`}
                right={<ChevronRight aria-hidden className="size-5" />}
                label={`Calcular el pronóstico de ${f.home_team} contra ${f.away_team}, ${formatDate(f.date)}`}
                disabled={disabled || !f.known}
                onClick={() => onPick({ home: f.home_team, away: f.away_team, date: f.date })}
              />
            ))}
          </ul>
        )}
      </Panel>

      <Panel
        title={date ? `Partidos del ${formatDate(date)}` : 'Últimos partidos jugados'}
        intro="Toca un partido para ver el pronóstico y compararlo con lo que pasó."
      >
        {played.loading && <Skeleton />}
        {played.error && (
          <div className="mt-4">
            <ErrorNotice message={played.error} onRetry={played.retry} />
          </div>
        )}
        {played.data && played.data.length === 0 && (
          <p className="mt-4 text-base text-ink-muted">
            No hay partidos jugados registrados ese día. Elige otra fecha en el formulario.
          </p>
        )}
        {played.data && played.data.length > 0 && (
          <ul className="mt-4">
            {played.data.map((m) => (
              <Row
                key={`${m.date}-${m.home_team}-${m.away_team}`}
                title={`${m.home_team} – ${m.away_team}`}
                sub={formatDate(m.date)}
                right={<span className="font-display text-2xl font-bold text-ink">{score(m)}</span>}
                label={`Ver el pronóstico de ${m.home_team} contra ${m.away_team}, ${formatDate(m.date)}. Resultado real ${score(m)}`}
                disabled={disabled}
                onClick={() => onPick({ home: m.home_team, away: m.away_team, date: m.date, actual: m })}
              />
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}

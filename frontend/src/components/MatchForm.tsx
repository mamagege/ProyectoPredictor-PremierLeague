import { useState } from 'react'
import { ArrowLeftRight, Calendar, ChevronDown, Loader2, RotateCcw } from 'lucide-react'
import type { MatchDay, PredictRequest, TeamsResponse } from '../api'
import { formatDate } from '../lib/format'

export interface MatchFields {
  home: string
  away: string
  /** Fecha AAAA-MM-DD; vacía = datos más recientes. */
  date: string
}

interface Props extends MatchFields {
  teams: TeamsResponse | null
  /** Fechas con partidos en el historial; null mientras cargan o si la API no responde. */
  dates: MatchDay[] | null
  offline: boolean
  busy: boolean
  onChange: (patch: Partial<MatchFields>) => void
  onSubmit: (req: PredictRequest) => void
}

const inputBase =
  'w-full rounded-md border border-line bg-raised px-3 py-2 text-sm text-ink ' +
  'hover:border-ink-muted disabled:opacity-50'

function TeamSelect({
  id,
  label,
  value,
  onChange,
  teams,
  offline,
  tone,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  teams: TeamsResponse | null
  offline: boolean
  tone: string
}) {
  const others = teams ? teams.all.filter((t) => !teams.current.includes(t)) : []
  return (
    <div>
      <label htmlFor={id} className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-ink-muted">
        <span aria-hidden className="size-2 rounded-full" style={{ background: tone }} />
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={!teams}
          className={`${inputBase} appearance-none pr-8 font-bold`}
        >
          {!teams && <option>{offline ? 'Equipos no disponibles' : 'Cargando equipos…'}</option>}
          {teams && (
            <>
              <optgroup label={`Temporada ${teams.season}`}>
                {teams.current.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </optgroup>
              <optgroup label="Otros equipos históricos">
                {others.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </optgroup>
            </>
          )}
        </select>
        <ChevronDown
          aria-hidden
          className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-ink-muted"
        />
      </div>
    </div>
  )
}

const toNumber = (s: string) => Number(s.trim().replace(',', '.'))

export default function MatchForm({ home, away, date, dates, teams, offline, busy, onChange, onSubmit }: Props) {
  const [odds, setOdds] = useState(['', '', ''])
  const [error, setError] = useState<string | null>(null)

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (home === away) {
      setError('Elige dos equipos distintos: un equipo no puede jugar contra sí mismo.')
      return
    }
    const filled = odds.filter((o) => o.trim() !== '')
    let parsed: [number, number, number] | undefined
    if (filled.length > 0) {
      const nums = odds.map(toNumber)
      if (filled.length < 3 || nums.some((n) => !Number.isFinite(n) || n <= 1)) {
        setError('Las cuotas necesitan los tres valores (1, X, 2), cada uno mayor a 1,00.')
        return
      }
      parsed = nums as [number, number, number]
    }
    setError(null)
    onSubmit({ home_team: home, away_team: away, match_date: date || undefined, odds: parsed })
  }

  const swap = () => {
    onChange({ home: away, away: home })
    setError(null)
  }

  const oddsLabels = ['1 · Local', 'X · Empate', '2 · Visitante']

  return (
    <form onSubmit={submit} noValidate className="rounded-lg border border-line bg-surface p-4">
      <div className="flex items-center justify-between border-b border-line pb-2.5">
        <div>
          <h2 className="font-display text-lg font-bold uppercase tracking-wide leading-tight">Configurar Partido</h2>
          <p className="text-xs text-ink-muted">Clubes, fecha y cuotas 1X2</p>
        </div>
        <button
          type="button"
          onClick={swap}
          title="Intercambiar local y visitante"
          aria-label="Intercambiar local y visitante"
          className="inline-flex items-center gap-1.5 rounded border border-line bg-raised px-2.5 py-1.5 text-xs font-bold text-ink-muted hover:border-ink-muted hover:text-ink"
        >
          <ArrowLeftRight aria-hidden className="size-3.5" />
          Invertir
        </button>
      </div>

      <div className="mt-3.5 grid gap-3">
        <TeamSelect id="home" label="1 · Equipo Local" value={home} onChange={(v) => onChange({ home: v })} teams={teams} offline={offline} tone="var(--color-local)" />
        <TeamSelect id="away" label="2 · Equipo Visitante" value={away} onChange={(v) => onChange({ away: v })} teams={teams} offline={offline} tone="var(--color-away)" />

        <div className="border-t border-line/70 pt-3">
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="date" className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-ink-muted">
              <Calendar aria-hidden className="size-3.5 text-accent" />
              Fecha (AAAA-MM-DD)
            </label>
            {date && (
              <button
                type="button"
                onClick={() => onChange({ date: '' })}
                className="inline-flex items-center gap-1 text-xs font-bold text-accent hover:underline"
              >
                <RotateCcw aria-hidden className="size-3" />
                Más reciente
              </button>
            )}
          </div>
          <input
            id="date"
            type="date"
            min="2000-08-18"
            max={teams?.data_end ?? '2026-12-31'}
            value={date}
            onChange={(e) => onChange({ date: e.target.value })}
            className={inputBase}
          />
          {dates && dates.length > 0 && (
            <div className="relative mt-1.5">
              <select
                aria-label="Jornadas recientes con partidos"
                value={dates.some((d) => d.date === date) ? date : ''}
                onChange={(e) => onChange({ date: e.target.value })}
                className={`${inputBase} appearance-none py-1.5 pr-8 text-xs text-ink-muted`}
              >
                <option value="">
                  {date
                    ? `Fecha activa: ${formatDate(date)} (o elige jornada)`
                    : 'Atajo: elegir jornada reciente con partidos…'}
                </option>
                {dates.map((d) => (
                  <option key={d.date} value={d.date}>
                    {formatDate(d.date)} · {d.matches} {d.matches === 1 ? 'partido' : 'partidos'}
                  </option>
                ))}
              </select>
              <ChevronDown
                aria-hidden
                className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-muted"
              />
            </div>
          )}
          <p className="mt-1 text-xs text-ink-muted">
            Elige cualquier fecha en formato calendario (ej. 2023 o 2024). Vacío = datos hasta{' '}
            {teams?.data_end ? formatDate(teams.data_end) : 'hoy'}.
          </p>
        </div>

        <div className="border-t border-line/70 pt-3">
          <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-ink-muted">
            Cuotas de mercado 1X2 (opcional)
          </span>
          <div className="grid grid-cols-3 gap-1.5">
            {oddsLabels.map((l, i) => (
              <div key={l} className="rounded border border-line bg-canvas/60 p-1.5 text-center">
                <label htmlFor={`odd-${i}`} className="mb-1 block text-[11px] font-bold text-ink-muted">
                  {l}
                </label>
                <input
                  id={`odd-${i}`}
                  inputMode="decimal"
                  placeholder={['1.80', '3.60', '4.50'][i]}
                  value={odds[i]}
                  onChange={(e) => setOdds(odds.map((o, j) => (j === i ? e.target.value : o)))}
                  className="w-full rounded bg-raised px-2 py-1 text-center font-display text-sm font-bold text-accent focus:outline-none"
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <p role="alert" className="mt-3 rounded-md border border-danger/50 bg-danger/10 px-2.5 py-2 text-xs text-danger">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy || !teams}
        className="mt-4 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2 font-display text-base font-bold uppercase tracking-wide text-canvas hover:brightness-110 disabled:opacity-60"
      >
        {busy && <Loader2 aria-hidden className="size-4 animate-spin" />}
        {busy ? 'Calculando…' : 'Calcular pronóstico'}
      </button>
    </form>
  )
}

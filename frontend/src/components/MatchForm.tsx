import { useState } from 'react'
import { ArrowLeftRight, ChevronDown, Loader2 } from 'lucide-react'
import type { PredictRequest, TeamsResponse } from '../api'

interface Props {
  teams: TeamsResponse | null
  offline: boolean
  busy: boolean
  onSubmit: (req: PredictRequest) => void
}

const inputBase =
  'w-full rounded-md border border-line bg-raised px-3 py-2.5 text-base text-ink ' +
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
      <label htmlFor={id} className="mb-1.5 flex items-center gap-2 text-sm font-bold text-ink-muted">
        <span aria-hidden className="size-2.5 rounded-full" style={{ background: tone }} />
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={!teams}
          className={`${inputBase} appearance-none pr-10`}
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
          className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-ink-muted"
        />
      </div>
    </div>
  )
}

const toNumber = (s: string) => Number(s.trim().replace(',', '.'))

export default function MatchForm({ teams, offline, busy, onSubmit }: Props) {
  const [home, setHome] = useState('Arsenal')
  const [away, setAway] = useState('Chelsea')
  const [date, setDate] = useState('')
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
        setError('Las cuotas necesitan los tres valores (local, empate, visitante), cada uno mayor a 1,00.')
        return
      }
      parsed = nums as [number, number, number]
    }
    setError(null)
    onSubmit({ home_team: home, away_team: away, match_date: date || undefined, odds: parsed })
  }

  const swap = () => {
    setHome(away)
    setAway(home)
    setError(null)
  }

  const oddsLabels = ['Local', 'Empate', 'Visitante']

  return (
    <form onSubmit={submit} noValidate className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 className="font-display text-2xl font-bold leading-tight">Partido</h2>
      <p className="mt-1 text-sm text-ink-muted">Elige los dos equipos. Lo demás es opcional.</p>

      <div className="mt-5 grid gap-4">
        <TeamSelect id="home" label="Local" value={home} onChange={setHome} teams={teams} offline={offline} tone="var(--color-local)" />
        <div className="-my-1 flex justify-center">
          <button
            type="button"
            onClick={swap}
            aria-label="Intercambiar local y visitante"
            className="grid size-9 place-items-center rounded-full border border-line bg-raised text-ink-muted hover:border-ink-muted hover:text-ink"
          >
            <ArrowLeftRight aria-hidden className="size-4 rotate-90" />
          </button>
        </div>
        <TeamSelect id="away" label="Visitante" value={away} onChange={setAway} teams={teams} offline={offline} tone="var(--color-away)" />

        <div>
          <label htmlFor="date" className="mb-1.5 block text-sm font-bold text-ink-muted">
            Fecha del partido
          </label>
          <input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputBase} />
          <p className="mt-1.5 text-sm text-ink-muted">
            Con fecha, el modelo usa solo lo ocurrido antes. Sin fecha, usa los datos más recientes (hasta mayo de 2025).
          </p>
        </div>

        <details className="group rounded-md border border-line">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2.5 text-sm font-bold text-ink-muted hover:text-ink">
            Cuotas de mercado (opcional)
            <ChevronDown aria-hidden className="size-4 transition-transform group-open:rotate-180" />
          </summary>
          <div className="border-t border-line p-3">
            <div className="grid grid-cols-3 gap-2">
              {oddsLabels.map((l, i) => (
                <div key={l}>
                  <label htmlFor={`odd-${i}`} className="mb-1 block text-xs font-bold text-ink-muted">
                    {l}
                  </label>
                  <input
                    id={`odd-${i}`}
                    inputMode="decimal"
                    placeholder={['1,80', '3,60', '4,50'][i]}
                    value={odds[i]}
                    onChange={(e) => setOdds(odds.map((o, j) => (j === i ? e.target.value : o)))}
                    className={inputBase}
                  />
                </div>
              ))}
            </div>
            <p className="mt-2 text-sm text-ink-muted">
              Cuotas decimales previas al partido. Son un dato de entrada para el modelo, no una recomendación. Sin
              cuotas, el mercado se estima a partir del Elo.
            </p>
          </div>
        </details>
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-md border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy || !teams}
        className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 font-display text-lg font-bold text-canvas hover:brightness-110 disabled:opacity-60"
      >
        {busy && <Loader2 aria-hidden className="size-5 animate-spin" />}
        {busy ? 'Calculando…' : 'Calcular pronóstico'}
      </button>
    </form>
  )
}

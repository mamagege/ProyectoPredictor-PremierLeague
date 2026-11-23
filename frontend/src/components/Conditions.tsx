import { Check } from 'lucide-react'
import type { PredictResponse, TeamState } from '../api'
import { leader } from '../lib/compare'
import { num0, num1, num2, pct1 } from '../lib/format'

interface Metric {
  key: keyof TeamState
  label: string
  hint: string
  fmt: (n: number) => string
  better: 'high' | 'low' | null
}

const METRICS: Metric[] = [
  { key: 'elo', label: 'Elo', hint: 'Nivel de fuerza acumulado en toda su historia', fmt: num0, better: 'high' },
  { key: 'form5', label: 'Forma', hint: 'Puntos en sus últimos 5 partidos', fmt: num1, better: 'high' },
  { key: 'rolling_gf5', label: 'Goles a favor', hint: 'Promedio por partido, últimos 5', fmt: num2, better: 'high' },
  { key: 'rolling_ga5', label: 'Goles en contra', hint: 'Promedio por partido, últimos 5', fmt: num2, better: 'low' },
  { key: 'rest_days', label: 'Descanso', hint: 'Días desde su último partido', fmt: num0, better: null },
  { key: 'season_pts', label: 'Puntos de la temporada', hint: 'Acumulados antes de esta fecha', fmt: num0, better: 'high' },
  { key: 'season_gd', label: 'Diferencia de gol', hint: 'Goles a favor menos en contra, temporada', fmt: num0, better: 'high' },
]

export default function Conditions({ result }: { result: PredictResponse }) {
  const { home_state: h, away_state: a, h2h } = result
  const noH2H = h2h.home === 45 && h2h.draw === 25 && h2h.away === 30

  return (
    <section aria-labelledby="cond-title" className="rounded-lg border border-line bg-surface p-5 sm:p-6">
      <h2 id="cond-title" className="font-display text-2xl font-bold leading-tight">
        Condiciones previas
      </h2>
      <p className="mt-1 text-ink-muted">Lo que sabía el modelo de cada equipo antes del partido. La marca indica quién va mejor.</p>

      <div className="relative -mx-1 mt-4 overflow-x-auto px-1">
        <table className="w-full min-w-[460px] border-collapse text-base">
          <caption className="sr-only">Comparación de {result.home_team} y {result.away_team}</caption>
          <thead>
            <tr className="border-b border-line text-left text-sm text-ink-muted">
              <th scope="col" className="w-[30%] py-2 pr-3 font-bold">
                <span aria-hidden className="mr-2 inline-block size-2.5 rounded-full align-middle" style={{ background: 'var(--color-local)' }} />
                {result.home_team}
              </th>
              <th scope="col" className="py-2 text-center font-bold">Indicador</th>
              <th scope="col" className="w-[30%] py-2 pl-3 text-right font-bold">
                {result.away_team}
                <span aria-hidden className="ml-2 inline-block size-2.5 rounded-full align-middle" style={{ background: 'var(--color-away)' }} />
              </th>
            </tr>
          </thead>
          <tbody>
            {METRICS.map((m) => {
              const hv = h[m.key]
              const av = a[m.key]
              const lead = leader(m.better, hv, av)
              return (
                <tr key={m.key} className="border-b border-line last:border-0">
                  <td className={`py-3 pr-3 ${lead === 'home' ? 'font-bold text-ink' : 'text-ink-muted'}`}>
                    <span className="inline-flex items-center gap-1.5">
                      {lead === 'home' && <Check aria-hidden className="size-4 text-local" />}
                      {m.fmt(hv)}
                      {lead === 'home' && <span className="sr-only"> (mejor)</span>}
                    </span>
                  </td>
                  <th scope="row" className="px-2 py-3 text-center font-normal">
                    <span className="block font-bold">{m.label}</span>
                    <span className="block text-sm text-ink-muted">{m.hint}</span>
                  </th>
                  <td className={`py-3 pl-3 text-right ${lead === 'away' ? 'font-bold text-ink' : 'text-ink-muted'}`}>
                    <span className="inline-flex items-center gap-1.5">
                      {lead === 'away' && <Check aria-hidden className="size-4 text-away" />}
                      {m.fmt(av)}
                      {lead === 'away' && <span className="sr-only"> (mejor)</span>}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-6 border-t border-line pt-5">
        <h3 className="font-bold">Historial directo</h3>
        {noH2H ? (
          <p className="mt-1 text-sm text-ink-muted">
            No hay enfrentamientos previos en los datos: el modelo usa la frecuencia general de la liga.
          </p>
        ) : (
          <>
            <div role="img" aria-label={`${result.home_team} ${pct1(h2h.home)}, empates ${pct1(h2h.draw)}, ${result.away_team} ${pct1(h2h.away)}`} className="mt-3 flex h-3 gap-0.5 overflow-hidden rounded-sm">
              <div style={{ width: `${h2h.home}%`, background: 'var(--color-local)' }} />
              <div style={{ width: `${h2h.draw}%`, background: 'var(--color-draw)' }} />
              <div style={{ width: `${h2h.away}%`, background: 'var(--color-away)' }} />
            </div>
            <dl className="mt-2 grid grid-cols-3 gap-2 text-sm">
              <div>
                <dt className="text-ink-muted">{result.home_team}</dt>
                <dd className="font-bold">{pct1(h2h.home)}</dd>
              </div>
              <div className="text-center">
                <dt className="text-ink-muted">Empates</dt>
                <dd className="font-bold">{pct1(h2h.draw)}</dd>
              </div>
              <div className="text-right">
                <dt className="text-ink-muted">{result.away_team}</dt>
                <dd className="font-bold">{pct1(h2h.away)}</dd>
              </div>
            </dl>
          </>
        )}
      </div>
    </section>
  )
}

import { useEffect, useState } from 'react'
import { api, type MetricsResponse, type TeamsResponse } from './api'
import PredictorView from './views/PredictorView'
import ModelView from './views/ModelView'
import Intro from './components/Intro'

type Tab = 'predictor' | 'modelo'

const tabFromHash = (): Tab => (window.location.hash === '#modelo' ? 'modelo' : 'predictor')

function Mark() {
  return (
    <svg aria-hidden viewBox="0 0 32 32" className="size-8">
      <g fill="none" strokeLinecap="round" strokeWidth="2.6">
        <path d="M6 24a14 14 0 0 1 14-14" stroke="var(--color-local)" />
        <path d="M6 24a9 9 0 0 1 9-9" stroke="var(--color-draw)" />
        <path d="M6 24a4 4 0 0 1 4-4" stroke="var(--color-away)" />
      </g>
    </svg>
  )
}

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromHash)
  const [teams, setTeams] = useState<TeamsResponse | null>(null)
  const [teamsError, setTeamsError] = useState<string | null>(null)
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [metricsError, setMetricsError] = useState<string | null>(null)

  useEffect(() => {
    const onHash = () => setTab(tabFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    api.teams().then(setTeams).catch((e: Error) => setTeamsError(e.message))
    api.metrics().then(setMetrics).catch((e: Error) => setMetricsError(e.message))
  }, [])

  const go = (t: Tab) => {
    window.location.hash = t === 'modelo' ? '#modelo' : '#predictor'
    setTab(t)
  }

  const navItem = (t: Tab, label: string) => (
    <a
      href={t === 'modelo' ? '#modelo' : '#predictor'}
      aria-current={tab === t ? 'page' : undefined}
      onClick={(e) => {
        e.preventDefault()
        go(t)
      }}
      className={`inline-flex min-h-11 items-center border-b-2 px-1 font-display text-lg font-bold ${
        tab === t ? 'border-action text-text' : 'border-transparent text-muted hover:text-text'
      }`}
    >
      {label}
    </a>
  )

  return (
    <div className="min-h-dvh">
      <Intro />
      <header className="border-b border-line bg-panel">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <a href="#predictor" onClick={(e) => { e.preventDefault(); go('predictor') }} className="flex items-center gap-2.5 py-3">
            <Mark />
            <span className="font-display text-2xl font-bold leading-none">Predictor EPL</span>
          </a>
          <nav aria-label="Principal" className="flex items-center gap-5">
            {navItem('predictor', 'Predictor')}
            {navItem('modelo', 'Modelo')}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {tab === 'predictor' ? (
          <PredictorView teams={teams} teamsError={teamsError} metrics={metrics} onOpenModel={() => go('modelo')} />
        ) : (
          <ModelView metrics={metrics} error={metricsError} />
        )}
      </main>

      <footer className="mx-auto max-w-6xl px-4 pb-8 text-sm text-muted sm:px-6">
        Proyecto PTIA · Escuela Colombiana de Ingeniería Julio Garavito · Grupo 04. Probabilidades estadísticas para
        entender el juego; no son una recomendación de apuesta.
      </footer>
    </div>
  )
}

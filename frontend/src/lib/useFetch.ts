import { useEffect, useState } from 'react'

interface Settled<T> {
  load: () => Promise<T>
  attempt: number
  data: T | null
  error: string | null
}

/**
 * Pide datos a la API cuando cambia `load` (envuélvela en useCallback con sus dependencias) y permite reintentar.
 * Mientras llega la respuesta de la petición vigente, `loading` es true y no se muestran datos viejos.
 */
export function useFetch<T>(load: () => Promise<T>) {
  const [attempt, setAttempt] = useState(0)
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    let cancelled = false
    load()
      .then((data) => !cancelled && setSettled({ load, attempt, data, error: null }))
      .catch((e: Error) => !cancelled && setSettled({ load, attempt, data: null, error: e.message }))
    return () => {
      cancelled = true
    }
  }, [load, attempt])

  const loading = !settled || settled.load !== load || settled.attempt !== attempt
  return {
    loading,
    data: loading ? null : settled.data,
    error: loading ? null : settled.error,
    retry: () => setAttempt((a) => a + 1),
  }
}

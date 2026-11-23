import type { ReactNode } from 'react'
import { RotateCw, TriangleAlert } from 'lucide-react'

interface Props {
  title?: string
  message: string
  /** Si se pasa, muestra «Reintentar»; solo para errores que reintentar puede resolver. */
  onRetry?: (() => void) | null
  children?: ReactNode
}

/** Error con causa y recuperación: nunca una pantalla en blanco. */
export default function ErrorNotice({ title, message, onRetry, children }: Props) {
  return (
    <div role="alert" className="flex gap-3 rounded-md border border-danger/50 bg-danger/10 p-4 text-danger">
      <TriangleAlert aria-hidden className="mt-0.5 size-5 shrink-0" />
      <div className="min-w-0">
        {title && <p className="font-bold">{title}</p>}
        <p className={title ? 'mt-1 text-base' : 'text-base'}>{message}</p>
        {children && <div className="mt-2 text-base text-ink">{children}</div>}
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-md border border-danger/60 px-4 font-bold text-danger hover:bg-danger/10"
          >
            <RotateCw aria-hidden className="size-4" />
            Reintentar
          </button>
        )}
      </div>
    </div>
  )
}

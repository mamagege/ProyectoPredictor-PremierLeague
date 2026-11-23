import { useEffect, useLayoutEffect, useRef, useState } from 'react'

/**
 * Entrada de primera carga: un trazo SVG de 3222×3114 se desenreda sobre un fondo
 * sólido y revela la app. Se reproduce una vez por sesión y no se repite.
 *
 * Línea de tiempo: 250 ms de pausa con la cubierta opaca + 2000 ms de desenredo.
 * - strokeDashoffset: 0 → -longitud, cubic-bezier(.645,.045,.355,1)
 * - grosor: .31 → .08 × √((3222²+3114²)/2), cubic-bezier(.75,.15,.15,1)
 * - el fondo se desvanece en el primer 18 % del desenredo
 * - la marca se oculta a los 950 ms del desenredo
 * - al terminar, la cubierta se elimina
 */

const PATH =
  'M299.654 453.865C505.574 319.225 711.494 184.585 836.054 109.945C960.614 35.3048 997.574 24.7448 944.014 110.385C890.454 196.025 745.254 378.185 571.454 634.385C397.654 890.585 199.654 1215.3 110.854 1382.58C22.0544 1549.86 48.4544 1549.86 77.8944 1540.62C107.334 1531.38 139.014 1512.9 367.854 1319.9C596.694 1126.9 1021.73 759.945 1255.21 555.065C1488.69 350.185 1517.73 318.505 1527.41 306.145C1537.09 293.785 1526.53 301.705 1346.85 618.625C1167.17 935.545 818.694 1561.22 635.214 1896.74C451.734 2232.26 443.814 2258.66 447.654 2268.3C451.494 2277.94 467.334 2270.02 511.134 2236.9C554.934 2203.78 626.214 2145.7 966.534 1817.46C1306.85 1489.22 1914.05 892.585 2263.81 557.505C2613.57 222.425 2687.49 166.985 2741.41 129.185C2795.33 91.3848 2827.01 72.9048 2843.33 67.3448C2859.65 61.7848 2859.65 69.7048 2849.09 96.2248C2838.53 122.745 2817.41 167.625 2584.77 544.505C2352.13 921.385 1370.37 2165.43 1139.25 2537.83C908.134 2910.23 902.854 2926.07 902.774 2939.51C902.694 2952.95 907.974 2963.51 1255.21 2613.87C1602.45 2264.23 2829.73 1017.54 2903.53 1071.46C2977.33 1125.38 2176.12 2817.04 2128 3037C2079.88 3256.96 2911.24 2018.56 3172 1793'

const W = 3222
const H = 3114
const D = Math.sqrt((W * W + H * H) / 2)
const HOLD_MS = 250
const UNWIND_MS = 2000
const MARK_HIDE_MS = 950
const FADE_END = 0.18
const SEEN_KEY = 'epl-intro-seen'

/** Curva cubic-bezier(x1, y1, x2, y2) como función t → valor (método de Newton). */
function bezier(x1: number, y1: number, x2: number, y2: number) {
  const cx = 3 * x1
  const bx = 3 * (x2 - x1) - cx
  const ax = 1 - cx - bx
  const cy = 3 * y1
  const by = 3 * (y2 - y1) - cy
  const ay = 1 - cy - by
  const sx = (t: number) => ((ax * t + bx) * t + cx) * t
  const sy = (t: number) => ((ay * t + by) * t + cy) * t
  const dx = (t: number) => (3 * ax * t + 2 * bx) * t + cx
  return (x: number) => {
    if (x <= 0) return 0
    if (x >= 1) return 1
    let t = x
    for (let i = 0; i < 8; i++) {
      const err = sx(t) - x
      if (Math.abs(err) < 1e-5) break
      const d = dx(t)
      if (Math.abs(d) < 1e-6) break
      t -= err / d
    }
    return sy(Math.min(1, Math.max(0, t)))
  }
}

const easeDash = bezier(0.645, 0.045, 0.355, 1)
const easeWidth = bezier(0.75, 0.15, 0.15, 1)

function alreadySeen(): boolean {
  try {
    return sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}
function markSeen() {
  try {
    sessionStorage.setItem(SEEN_KEY, '1')
  } catch {
    /* sin almacenamiento: la intro simplemente puede repetirse */
  }
}

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

interface Props {
  /** Color de la cubierta y del trazo (comparten color para que el inicio sea opaco). */
  ground?: string
  /** Color de la marca centrada. */
  ink?: string
  /** Texto de la marca. */
  title?: string
}

export default function Intro({ ground = '#28466f', ink = '#e6eef9', title = 'Predictor EPL' }: Props) {
  const [active, setActive] = useState(() => !alreadySeen() && !reducedMotion())
  const groundRef = useRef<SVGRectElement>(null)
  const pathRef = useRef<SVGPathElement>(null)
  const markRef = useRef<HTMLDivElement>(null)
  const lengthRef = useRef(0)

  // Mide la longitud real del trazo antes del primer pintado.
  useLayoutEffect(() => {
    if (active && pathRef.current) {
      const L = pathRef.current.getTotalLength()
      lengthRef.current = L
      pathRef.current.style.strokeDasharray = String(L)
      pathRef.current.style.strokeDashoffset = '0'
    }
  }, [active])

  useEffect(() => {
    if (!active) return

    let raf = 0
    let last = 0
    let elapsed = 0 // solo avanza mientras la pestaña es visible
    let cancelled = false

    const finish = () => {
      cancelAnimationFrame(raf)
      markSeen()
      setActive(false)
    }

    // Función de dibujo guiada por el tiempo transcurrido normalizado.
    const render = (ms: number) => {
      const path = pathRef.current
      const gnd = groundRef.current
      const mark = markRef.current
      if (!path || !gnd || !mark) return
      const u = Math.min(1, Math.max(0, (ms - HOLD_MS) / UNWIND_MS))
      path.style.strokeDashoffset = String(-lengthRef.current * easeDash(u))
      const widthK = 0.31 + (0.08 - 0.31) * easeWidth(u)
      path.style.strokeWidth = String(widthK * D)
      gnd.style.opacity = String(1 - Math.min(1, u / FADE_END))
      mark.style.opacity = ms - HOLD_MS < MARK_HIDE_MS ? '1' : '0'
      if (u >= 1) finish()
    }

    const tick = (now: number) => {
      if (cancelled) return
      if (last) elapsed += Math.min(64, now - last)
      last = now
      render(elapsed)
      if (elapsed < HOLD_MS + UNWIND_MS) raf = requestAnimationFrame(tick)
    }

    const start = () => {
      last = 0
      raf = requestAnimationFrame(tick)
    }

    // Pestaña oculta: se congela y al volver continúa donde estaba.
    const onVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(raf)
        last = 0
      } else if (!cancelled) {
        start()
      }
    }

    // Movimiento reducido en vivo: muestra de inmediato la composición descubierta.
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onMotion = () => mq.matches && finish()

    // Salida rápida con Escape o con un toque/clic.
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && finish()

    document.addEventListener('visibilitychange', onVisibility)
    mq.addEventListener('change', onMotion)
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', finish)

    // Con la tipografía lista, la marca no parpadea al cambiar de fuente.
    document.fonts.ready.then(() => {
      if (!cancelled && !document.hidden) start()
    })

    return () => {
      cancelled = true
      cancelAnimationFrame(raf)
      document.removeEventListener('visibilitychange', onVisibility)
      mq.removeEventListener('change', onMotion)
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('pointerdown', finish)
    }
  }, [active])

  if (!active) return null

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-[100] overflow-hidden">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        fill="none"
        className="absolute inset-0 size-full"
      >
        <rect ref={groundRef} width={W} height={H} fill={ground} />
        <path
          ref={pathRef}
          d={PATH}
          stroke={ground}
          strokeWidth={0.31 * D}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div ref={markRef} className="absolute inset-0 grid place-items-center" style={{ color: ink }}>
        <div className="flex items-center gap-3">
          <svg viewBox="0 0 32 32" className="size-14">
            <g fill="none" strokeLinecap="round" strokeWidth="2.6" stroke="currentColor">
              <path d="M6 24a14 14 0 0 1 14-14" />
              <path d="M6 24a9 9 0 0 1 9-9" />
              <path d="M6 24a4 4 0 0 1 4-4" />
            </g>
          </svg>
          <span className="font-display text-5xl font-bold leading-none sm:text-6xl">{title}</span>
        </div>
      </div>
    </div>
  )
}

const nf = (digits: number) =>
  new Intl.NumberFormat('es-CO', { minimumFractionDigits: digits, maximumFractionDigits: digits })

const f0 = nf(0)
const f1 = nf(1)
const f2 = nf(2)

export const num0 = (n: number) => f0.format(n)
export const num1 = (n: number) => f1.format(n)
export const num2 = (n: number) => f2.format(n)
export const pct1 = (n: number) => `${f1.format(n)} %`
export const signed1 = (n: number) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${f1.format(Math.abs(n))}`

export function formatDate(iso: string | null): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'long', year: 'numeric' }).format(
    new Date(y, m - 1, d),
  )
}

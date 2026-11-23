const ITEMS: [string, string][] = [
  [
    'Qué hace la aplicación con tus datos',
    'Cuando calculas un pronóstico, el navegador envía los equipos, la fecha y las cuotas que escribiste a la API de este mismo proyecto (el mismo origen que sirve la página). Solo se usan para calcular la respuesta y no se guardan.',
  ],
  [
    'Qué no hace',
    'No hay cuentas, cookies, analítica ni publicidad. No se contacta a ningún servicio de terceros: las tipografías y los iconos se sirven desde la propia aplicación.',
  ],
  [
    'Qué se guarda en tu navegador',
    'Nada: la aplicación no utiliza cookies ni almacenamiento local en tu navegador.',
  ],
  [
    'De dónde salen los datos de los partidos',
    'De tres conjuntos de datos públicos de Kaggle incluidos en el repositorio del proyecto, con partidos desde agosto de 2000 hasta agosto de 2026. Lo que escribes en la aplicación nunca se envía a esas fuentes.',
  ],
  [
    'Sobre las apuestas',
    'Las cuotas son un dato opcional de entrada para el modelo. La aplicación entrega probabilidades estadísticas para entender el juego y no es una recomendación de apuesta.',
  ],
  [
    'Política de la institución',
    'Este es un proyecto académico del curso PTIA de la Escuela Colombiana de Ingeniería Julio Garavito. Para la política oficial de tratamiento de datos de la Escuela, consulta su sitio institucional.',
  ],
]

export default function PrivacyView() {
  return (
    <article className="max-w-[65ch]">
      <h1 tabIndex={-1} className="text-balance font-display text-4xl font-bold leading-tight focus:outline-none sm:text-5xl">
        Privacidad
      </h1>
      <p className="mt-3 text-lg text-ink-muted">
        Lo que esta aplicación hace de verdad con tu información, sin texto genérico.
      </p>
      <div className="mt-8 grid gap-6">
        {ITEMS.map(([title, body]) => (
          <section key={title}>
            <h2 className="font-display text-2xl font-bold leading-tight">{title}</h2>
            <p className="mt-1 text-base text-ink-muted">{body}</p>
          </section>
        ))}
      </div>
    </article>
  )
}

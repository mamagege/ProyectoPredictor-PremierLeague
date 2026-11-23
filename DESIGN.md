---
name: Predictor EPL
description: Boletín nocturno de probabilidades pre-partido de la Premier League, con la incertidumbre siempre a la vista.
colors:
  canvas: "#07142a"
  surface: "#0b1d38"
  raised: "#12294b"
  line: "#28466f"
  ink: "#e6eef9"
  ink-muted: "#a3b6d1"
  outcome-home: "#1fee6e"
  outcome-draw: "#ffd60a"
  outcome-away: "#ff3355"
  accent: "#5aa0ff"
  danger: "#ff9aa9"
typography:
  display:
    fontFamily: "Barlow Semi Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "3.75rem"
    fontWeight: 700
    lineHeight: 1
  headline:
    fontFamily: "Barlow Semi Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 700
    lineHeight: 1.1
  title:
    fontFamily: "Barlow Semi Condensed, Barlow, ui-sans-serif, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.25
  body:
    fontFamily: "Barlow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Barlow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.43
rounded:
  sm: "2px"
  md: "6px"
  lg: "8px"
  full: "9999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "20px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.canvas}"
    typography: "{typography.title}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
    height: "44px"
  input:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "24px"
  outcome-track:
    backgroundColor: "{colors.raised}"
    rounded: "{rounded.sm}"
    height: "12px"
---

# Design System: Predictor EPL

## Overview

**Creative North Star: "El Boletín del Partido"**

*Pronóstico* es, en español, tanto predicción como parte del tiempo. El sistema toma esa coincidencia al pie de la letra: cada partido recibe un boletín con tres probabilidades que suman 100 %, una escala de 0 a 100 y la frecuencia de 2021 a 2025 marcada sobre cada barra, igual que un parte meteorológico compara el día con lo habitual. La escena de uso es el sofá, la noche previa al partido, en el móvil; por eso el sistema es oscuro, tinta azul, y cada cifra se lee de un vistazo.

La densidad es de herramienta, no de póster: barra superior estándar, columna de entrada a la izquierda, boletín a la derecha, tablas de verdad para comparar. El mundo meteorológico aporta solo cuatro cosas: la paleta de estadio (verde césped, amarillo y rojo de tarjeta), la tipografía condensada de boletín con cifras tabulares, la densidad ordenada y un gesto firma, la marca de la frecuencia 2021–25. Nunca aporta iconos de sol y nubes ni estructura.

**Key Characteristics:**
- Tinta azul nocturna con tres tonos de señal, uno por desenlace; el color nunca va solo, siempre con etiqueta y cifra.
- Plano por defecto: profundidad por capas tonales y líneas finas, sin sombras.
- Cifras grandes y condensadas; texto de apoyo claro y sin tecnicismos.
- La incertidumbre es el contenido: nunca un ganador solitario.

## Colors

Paleta de noche con tres colores de estadio: un fondo azul tinta en tres escalones y tres tonos de señal saturados que identifican Local, Empate y Visitante.

### Primary
- **Verde Césped** (#1fee6e): Victoria local. Barra, cifra grande, punto del selector «Local» y segmento del historial directo.

### Secondary
- **Amarillo Tarjeta** (#ffd60a): Empate, y los avisos informativos (datos antiguos).
- **Rojo Tarjeta** (#ff3355): Victoria visitante y celdas de error en la matriz de confusión.

### Tertiary
- **Azul de Acción** (#5aa0ff): único color de acción: botón primario, enlaces, anillo de foco, pestaña activa, selección de texto.
- **Rosa de Error** (#ff9aa9): mensajes de error de validación y de servicio.

### Neutral
- **Tinta de Medianoche** (#07142a): fondo de la página.
- **Panel Nocturno** (#0b1d38): superficie de paneles y barra superior.
- **Capa Elevada** (#12294b): campos de entrada, pistas de las barras, fila resaltada de tablas.
- **Línea de Isobara** (#28466f): bordes y separadores de 1 px.
- **Texto Boletín** (#e6eef9): texto principal.
- **Texto Atenuado** (#a3b6d1): etiquetas, ayudas y valores secundarios (≥ 4,5:1 sobre el panel).

### Named Rules
**The Three Voices Rule.** Verde, amarillo y rojo significan únicamente Local, Empate y Visitante (y, por extensión, acierto, aviso y error). No se usan como decoración ni para otro dato.

**The One Action Rule.** El azul de acción es el único color de interacción. Si algo es clicable y no es un resultado, es azul o texto.

**The Never-Alone Rule.** Ninguna probabilidad depende solo del color: siempre lleva etiqueta y valor numérico. Verde y rojo son el par que más se confunde en el daltonismo; aquí se distinguen además por la posición (local, empate, visitante), el texto y la luminosidad (el verde y el amarillo son mucho más claros que el rojo).

**The Role Names Rule.** Los colores se nombran por rol (`canvas`, `surface`, `line`, `ink`, `accent`), no por tono, y se declaran como canales RGB en `:root` (por ejemplo `--surface: 11 29 56`); Tailwind los lee como `rgb(var(--surface))`. Un modo claro es cambiar esos valores. Los tres colores reservados (`outcome-*`) conservan su significado en cualquier modo.

## Typography

**Display Font:** Barlow Semi Condensed (con Barlow, sans-serif)
**Body Font:** Barlow (con system-ui, sans-serif)
**Label/Mono Font:** ninguna; las cifras usan numerales tabulares de Barlow.

**Character:** Condensada y firme en los titulares y las cifras, abierta y neutra en el texto corrido. Se parece a la rotulación de un boletín, no a un tablero técnico. Autoalojada en WOFF2 (400 y 700).

### Hierarchy
- **Display** (700, 3rem–3.75rem, 1): cifra de probabilidad de cada desenlace, con el «%» en tamaño menor y color atenuado.
- **Headline** (700, 2.25rem–3rem, 1.1): título de la pantalla Modelo.
- **Title** (700, 1.5rem, 1.25): título de cada panel y texto del botón principal (1.125rem).
- **Body** (400, 1rem–1.125rem, 1.5): explicaciones; medida máxima de 65 caracteres en párrafos introductorios.
- **Label** (700, 0.875rem, 1.43): etiquetas de campos, encabezados de tabla y notas.

### Named Rules
**The Tabular Rule.** Todas las cifras llevan numerales tabulares para alinear columnas; los decimales usan coma (es-CO).

**The Two Weights Rule.** Solo 400 y 700. La jerarquía sale del tamaño y del contraste, no de pesos intermedios.

## Layout

Contenedor centrado de 72rem (1152 px) con márgenes de 16 px en móvil y 24 px desde 640 px. En escritorio (≥ 1024 px) la pantalla Predictor es una rejilla de dos columnas: formulario fijo de 380 px a la izquierda, que se queda visible al hacer scroll, y el boletín con las condiciones previas a la derecha. Por debajo de 1024 px todo se apila en una columna con el formulario primero. La pantalla Modelo es de una columna, con matriz de confusión y metodología lado a lado desde 1280 px.

Ritmo de espaciado: 20 px entre paneles y dentro de ellos en móvil, 24 px desde 640 px; 16 px entre campos; filas de tabla de 12 px verticales. Las rejillas usan `minmax(0, 1fr)` y las tablas anchas se desplazan dentro de su panel: la página nunca desborda en horizontal (verificado a 375 px).

## Elevation & Depth

Plano. La profundidad se logra con tres escalones tonales (tinta, panel, capa elevada) y bordes de 1 px en azul de isobara; no hay sombras en ningún componente. El único elemento que «sale» de la superficie es la marca blanca de la frecuencia 2021–25, que sobrepasa la barra 6 px por arriba.

### Named Rules
**The Flat-By-Default Rule.** Ninguna sombra ni desenfoque decorativo. La jerarquía se construye con el escalón tonal y el borde fino.

## Shapes

Esquinas contenidas: paneles de 8 px, campos y botones de 6 px, barras de probabilidad de 2 px (casi rectas, como una escala de instrumento) y círculos completos solo para puntos de leyenda y el botón de intercambio. Bordes de 1 px en azul de isobara; sin recortes ni siluetas especiales. La marca de la normal es una línea vertical de 2 px con extremos redondeados.

## Components

### Buttons
- **Shape:** esquina contenida (6 px), altura mínima de 44 px para el tacto.
- **Primary:** fondo azul de acción (#5aa0ff) con texto tinta (#07142a), tipografía Title de 1.125rem, ancho completo en el formulario. Un solo botón primario por pantalla: «Calcular pronóstico».
- **Hover / Focus:** hover aumenta el brillo; foco con anillo de 2 px azul de acción a 2 px de distancia; estado ocupado con indicador giratorio y texto «Calculando…»; deshabilitado al 60 % de opacidad.
- **Secondary:** botón circular de 36 px con borde fino para intercambiar equipos; enlace subrayado en azul para «Ver cómo se evaluó».

### Cards / Containers
- **Corner Style:** 8 px.
- **Background:** panel nocturno (#0b1d38) con borde de 1 px.
- **Shadow Strategy:** ninguna (ver Elevation & Depth).
- **Border:** isobara (#28466f).
- **Internal Padding:** 20 px en móvil, 24 px desde 640 px. Nunca se anidan paneles.

### Inputs / Fields
- **Style:** fondo capa elevada, borde fino, 6 px de radio, texto de 1rem; los selectores son nativos con flecha dibujada. El punto de color junto a la etiqueta identifica Local (verde) y Visitante (rojo).
- **Focus:** anillo azul de acción de 2 px; el borde sube a texto atenuado al pasar el cursor.
- **Error / Disabled:** el error aparece en un bloque con borde y fondo rosa tenue, con `role="alert"` y texto que nombra el problema y cómo recuperarse; deshabilitado al 50 %.

### Navigation
Barra superior estándar sobre el panel nocturno: marca (tres isobaras de colores + «Predictor EPL») a la izquierda y pestañas «Predictor» / «Modelo» a la derecha. La pestaña activa lleva un subrayado de 2 px en azul de acción y `aria-current="page"`; las inactivas van en texto atenuado. Misma disposición en móvil, sin menú hamburguesa.

### Outcome Bar (componente firma)
Sobre la lista, una barra apilada de 16 px con los tres tramos del 100 % da la forma de la distribución de un vistazo. Cada fila: punto de color y etiqueta a la izquierda («Victoria de Arsenal», con «más probable» en pequeño si corresponde), cifra Display a la derecha en el color del desenlace; debajo una pista de 12 px de capa elevada con relleno del color y la **marca blanca de la frecuencia 2021–25** (frecuencia real del desenlace en los 1.520 partidos de prueba); al pie, «Frecuencia 2021–25: x %» y la diferencia en puntos con una flecha. En el estado vacío la cifra es un guion atenuado. Las barras crecen una vez desde la izquierda, con 90 ms de desfase entre filas; al recalcular el mismo partido aparece un aviso persistente con el cambio respecto al cálculo anterior.

### Tablas
Tablas semánticas con encabezados de fila y de columna, separadores de 1 px, sin cebra. El mejor valor de cada fila o columna lleva una marca de verificación y negrita (con texto oculto «mejor» para lectores de pantalla). La matriz de confusión usa una escala neutra (texto boletín sobre capa elevada, proporcional al porcentaje de la fila, máximo 40 %) y marca los aciertos de la diagonal con un borde de 2 px: no reutiliza verde ni rojo, que significan Local y Visitante.

### Avisos
Bloque amarillo (`role="status"`) para datos antiguos de un equipo; bloque rosa (`role="alert"`) para errores. Siempre con icono dibujado (Lucide), texto que explica la causa y qué hacer. Los errores que reintentar puede resolver (sin conexión o fallo del servidor) llevan el botón «Reintentar» de 44 px; los de validación, no.

### Estados de cada vista
Toda vista tiene cuatro estados y nunca queda en blanco: **cargando** (en el Predictor, las cifras pulsan con la forma final del boletín; en Modelo, tres marcadores con la altura de los paneles; sin movimiento con `prefers-reduced-motion`), **vacío** (las barras con la frecuencia 2021–25 y un guion atenuado), **error** con causa y recuperación, y **datos de ejemplo** señalados con una etiqueta «Datos de ejemplo» cuando la API responde en modo simulado. Tras cambiar de pantalla, el foco pasa al título de la vista nueva y un `role="status"` oculto anuncia el cambio.

### Fecha y partidos
La fecha es un selector nativo con las fechas que tienen partidos en el historial (más recientes primero, con la cantidad de partidos de cada una), no un campo para escribir; «Datos más recientes» es la opción por omisión. Debajo del boletín, a ancho completo, dos paneles de una sola superficie con filas separadas por líneas finas: **Próximos partidos** (desde un calendario opcional; si no existe, lo dice sin inventar partidos) y **Últimos partidos jugados** o **Partidos del día** elegido. Cada fila es un botón de al menos 56 px: tocarla carga los equipos y la fecha en el formulario y calcula al instante. En los partidos ya jugados, el boletín añade una línea con el resultado real, si el modelo acertó el desenlace y qué probabilidad le había dado a lo que ocurrió, con iconos y texto neutros (sin verde ni rojo, que son de Local y Visitante).

### Calibración
Panel de la pantalla Modelo con un diagrama de confiabilidad dibujado en SVG: eje horizontal, la probabilidad que dio el modelo; eje vertical, la frecuencia con la que el resultado ocurrió; una línea por resultado (verde Local, amarillo Empate, rojo Visitante) sobre una diagonal discontinua de calibración perfecta. El tamaño de cada punto crece con los partidos que agrupa y cada uno lleva su descripción en un `<title>`; la leyenda va en texto fuera del gráfico, así que el color nunca va solo. Al lado, el error de calibración (ECE), la temperatura y lo que cambian los umbrales bayesianos en validación, siempre con los números que entrega el backend.

### Intro de entrada
Cubierta de pantalla completa que se reproduce en cada carga de la página: fondo sólido en azul de isobara (#28466f) con la marca centrada en texto boletín (#e6eef9). Tras 250 ms, un trazo continuo del mismo color se desenreda durante 2 s (desfase del trazo con `cubic-bezier(.645,.045,.355,1)`, grosor de 0,31 a 0,08 con `cubic-bezier(.75,.15,.15,1)`), el fondo se desvanece en el primer 18 %, la marca desaparece a los 950 ms y la cubierta se elimina al terminar. Escape o un toque la saltan; con `prefers-reduced-motion` no aparece; se congela con la pestaña oculta. Es el único movimiento de gran escala del sistema.

## Do's and Don'ts

### Do:
- **Do** mostrar siempre las tres probabilidades juntas, con cifra y etiqueta, y la frecuencia 2021–25 de cada una.
- **Do** usar el azul de acción (#5aa0ff) solo para lo que se puede pulsar.
- **Do** mantener el sistema plano: separar con escalones tonales y bordes de 1 px.
- **Do** escribir en español con coma decimal y explicar cada indicador sin jerga de ML.
- **Do** respetar `prefers-reduced-motion`: las barras y el aviso de cambio no se animan.
- **Do** cuidar el contraste: texto principal y atenuado ≥ 4,5:1 sobre panel y fondo.

### Don't:
- **Don't** destacar un «ganador» solitario ni usar lenguaje de apuestas («pick», «apostar», «seguro»); las cuotas son un dato de entrada, no una recomendación.
- **Don't** usar verde, amarillo o rojo para decoración o para datos que no sean Local, Empate y Visitante.
- **Don't** añadir sombras, degradados de texto, desenfoque decorativo ni iconos de clima (sol, nubes).
- **Don't** anidar paneles ni repetir tarjetas iguales de icono, título y texto como estructura de página.
- **Don't** usar escudos o marcas de clubes sin licencia, ni inventar datos que la API no entrega.
- **Don't** depender solo del color para transmitir un resultado.

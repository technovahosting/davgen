# Tema claro / oscuro / del sistema e interfaz adaptable

davgen genera siempre estos archivos (son aditivos: no pisan nada tuyo):

| Archivo | Qué hace |
|---|---|
| `src/services/tema.js` | Aplica y recuerda el tema: `sistema` (por defecto), `claro` u `oscuro` |
| `src/components/generados/SelectorTema.jsx` | Los tres botones para elegirlo |

Un proyecto **nuevo** ya los trae montados en `App.jsx`. En un proyecto que ya
tenía su propio `App.jsx` (davgen no lo regenera) se montan con dos líneas:

```jsx
import './services/tema'                                      // aplica el tema al cargar
import SelectorTema from './components/generados/SelectorTema'

<SelectorTema />        {/* donde quieras: barra superior, login… */}
```

## Requisito en `src/index.css`

Los dos temas se declaran una vez, junto a Tailwind y daisyUI:

```css
@import "tailwindcss";
@plugin "daisyui" {
  themes: light --default, dark --prefersdark;
}
```

`--prefersdark` es lo que hace que, sin elegir nada, la aplicación siga al
sistema operativo. Cuando la persona elige claro u oscuro, `tema.js` pone
`data-theme` en `<html>` y esa elección manda.

## Para que tus pantallas acompañen el tema

Usa los colores **semánticos** de daisyUI en vez de colores fijos:

| En vez de… | Usa… |
|---|---|
| `bg-white`, `#fff` | `bg-base-100` |
| fondo de página gris | `bg-base-200` |
| `text-black`, `#111` | `text-base-content` |
| bordes grises | `border-base-300` |
| azul de marca | `btn-primary`, `text-primary`, `bg-primary` |

Un color escrito a mano (`style={{ background: '#0f172a' }}`) no cambia con el
tema: ese fue el motivo por el que el `App.jsx` de versiones anteriores se veía
siempre oscuro.

## Para que funcione bien en el celular

- El menú lateral es un cajón: fijo en pantallas grandes (`lg:drawer-open`) y
  oculto tras el botón ☰ en el celular.
- Las tablas van dentro de un contenedor con `overflow-x-auto`: se deslizan de
  lado sin ensanchar la página.
- Formularios en una columna que pasa a dos con `sm:grid-cols-2`.
- `index.html` debe conservar
  `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
  (la plantilla de Vite ya lo trae).

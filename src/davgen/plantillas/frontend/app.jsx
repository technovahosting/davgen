// App.jsx — personalizable: el generador NO lo regenera tras la primera creación.
// Arquitectura: un solo proyecto React subdividido internamente por módulo.
// Flujo: Portal → Login → App (menú lateral con los módulos de MODULOS_GENERADOS).
//
// Interfaz web ADAPTABLE (celular, tablet y PC) y con tema claro, oscuro o el
// del sistema: usa los colores semánticos de daisyUI (bg-base-100, btn-primary…)
// en vez de colores fijos. Ver components/generados/LEEME-TEMA.md.
import { useState, Suspense } from 'react'
import { MODULOS_GENERADOS, PAGINAS_GENERADAS } from './pages/generados/rutas'
import { authService } from './services/authService'
import './services/tema'                    // aplica el tema antes de dibujar
import SelectorTema from './components/generados/SelectorTema'
// BotonGoogle SÍ lo regenera davgen (es aditivo). Se dibuja solo si la BD
// tiene google_auth_activo=1 y un google_client_id — no hace falta
// condicionarlo acá. Ver components/generados/LEEME-GOOGLE.md.
import BotonGoogle from './components/generados/BotonGoogle'
// Privacidad y términos de uso: textos de [legal] en _configtotal.ini.
// Ver components/generados/LEEME-LEGAL.md (también trata la accesibilidad).
import AvisoLegal from './components/generados/AvisoLegal'

// Marco común de las pantallas sin sesión: centrado, con el selector de tema.
function Marco({ children }) {
  return (
    <main className="relative grid min-h-screen place-items-center bg-base-200 p-4 text-base-content">
      <div className="absolute right-3 top-3"><SelectorTema /></div>
      <div className="grid w-full justify-items-center gap-4">
        {children}
        <AvisoLegal className="opacity-70" conAceptacion />
      </div>
    </main>
  )
}

function Portal({ onLogin }) {
  return (
    <Marco>
      <div className="card w-full max-w-md bg-base-100 shadow-xl">
        <div className="card-body items-center text-center">
          <h1 className="card-title text-3xl">__NOMBRE__</h1>
          <p className="opacity-70">Sistema de gestión.<br />Accede con tu cuenta para continuar.</p>
          <div className="card-actions mt-4">
            <button className="btn btn-primary btn-wide" onClick={onLogin}>Iniciar sesión</button>
          </div>
        </div>
      </div>
    </Marco>
  )
}

function Login({ onAutenticado, onVolver }) {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [cargando, setCargando] = useState(false)

  async function entrar(e) {
    e.preventDefault(); setError(''); setCargando(true)
    try {
      const info = await authService.login(email, password)
      if (info?.requiere_2fa) {
        const codigo = window.prompt(`Código 2FA (método: ${info.metodo}):`) ?? ''
        const i2 = await authService.verificar(email, password, codigo)
        onAutenticado(i2?.user ?? null)
      } else {
        onAutenticado(info?.user ?? null)
      }
    } catch (err) { setError(err.message) }
    finally { setCargando(false) }
  }

  return (
    <Marco>
      <div className="card w-full max-w-sm bg-base-100 shadow-xl">
        <div className="card-body">
          <button className="btn btn-ghost btn-sm self-start px-1" onClick={onVolver}>← Volver</button>
          <h2 className="card-title text-2xl">Iniciar sesión</h2>
          <form onSubmit={entrar} className="mt-2 grid gap-3">
            <label className="grid gap-1">
              <span className="text-sm">Correo electrónico</span>
              <input type="email" required autoComplete="username" autoFocus
                className="input input-bordered w-full"
                value={email} onChange={e => setEmail(e.target.value)} />
            </label>
            <label className="grid gap-1">
              <span className="text-sm">Contraseña</span>
              <input type="password" required autoComplete="current-password"
                className="input input-bordered w-full"
                value={password} onChange={e => setPassword(e.target.value)} />
            </label>
            <button type="submit" className="btn btn-primary" disabled={cargando}>
              {cargando ? 'Ingresando…' : 'Entrar'}
            </button>
            {error && <p role="alert" className="text-sm text-error">{error}</p>}
          </form>

          {/* Google — no ocupa lugar si está apagado en la BD */}
          <div className="mt-3 grid justify-items-center gap-3">
            <BotonGoogle
              onAutenticado={(user) => onAutenticado(user)}
              onError={(msg) => setError(msg)}
            />
          </div>
        </div>
      </div>
    </Marco>
  )
}

// Menú lateral con módulos agrupados (desde MODULOS_GENERADOS de rutas.jsx)
function Menu({ seccion, onSeccion, usuario, onSalir }) {
  return (
    <aside className="flex min-h-full w-64 flex-col border-r border-base-300 bg-base-100 text-base-content">
      <div className="border-b border-base-300 p-4">
        <div className="truncate font-bold">__NOMBRE__</div>
        <div className="truncate text-xs opacity-60">{usuario?.nombre}</div>
      </div>

      <nav className="flex-1 overflow-y-auto p-2" aria-label="Módulos">
        {Object.entries(MODULOS_GENERADOS).map(([mod, info]) => (
          <ul key={mod} className="menu w-full p-0">
            <li className="menu-title">{info.etiqueta}</li>
            {info.secciones.map(s => (
              <li key={s.clave}>
                <button
                  className={s.clave === seccion ? 'menu-active active font-semibold' : ''}
                  aria-current={s.clave === seccion ? 'page' : undefined}
                  onClick={() => onSeccion(s.clave)}
                >
                  {s.etiqueta}
                </button>
              </li>
            ))}
          </ul>
        ))}
      </nav>

      <div className="grid gap-3 border-t border-base-300 p-3">
        <button className="btn btn-outline btn-error btn-sm w-full" onClick={onSalir}>
          Cerrar sesión
        </button>
        <AvisoLegal className="opacity-70" />
      </div>
    </aside>
  )
}

function tituloDe(clave) {
  for (const info of Object.values(MODULOS_GENERADOS)) {
    const s = info.secciones.find(x => x.clave === clave)
    if (s) return s.etiqueta
  }
  return '__NOMBRE__'
}

export default function App() {
  const primeraClave = Object.values(MODULOS_GENERADOS)[0]?.secciones[0]?.clave ?? ''
  const [vista, setVista]     = useState(authService.haySesion() ? 'app' : 'portal')
  const [usuario, setUsuario] = useState(authService.usuarioActual())
  const [seccion, setSeccion] = useState(primeraClave)
  const [menuAbierto, setMenuAbierto] = useState(false)   // solo importa en el celular

  function autenticado(user) { setUsuario(user); setVista('app') }
  function salir() { authService.logout().then(() => { setUsuario(null); setVista('portal') }) }
  function irA(clave) { setSeccion(clave); setMenuAbierto(false) }

  if (vista === 'portal') return <Portal onLogin={() => setVista('login')} />
  if (vista === 'login')  return <Login onAutenticado={autenticado} onVolver={() => setVista('portal')} />

  const Pagina = PAGINAS_GENERADAS[seccion]
  return (
    // Cajón: menú fijo en pantallas grandes, oculto tras ☰ en el celular
    <div className="drawer lg:drawer-open">
      {/* Con teclado: Tab llega primero a «Saltar al contenido» y a este
          interruptor del menú (Espacio lo abre y lo cierra en el celular). */}
      <a href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-base-100 focus:px-3 focus:py-2 focus:shadow">
        Saltar al contenido
      </a>
      <input id="menu-lateral" type="checkbox" className="drawer-toggle" aria-label="Menú"
        checked={menuAbierto} onChange={e => setMenuAbierto(e.target.checked)} />

      <div className="drawer-content flex min-h-screen min-w-0 flex-col bg-base-200 text-base-content">
        <header className="navbar sticky top-0 z-10 gap-2 bg-base-100 shadow-sm">
          <label htmlFor="menu-lateral" className="btn btn-square btn-ghost lg:hidden" aria-label="Abrir el menú">
            <span aria-hidden="true" className="text-xl">☰</span>
          </label>
          <span className="flex-1 truncate font-semibold">{tituloDe(seccion)}</span>
          <SelectorTema />
        </header>

        <main id="contenido" tabIndex={-1} className="min-w-0 flex-1 p-3 outline-none sm:p-6">
          <Suspense fallback={<p className="opacity-60">Cargando…</p>}>
            {Pagina ? <Pagina /> : <p className="opacity-60">Seleccionar una sección.</p>}
          </Suspense>
        </main>
      </div>

      <div className="drawer-side z-20">
        <label htmlFor="menu-lateral" className="drawer-overlay" aria-label="Cerrar el menú"></label>
        <Menu seccion={seccion} onSeccion={irA} usuario={usuario} onSalir={salir} />
      </div>
    </div>
  )
}

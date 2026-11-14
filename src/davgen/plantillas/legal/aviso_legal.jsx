// AvisoLegal — enlaces «Privacidad» y «Términos de uso» + la ventana que los
// muestra. Montar donde se quiera (pie del login, menú lateral):
//   import AvisoLegal from './components/generados/AvisoLegal'
//   <AvisoLegal />            (en el ingreso: <AvisoLegal conAceptacion />)
// Los textos salen de [legal] en _configtotal.ini. Son un punto de partida:
// revisarlos con quien responda legalmente por el sistema (LEEME-LEGAL.md).
import { useEffect, useRef, useState } from 'react'

const SISTEMA = '__NOMBRE__'
const RESPONSABLE = '__RESPONSABLE__'
const CONTACTO = '__CONTACTO__'
const JURISDICCION = '__JURISDICCION__'
const ALOJAMIENTO = '__ALOJAMIENTO__'
const VIGENTE_DESDE = '__VIGENTE_DESDE__'
const DIAS_BITACORA = __DIAS_BITACORA__
const CON_GOOGLE = __CON_GOOGLE__

function Privacidad() {
  return (
    <>
      <h4>Quién responde por tus datos</h4>
      <p>
        {RESPONSABLE
          ? <>El responsable de {SISTEMA} es <strong>{RESPONSABLE}</strong>.</>
          : <>El responsable de {SISTEMA} todavía no publicó sus datos.</>}
        {CONTACTO && <> Para cualquier consulta sobre tus datos: <strong>{CONTACTO}</strong>.</>}
      </p>

      <h4>Qué datos se guardan</h4>
      <ul>
        <li><strong>Tu cuenta:</strong> nombre, correo y rol. La contraseña se guarda transformada, de modo que nadie puede leerla.</li>
        <li><strong>Registro de actividad:</strong> fecha y hora, usuario, sección, operación y dirección IP de cada ingreso y de cada cambio.</li>
        <li><strong>Verificación en dos pasos:</strong> si la activas, los códigos que se te envían.</li>
        <li><strong>Lo que cargues:</strong> la información y los archivos que registres al usar el sistema.</li>
      </ul>

      <h4>Para qué se usan</h4>
      <p>
        Para darte acceso, proteger tu cuenta, saber quién hizo cada cambio y prestar
        el servicio. No se venden ni se usan para publicidad.
      </p>

      <h4>Por qué podemos usarlos</h4>
      <p>
        Porque son necesarios para darte el servicio y porque tú los entregas: al
        crear tu cuenta o ingresar aceptas que se usen como dice este texto.
        Puedes retirar esa aceptación pidiendo la baja de tu cuenta; lo que la ley
        obligue a conservar se guardará solo por ese motivo.
      </p>

      <h4>Con quién se comparten</h4>
      <ul>
        <li>Con los proveedores que hacen funcionar el sistema (alojamiento y envío de correos), solo para ese fin.</li>
        <li>Con una autoridad, cuando una ley o una orden válida lo exija.</li>
        <li>Con nadie más. No se venden ni se ceden.</li>
      </ul>

      <h4>Dónde se guardan</h4>
      <p>
        {ALOJAMIENTO
          ? <>En servidores de <strong>{ALOJAMIENTO}</strong>.</>
          : <>En los servidores del proveedor de alojamiento que contrata el responsable.</>}
        {' '}Esos servidores pueden estar en otro país.
      </p>

      <h4>Cómo se protegen</h4>
      <p>
        El acceso exige usuario y contraseña, cada persona ve solo lo que su rol
        permite y queda registro de cada cambio. Ningún sistema es totalmente
        seguro: si ocurre un incidente que afecte tus datos, el responsable te lo
        comunicará junto con las medidas tomadas.
      </p>

      <h4>Cuánto tiempo se conservan</h4>
      <ul>
        <li>
          <strong>Registro de actividad:</strong>{' '}
          {DIAS_BITACORA > 0
            ? <>{DIAS_BITACORA} días; después se borra solo.</>
            : <>sin plazo de borrado automático.</>}
        </li>
        <li><strong>Códigos de verificación y sesiones vencidas:</strong> se borran un día después de vencer.</li>
        <li><strong>Tu cuenta y lo que cargaste:</strong> mientras la cuenta esté activa, o el tiempo que exija la ley, hasta que el responsable lo elimine.</li>
      </ul>

      <h4>Qué se guarda en tu navegador</h4>
      <p>
        Este sistema <strong>no usa cookies</strong> ni herramientas de seguimiento. Guarda en
        el almacenamiento de tu navegador dos cosas que necesita para funcionar: tu
        sesión (se borra al cerrar sesión) y el tema claro u oscuro que elegiste.
      </p>

      {CON_GOOGLE && (
        <>
          <h4>Ingreso con Google</h4>
          <p>
            Si entras con tu cuenta de Google, Google nos confirma tu identidad y nos
            entrega tu nombre y tu correo. Ese servicio lo presta Google, con su propia
            política de privacidad y sus propias cookies.
          </p>
        </>
      )}

      <h4>Menores de edad</h4>
      <p>
        Si eres menor de edad, usa este sistema solo con autorización de tu madre,
        tu padre o tu tutor.
      </p>

      <h4>Tus derechos</h4>
      <p>
        Puedes pedir ver tus datos, corregirlos, que se eliminen u oponerte a un uso
        determinado
        {CONTACTO ? <> escribiendo a <strong>{CONTACTO}</strong>.</> : <> al responsable del sistema.</>}
        {' '}Se te responderá en un plazo razonable. Si no quedas conforme, puedes
        acudir a la autoridad competente.
      </p>

      <h4>Cambios</h4>
      <p>
        Este texto puede actualizarse; la versión vigente es la que se muestra aquí.
        {VIGENTE_DESDE && <> Vigente desde: {VIGENTE_DESDE}.</>}
      </p>
    </>
  )
}

function Terminos() {
  return (
    <>
      <h4>Aceptación</h4>
      <p>
        Al ingresar a {SISTEMA} aceptas estas condiciones y la política de
        privacidad. Si no estás de acuerdo, no uses el sistema.
      </p>

      <h4>Tu cuenta</h4>
      <ul>
        <li>La cuenta es personal. No compartas tu contraseña.</li>
        <li>Eres responsable de lo que se haga con tu cuenta. Si crees que alguien más la usó, avisa al responsable.</li>
      </ul>

      <h4>Uso permitido</h4>
      <ul>
        <li>Usa {SISTEMA} solo para las tareas para las que se te dio acceso.</li>
        <li>No intentes ver ni cambiar información que no te corresponde, ni afectar el funcionamiento del sistema.</li>
        <li>Carga solo información y archivos que tengas derecho a usar.</li>
      </ul>

      <h4>Lo que cargas</h4>
      <ul>
        <li>La información que registras sigue siendo tuya o de quien te la confió.</li>
        <li>Si cargas datos de otras personas, eres responsable de tener su autorización.</li>
      </ul>

      <h4>Disponibilidad</h4>
      <p>
        {SISTEMA} se ofrece tal como está. Se trabaja para que funcione bien, pero no
        se garantiza que esté disponible sin interrupciones ni libre de errores.
        Conserva por tu cuenta una copia de la información que no puedas perder.
      </p>

      <h4>Responsabilidad</h4>
      <p>
        Hasta donde la ley lo permita, el responsable no responde por daños
        indirectos, pérdida de información o de ingresos derivados del uso del
        sistema o de no poder usarlo. Esto no limita los derechos que la ley te
        reconoce y a los que no se puede renunciar.
      </p>

      <h4>Qué puede hacer el responsable</h4>
      <ul>
        <li>Suspender o cerrar una cuenta que incumpla estas condiciones.</li>
        <li>Interrumpir el servicio por mantenimiento o por causas que no dependan de él.</li>
        <li>Cambiar estas condiciones; la versión vigente es la que se muestra aquí.</li>
      </ul>

      {JURISDICCION && (
        <>
          <h4>Ley aplicable</h4>
          <p>Estas condiciones se rigen por las leyes de {JURISDICCION}.</p>
        </>
      )}

      {VIGENTE_DESDE && <p>Vigentes desde: {VIGENTE_DESDE}.</p>}
    </>
  )
}

const DOCUMENTOS = {
  privacidad: { titulo: 'Política de privacidad', Cuerpo: Privacidad },
  terminos: { titulo: 'Términos de uso', Cuerpo: Terminos },
}

// `conAceptacion`: agrega la frase «Al ingresar aceptas…» (para la pantalla de ingreso).
export default function AvisoLegal({ className = '', conAceptacion = false }) {
  const [abierto, setAbierto] = useState(null)        // null | 'privacidad' | 'terminos'
  const cerrar = useRef(null)
  const origen = useRef(null)                         // a dónde vuelve el foco

  useEffect(() => {
    if (abierto) cerrar.current?.focus()
    else origen.current?.focus()
  }, [abierto])

  function abrir(cual, e) {
    origen.current = e.currentTarget
    setAbierto(cual)
  }

  const doc = abierto ? DOCUMENTOS[abierto] : null
  return (
    <>
      {conAceptacion && (
        <p className={`text-center text-xs ${className}`}>
          Al ingresar aceptas los términos de uso y la política de privacidad.
        </p>
      )}
      <nav aria-label="Información legal" className={`flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs ${className}`}>
        <button type="button" className="link link-hover" onClick={(e) => abrir('privacidad', e)}>
          Privacidad
        </button>
        <button type="button" className="link link-hover" onClick={(e) => abrir('terminos', e)}>
          Términos de uso
        </button>
      </nav>

      {doc && (
        <div
          className="modal modal-open"
          role="dialog"
          aria-modal="true"
          aria-labelledby="aviso-legal-titulo"
          onKeyDown={(e) => { if (e.key === 'Escape') setAbierto(null) }}
        >
          <div className="modal-box max-w-2xl text-left">
            <h3 id="aviso-legal-titulo" className="mb-3 text-lg font-bold">{doc.titulo}</h3>
            <div className="max-h-[60vh] space-y-2 overflow-y-auto pr-1 text-sm [&_h4]:mt-4 [&_h4]:font-semibold [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5"
              tabIndex={0} role="region" aria-label={doc.titulo}>
              <doc.Cuerpo />
            </div>
            <div className="modal-action">
              <button ref={cerrar} type="button" className="btn btn-primary" onClick={() => setAbierto(null)}>
                Cerrar
              </button>
            </div>
          </div>
          <button type="button" className="modal-backdrop" aria-label="Cerrar" tabIndex={-1}
            onClick={() => setAbierto(null)} />
        </div>
      )}
    </>
  )
}

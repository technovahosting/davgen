# Privacidad, términos, conservación de datos y accesibilidad

davgen genera `AvisoLegal.jsx` (enlaces «Privacidad» y «Términos de uso» con sus
textos) y lo regenera en cada corrida. El `App.jsx` de un proyecto nuevo ya lo
muestra en la pantalla de ingreso y en el menú. En un proyecto anterior:

```jsx
import AvisoLegal from './components/generados/AvisoLegal'
// …en el pie del login y/o del menú:
<AvisoLegal />
```

## Qué completar — `[legal]` en `_configtotal.ini`

| Clave | Qué es |
|---|---|
| `responsable` | Persona o empresa que responde por los datos |
| `contacto` | Correo o teléfono para consultas y pedidos sobre los datos |
| `jurisdiccion` | País (o ciudad y país) cuya ley rige los términos |
| `alojamiento` | Dónde se guardan los datos: empresa de alojamiento y país |
| `vigente_desde` | Fecha desde la que rigen los textos |
| `retencion_bitacora_dias` | Días que se guarda el registro de actividad (`0` = no se borra) |

Después de cambiarlas: `davgen generar`.

**Los textos son un punto de partida, no asesoría legal.** Describen lo que el
sistema generado hace de verdad con los datos; lo que agregue tu negocio (datos
de clientes, salud, pagos, menores) hay que sumarlo, y conviene que los revise
quien responda legalmente. Para reescribirlos:
`davgen plantillas copiar legal/aviso_legal.jsx`.

## Quién responde por qué

| Quién | Responde por |
|---|---|
| **El responsable** (la persona o empresa de `[legal] responsable`: tu cliente, o tú) | Los datos que el sistema guarda, cumplir la ley de su país, atender los pedidos de las personas y avisar si hay un incidente |
| **Quien desarrolla el sistema** (tú) | Lo que construyes y entregas: que los textos digan la verdad sobre lo que hace el sistema, la seguridad del despliegue y lo que pactes con tu cliente |
| **davgen y sus autores** | Nada de lo anterior. davgen es una herramienta gratuita, sin garantía (licencia MIT): no opera tu sistema, no ve tus datos y no da asesoría legal |

Si desarrollas para un cliente, déjalo por escrito: quién es el responsable de
los datos, quién administra el hosting y las copias de respaldo, y qué pasa con
los datos cuando termina el contrato.

## Lista para el desarrollador antes de publicar

**Los textos**

- [ ] Completé `[legal]`: `responsable`, `contacto`, `jurisdiccion`,
      `alojamiento` y `vigente_desde`.
- [ ] Leí los dos textos enteros y **dicen la verdad** sobre este sistema. Si
      agregué algo que usa datos (un formulario público, pagos, correos
      masivos, analítica, un mapa), lo sumé al texto.
- [ ] Los revisó quien responde legalmente por el sistema.
- [ ] La pantalla de ingreso muestra «Al ingresar aceptas…»
      (`<AvisoLegal conAceptacion />`). Si la ley o el tipo de dato exige un
      consentimiento **expreso**, agregué una casilla sin marcar y guardo la
      fecha en que cada persona aceptó.

**Los datos**

- [ ] Sé qué datos personales guarda cada tabla y para qué. Lo que no hace
      falta, no se pide.
- [ ] Hay datos delicados (salud, menores, finanzas, creencias, biométricos):
      los acceden solo los roles que deben y lo revisó un profesional.
- [ ] Definí cuánto tiempo se guarda cada cosa y quién lo borra (el sistema
      solo borra la bitácora y los códigos vencidos).
- [ ] Hay un camino real para que una persona pida ver, corregir o borrar sus
      datos, y alguien que responde en `contacto`.

**La seguridad**

- [ ] El sitio usa `https://`.
- [ ] Cambié la contraseña inicial del administrador y cada persona tiene su
      propia cuenta (nada de cuentas compartidas).
- [ ] Activé la verificación en dos pasos para los administradores.
- [ ] Los archivos `_acceso.*.ini` no están en git ni en una carpeta compartida.
- [ ] Hay copias de respaldo de la base, alguien probó restaurar una y están
      guardadas fuera del servidor.
- [ ] Sé a quién avisar y qué hacer si se filtran datos.

## Normas a consultar (Bolivia)

Esto es orientación, **no asesoría legal**, y las normas cambian: verifícalo con
un abogado antes de publicar.

- Bolivia **no tiene todavía una ley general de protección de datos
  personales**; hay proyectos en trámite. Conviene diseñar ya con sus
  principios: pedir solo lo necesario, decir para qué, pedir permiso y dejar
  que la persona vea, corrija y borre lo suyo.
- **Constitución Política del Estado**: derecho a la privacidad e intimidad
  (art. 21) y Acción de Protección de Privacidad (arts. 130 y 131), que
  permite a una persona exigir conocer, corregir o eliminar sus datos.
- **Ley 164** de Telecomunicaciones y TIC y su reglamento, **Decreto Supremo
  1793**: tratamiento de datos personales con consentimiento previo y expreso
  del titular, y para la finalidad informada.
- **Normas del sector**, que pesan más que las generales: salud (expediente
  clínico), financiero (ASFI), educación, entidades públicas.

Si el sistema tiene usuarios en otros países rigen también sus leyes (por
ejemplo, el RGPD si hay personas en la Unión Europea).

## Cuánto tiempo se guardan los datos

| Dato | Plazo | Quién lo borra |
|---|---|---|
| Registro de actividad (`tbl_seg_bitacora`) | `retencion_bitacora_dias` (365 por defecto) | El sistema, solo |
| Códigos de verificación y enlaces de recuperación | 1 día después de vencer | El sistema, solo |
| Sesiones vencidas (`personal_access_tokens`) | 1 día después de vencer | El sistema, solo |
| Cuentas, archivos y datos del negocio | Lo que decida el responsable | El responsable (no hay borrado automático) |

El borrado automático lo hace `app/Utils/Retencion.php` aprovechando algunos
inicios de sesión (no hace falta programar una tarea en el hosting). El plazo
vigente es el de `tbl_seg_parametro.retencion_bitacora_dias`: si se cambia ahí,
cambiar también el `.ini` y regenerar para que el texto de privacidad coincida.

## ¿Y el aviso de cookies?

**No corresponde, y por eso davgen no lo genera.** El aviso se exige cuando un
sitio guarda cookies o rastreadores que no son necesarios (analítica,
publicidad, redes sociales). El sistema generado no usa ninguna cookie: la
sesión va en el almacenamiento local del navegador y es imprescindible para
funcionar, y no carga recursos de terceros. Eso mismo dice el texto de
privacidad. Un aviso que pide permiso para algo que no existe solo estorba.

Hay que **agregarlo** si después se incorpora analítica, un píxel de publicidad,
mapas o videos incrustados, o un chat de terceros. Con el ingreso con Google
activado, es Google quien usa sus cookies en su propia ventana; el texto de
privacidad lo menciona.

## Accesibilidad (teclado y lectores de pantalla)

Las pantallas generadas se pueden usar sin ratón y anuncian lo que hacen:

- cada campo tiene su etiqueta, y los botones sin texto («, », ☰) tienen nombre;
- las ventanas se cierran con **Esc**, llevan el foco adentro al abrirse y lo
  devuelven al cerrarse;
- los avisos y errores se anuncian (`role="status"` / `role="alert"`);
- hay un enlace «Saltar al contenido» al tabular, y la página declara su idioma.

Para el código propio, las mismas reglas:

- toda `<img>` lleva `alt` con lo que muestra; si es decorativa, `alt=""`;
- todo lo que se pueda pulsar es un `<button>` o un `<a>`, no un `<div>` con `onClick`;
- todo campo tiene `<label>` (o `aria-label`);
- no usar el color como única señal (acompañar con texto o icono).

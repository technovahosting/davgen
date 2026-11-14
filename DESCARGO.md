# Descargo de responsabilidad y privacidad

Este documento explica, en palabras simples, qué es davgen, qué **no** es, y
quién responde por qué. No reemplaza a la [licencia](LICENSE): la acompaña.

## 1 · davgen se entrega sin garantía

davgen es software libre y gratuito bajo la licencia MIT. Se entrega **«tal como
está», sin garantía de ningún tipo**: ni de que funcione sin errores, ni de que
sirva para un fin determinado, ni de que el código que genera sea seguro o
cumpla alguna norma. Sus autores y colaboradores **no responden por daños**
—pérdida de datos, de dinero, de tiempo, sanciones o reclamos de terceros— que
resulten de usar davgen o lo que davgen genera. Usarlo es decisión y
responsabilidad de quien lo usa.

No hay obligación de dar soporte, corregir fallos ni publicar actualizaciones.

## 2 · El sistema generado es tuyo, y tu responsabilidad

El código que davgen escribe en tu proyecto te pertenece sin condiciones. Con
eso viene la responsabilidad completa sobre él:

- **Revisarlo y probarlo** antes de usarlo con datos reales. Código generado no
  es código auditado.
- **Su seguridad**: el servidor, el `https`, las contraseñas, las copias de
  respaldo, las actualizaciones de Laravel, React y sus dependencias.
- **Los datos** que guarde y **cumplir las leyes** del lugar donde opere:
  protección de datos, consumo, facturación, salud, educación o las que
  correspondan.
- **Lo que le agregues**: davgen solo conoce lo que generó.

davgen incluye medidas de seguridad razonables y documenta las pruebas hechas
([docs/seguridad.md](docs/seguridad.md)), pero eso **no es una certificación**.

## 3 · Los textos legales son plantillas, no asesoría

El sistema generado trae una política de privacidad y unos términos de uso de
partida. Describen lo que hace el sistema recién generado; **no son asesoría
legal ni garantizan el cumplimiento de ninguna ley**. Hay que completarlos,
ajustarlos a lo que tu sistema hace de verdad y hacerlos revisar por un
profesional del derecho de tu país. Lo mismo vale para cualquier mención a
normas en la documentación: es orientación general y puede estar desactualizada.

## 4 · Usos que requieren un cuidado especial

No uses un sistema generado, sin revisión profesional independiente, para:

- datos de salud, de menores de edad, biométricos o financieros;
- decisiones que afecten derechos de las personas;
- servicios donde una falla ponga en riesgo la vida, la salud o el patrimonio.

En esos casos la ley suele exigir más de lo que cualquier generador puede dar.

## 5 · Qué datos recoge davgen: ninguno

- davgen **no tiene telemetría, cuentas ni servidores**. No envía tu código,
  tu configuración ni tus datos a sus autores ni a nadie.
- Solo se conecta a lo que tú configuras: tu base de datos y tu FTP.
- Para crear el proyecto ejecuta `composer` y `npm`, que descargan paquetes de
  sus propios repositorios, con sus propias políticas.
- Tus contraseñas se quedan en tu equipo, en archivos que el proyecto excluye
  de git. **Tú** respondes por cuidarlos y por no publicarlos.
- davgen **no trae ninguna contraseña de fábrica**: la del administrador la
  eliges tú. Elegir una débil o reutilizada es tu riesgo.

## 6 · Si lo usas con un asistente de inteligencia artificial

La skill `crear-sistema` permite usar davgen conversando con Claude.

- Lo que escribes en la conversación lo procesa el proveedor del asistente
  (Anthropic, en el caso de Claude), según **sus** términos y su política de
  privacidad. davgen no interviene en eso ni recibe nada.
- **No pegues en el chat contraseñas ni datos personales reales.** La skill
  está escrita para no pedirlos.
- Un asistente puede equivocarse. Lo que propone o ejecuta lo decides y lo
  revisas tú.

## 7 · Si lo usas para estudiar

davgen sirve para aprender cómo se arma un sistema completo. Si presentas un
trabajo hecho con él, **di qué generó la herramienta y qué escribiste tú**, y
respeta las reglas de tu institución sobre el uso de generadores y de
inteligencia artificial. Eso lo decide tu docente, no davgen.

## 8 · Marcas y proyectos de terceros

davgen es un proyecto independiente. No está afiliado ni respaldado por
Laravel, React, MySQL, Google, Anthropic ni ningún otro proyecto o empresa
mencionados. Sus nombres se usan solo para describir con qué funciona. Las
licencias de lo que davgen usa o genera están en
[AVISOS-TERCEROS.md](AVISOS-TERCEROS.md).

## 9 · Fallos de seguridad

Si encuentras una vulnerabilidad en davgen o en el código que genera, repórtala
en privado como indica [SECURITY.md](SECURITY.md). Se atiende con la mejor
voluntad, sin plazos comprometidos.

---

*Este documento es un resumen en lenguaje llano. Si algo aquí contradice la
[licencia MIT](LICENSE), vale la licencia. No es asesoría legal.*

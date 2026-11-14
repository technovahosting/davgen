# Accesos cifrados

Los accesos de cada entorno (base de datos, FTP, contraseña inicial del admin)
se pueden guardar **cifrados dentro del proyecto**. Se abren con un **token**
que eliges tú, uno por proyecto, y que davgen pide al ejecutar.

```text
_acceso.desarrollo.cifrado     ← ilegible sin el token; se puede versionar
_acceso.produccion.cifrado
_acceso.*.ini                  ← dejan de existir en disco
```

## Cifrar

```bash
davgen acceso cifrar
```

1. Pide el token dos veces (mínimo 12 caracteres; conviene una frase).
2. Cifra los dos archivos, comprueba que se pueden volver a abrir y recién
   entonces borra los `.ini`.
3. Muestra **una sola vez** la **llave maestra** de recuperación. Guárdala
   fuera de la PC (papel, gestor de contraseñas). davgen no la conserva.

A partir de ahí todo funciona igual, con un paso más: la primera vez que un
comando necesita los accesos, pide el token (sin mostrarlo en pantalla).

```bash
davgen acceso                 # estado: qué está cifrado y si tiene llave maestra
davgen acceso ver             # muestra los accesos (pide el token)
davgen acceso descifrar       # vuelve a los .ini para editarlos; luego `cifrar`
davgen acceso cambiar-token   # token nuevo (pide el actual)
```

Para tareas automáticas (tarea programada, CI) el token va en la variable de
entorno `DAVGEN_TOKEN`.

## Si se pierde el token

**Camino 1 — con la llave maestra.** No se pierde nada:

```bash
davgen acceso cambiar-token --con-llave-maestra
```

Pide la llave maestra y un token nuevo. Los accesos quedan como estaban; solo
cambia el token que los abre.

**Camino 2 — sin llave maestra.** Los accesos cifrados no se pueden recuperar:

```bash
davgen acceso reiniciar                      # o --entorno produccion
```

Deja `_acceso.<entorno>.ini` vacío para volver a cargar los datos de la base y
del FTP desde el panel del hosting, y después `davgen acceso cifrar`. El archivo
cifrado anterior no se destruye: queda como `.cifrado.perdido-<fecha>`, por si
el token aparece. El sistema publicado no se ve afectado: sus contraseñas
siguen siendo las mismas, lo único perdido era tu copia.

## Cómo está cifrado

Solo construcciones estándar (librería `cryptography`):

| Pieza | Elección |
|---|---|
| Contenido | AES-256-GCM con una clave de datos aleatoria de 32 bytes |
| De token a clave | scrypt (n = 2¹⁵, r = 8, p = 1) con sal aleatoria de 16 bytes |
| Token y llave maestra | Dos «cerraduras» sobre la misma clave de datos |
| Llave maestra | 160 bits al azar, en 8 grupos de 4 caracteres |

Cambiar el token no vuelve a cifrar el contenido: rehace su cerradura. Por eso
la llave maestra puede autorizar un token nuevo sin conocer el anterior.
Un token incorrecto y un archivo alterado dan el mismo error, y un archivo de
desarrollo no puede hacerse pasar por el de producción.

## Qué protege y qué no

**Protege**

- El archivo se puede versionar, respaldar y sincronizar sin exponer nada.
- Quien lea la carpeta o el repositorio no obtiene las contraseñas.
- Un programa o asistente que lea los archivos del proyecto tampoco.

**No protege**

- **Lo que ya se filtró antes de cifrar.** Si una contraseña estuvo en un
  repositorio o en una conversación, hay que rotarla una vez. El cifrado evita
  que vuelva a pasar.
- **Un token débil.** Toda la seguridad es la del token.
- **El `.env` de Laravel**, que necesita la contraseña de la base en claro (en
  tu PC y en el servidor). Sigue fuera de git.
- **Lo que se muestra en pantalla.** `davgen acceso ver` imprime los accesos;
  `davgen seguridad` y `generar` muestran la contraseña inicial del admin.
- **El borrado del `.ini`.** Se borra normalmente: el disco puede conservar
  restos recuperables con herramientas forenses.
- **El FTP**, que viaja sin cifrar por la red.
- **Un token y un repositorio filtrados juntos**: ahí sí toca rotar todo y
  cambiar el token.

## Detalles

- **Un token por proyecto**: los dos entornos se cifran con el mismo. Cifrar un
  entorno nuevo con un token distinto del que abre el otro se rechaza.
- **Llave maestra al volver a cifrar**: `descifrar` + `cifrar` genera una llave
  nueva y la anterior deja de servir. Para conservar la misma, pasarla en la
  variable `DAVGEN_LLAVE_MAESTRA` al cifrar.
- **Sin llave maestra**: `davgen acceso cifrar --sin-llave-maestra`. Entonces el
  único camino ante un token perdido es reiniciar.
- **Secretos nuevos**: cuando davgen tiene que guardar uno (la contraseña del
  admin en `davgen seguridad`), lo escribe dentro del archivo cifrado y conserva
  la llave maestra.
- Los `.ejemplo.ini` (sin contraseñas) se siguen escribiendo para documentar qué
  claves existen.

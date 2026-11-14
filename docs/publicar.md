# Publicar davgen

Lista de control para abrir el repositorio y para sacar cada versión. Está
escrita para hacerse despacio: publicar no se deshace.

## A · Antes de hacer público el repositorio (una sola vez)

- [x] **Repositorio nuevo, sin historial anterior.** Este repositorio nace
      limpio, con un único commit inicial. El de la v4 **no se hace público
      ni se importa su historial aquí**.
- [ ] **Rotar las credenciales que vivieron en el repositorio de la v4** (BD y
      FTP del entorno de pruebas, y cualquier otra que haya pasado por un
      `_configtotal.ini` versionado). Aunque ese repositorio siga privado.
- [ ] **Decidir la licencia.** Está puesta MIT (la misma de Laravel y React, la
      de mayor adopción). Cambiarla después de publicar es difícil: si se
      prefiere Apache-2.0, AGPL o un modelo comercial, decidirlo ahora
      (`LICENSE`, `pyproject.toml`, `README.md`).
- [ ] **Confirmar el nombre.** Comprobar que `davgen` está libre en
      <https://pypi.org/project/davgen/>. Si no lo está, cambiar `name` en
      `pyproject.toml` (el comando puede seguir llamándose `davgen`).
- [ ] **Datos de contacto.** `SECURITY.md` pide usar los avisos privados de
      GitHub; activarlos en Settings → Security. Decidir si `authors` de
      `pyproject.toml` lleva un correo público.
- [ ] Revisar a ojo `git ls-files` antes del primer `push`: nada de `.ini` con
      datos, `.exe`, `.zip` ni carpetas de proyectos de clientes.
- [ ] Ejecutar `scripts/probar.ps1 -Paquete` y dejar el CI en verde.

## B · Cada versión

1. Subir `VERSION` en `src/davgen/nucleo/version.py` (semver: si cambia una
   ruta, la firma de un SP o el nombre de un archivo generado, es MAYOR) y el
   mismo número en `.claude-plugin/plugin.json`.
2. Anotar los cambios en `CHANGELOG.md`.
3. `scripts/probar.ps1 -Paquete` en verde.
4. Commit, etiqueta `vX.Y.Z` y push.
5. Crear el *Release* en GitHub con esa etiqueta. El workflow `publicar.yml`
   comprueba que la etiqueta coincide con `VERSION`, corre las pruebas y
   publica en PyPI (requiere haber configurado *Trusted Publishing*; los pasos
   están en la cabecera de ese workflow).
6. `python scripts/empaquetar_skill.py` y adjuntar `dist/crear-sistema.zip` al
   Release: es la descarga directa de la skill ([skill.md](skill.md)). **El
   `.zip` no se versiona.**
7. Opcional: `scripts/compilar-exe.ps1` y adjuntar `dist/davgen-X.Y.Z.exe` al
   Release junto con `LICENSE` y `AVISOS-TERCEROS.md`. **El `.exe` no se
   versiona.**

## C · Qué se revisó para no infringir condiciones de terceros

El detalle está en [AVISOS-TERCEROS.md](../AVISOS-TERCEROS.md). En resumen:

| Riesgo | Qué se hizo |
|---|---|
| Redistribuir `vendor/` y `node_modules/` (cientos de licencias) | Se eliminó el bundle; cada usuario descarga con `composer`/`npm` |
| Controlador MySQL con licencia GPL dentro del ejecutable | El predeterminado es PyMySQL (MIT) |
| Client ID de OAuth de una organización usado por terceros | No hay ninguno por defecto; Google viene apagado |
| Cuenta «dueña» sembrada como administrador en todo sistema generado | No hay ninguna por defecto |
| Contraseña de administrador fija y pública | Aleatoria por proyecto |
| Marca del botón de Google | Se usa el botón oficial, sin modificar |
| Uso de marcas (Laravel, React…) | Solo descriptivo; aviso de no afiliación; no van en el nombre del producto |
| Licencia del propio davgen y del código generado | MIT; el código generado es del usuario |
| Mecanismo que inutilizaba el programa en el equipo del usuario | Eliminado |

Esto es una revisión técnica hecha con cuidado, **no un dictamen legal**. Antes
de un lanzamiento comercial conviene que la vea un abogado, sobre todo si se
elige un modelo distinto de MIT.

## D · Pendiente para una publicación madura

- Sitio de documentación y un proyecto de demostración público.
- Mensajes y documentación en inglés.
- `CODE_OF_CONDUCT.md` y plantillas de *issues* cuando haya colaboradores.

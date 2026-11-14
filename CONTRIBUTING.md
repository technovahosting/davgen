# Contribuir a davgen

## Preparar el entorno

```powershell
.\scripts\probar.ps1          # Windows
```
```bash
scripts/probar.sh             # Linux / macOS
```

El script crea un entorno virtual en `.tmp/venv`, instala davgen en modo
editable con las herramientas de desarrollo, pasa el linter y corre las
pruebas. No necesita MySQL, FTP, Composer ni Node.

A mano:

```bash
python -m venv .tmp/venv && . .tmp/venv/bin/activate    # Windows: .tmp\venv\Scripts\activate
pip install -e ".[dev]"
pytest                     # todas
pytest -k plantillas       # un grupo
ruff check src tests scripts
python scripts/generar_ejemplo.py --extras   # deja el ejemplo en .tmp/ejemplo
```

Si hay un PHP instalado, las pruebas validan además la sintaxis del PHP
generado (`DAVGEN_PHP=/ruta/a/php` para elegir uno).

## Reglas del proyecto

1. **Toda corrección trae su prueba.** Si arreglas algo que falló en un
   proyecto real, la prueba debe fallar sin el arreglo.
2. **Nada sale del proyecto sin que el usuario lo pida.** Cualquier código que
   escriba en una base de datos, en un FTP o instale algo debe respetar
   `--local` y, en modo interactivo, confirmarse mostrando el destino.
3. **Nunca borrar lo que davgen no generó.** Lo generado lleva la cabecera
   `@generated davgen`; lo demás es del usuario.
4. **Valores por defecto neutros.** Ninguna cuenta, correo, dominio,
   identificador ni contraseña fija en el código, las plantillas o los
   ejemplos. Hay una prueba que lo vigila.
5. **Sin secretos en el repositorio.** `_configtotal.ini` está en `.gitignore`.
6. **Las plantillas son datos** (`src/davgen/plantillas/`), con finales de
   línea LF. No vuelvas a incrustar PHP/JSX/SQL largos en Python.
7. **La base de datos se usa a través de `nucleo/bd.py`** y la fecha a través
   de `nucleo/reloj.py`: es lo que permite probar sin servicios y que la salida
   sea reproducible.
8. **Versionado semántico.** `VERSION` vive solo en
   `src/davgen/nucleo/version.py`. Cambiar una ruta de la API, la firma de un SP
   o el nombre/ubicación de un archivo generado es un cambio MAYOR. Todo cambio
   visible se anota en `CHANGELOG.md`.
9. Mensajes de consola y código generado en español.

## Antes de abrir un pull request

- `scripts/probar.ps1` (o `.sh`) en verde.
- Si cambiaste una plantilla o un generador: genera el ejemplo antes y después
  (`python scripts/generar_ejemplo.py .tmp/antes --extras`) y revisa el
  `diff -r` — en la descripción del PR cuenta qué archivos generados cambian y
  por qué.
- No incluyas archivos de `.tmp/`, `dist/`, `.exe` ni `.zip`.

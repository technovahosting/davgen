"""version.py — versión ÚNICA del generador davgen (fuente de verdad).

`pyproject.toml` lee VERSION de aquí (versión dinámica): no se duplica el
número en ningún otro archivo. El historial de cambios vive en CHANGELOG.md.

Versionado semántico (https://semver.org/lang/es/):
  · MAYOR — cambia el contrato de lo generado (rutas de la API, firma de los
            SPs, estructura de carpetas) o el de las plantillas.
  · MENOR — funcionalidad nueva compatible.
  · PARCHE — correcciones.
"""

VERSION = '5.1.0'

# Autor del generador (aparece en el pie de las guías que davgen escribe).
# El `@author` del CÓDIGO generado es otro dato: sale de [proyecto] autor del
# _configtotal.ini de cada proyecto y, si está vacío, simplemente no se escribe.
AUTOR = 'David Serrudo'

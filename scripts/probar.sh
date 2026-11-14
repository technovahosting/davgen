#!/usr/bin/env bash
# probar.sh — todo lo que corre el CI, en local (Linux / macOS / Git Bash).
#
#   scripts/probar.sh              pruebas + linter
#   scripts/probar.sh --ejemplo    además genera el proyecto de ejemplo en .tmp/ejemplo
#
# No necesita MySQL, FTP, composer ni node. Usa un entorno virtual propio en
# .tmp/venv: no toca el Python del sistema.
set -u
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python
VENV=.tmp/venv
if [ -x "$VENV/bin/python" ]; then PY="$VENV/bin/python"
elif [ -x "$VENV/Scripts/python.exe" ]; then PY="$VENV/Scripts/python.exe"
else
  echo "→ Creando el entorno virtual en $VENV…"
  "$PYTHON" -m venv "$VENV" || { echo "✗ No se pudo crear el entorno"; exit 1; }
  if [ -x "$VENV/bin/python" ]; then PY="$VENV/bin/python"; else PY="$VENV/Scripts/python.exe"; fi
fi
"$PY" -m pip install --quiet --disable-pip-version-check -e '.[dev]' || exit 1

fallas=0
echo; echo "── Linter (ruff) ──"
"$PY" -m ruff check src tests scripts || fallas=$((fallas + 1))
echo; echo "── Pruebas (pytest) ──"
"$PY" -m pytest || fallas=$((fallas + 1))
if [ "${1:-}" = "--ejemplo" ]; then
  echo; echo "── Proyecto de ejemplo ──"
  "$PY" scripts/generar_ejemplo.py --extras || fallas=$((fallas + 1))
fi

echo
if [ "$fallas" -eq 0 ]; then echo "✓ Todo en orden."; exit 0; fi
echo "✗ $fallas paso(s) fallaron."; exit 1

# probar.ps1 — todo lo que corre el CI, en local (Windows / PowerShell).
#
#   .\scripts\probar.ps1              pruebas + linter
#   .\scripts\probar.ps1 -Ejemplo     además genera el proyecto de ejemplo en .tmp\ejemplo
#   .\scripts\probar.ps1 -Paquete     además construye el wheel y lo prueba instalado
#
# No necesita MySQL, FTP, composer ni node. Si hay un PHP instalado se valida
# también la sintaxis del PHP generado (variable DAVGEN_PHP para elegir cuál).
# Usa un entorno virtual propio en .tmp\venv: no toca el Python del equipo.
param([switch]$Ejemplo, [switch]$Paquete)

$ErrorActionPreference = 'Continue'   # pip/pytest escriben en stderr sin fallar
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$venv = Join-Path $raiz '.tmp\venv'
$py = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host '→ Creando el entorno virtual en .tmp\venv…' -ForegroundColor Cyan
    python -m venv $venv
    if (-not (Test-Path $py)) { Write-Host '✗ No se pudo crear el entorno (¿Python 3.10+ instalado?)' -ForegroundColor Red; exit 1 }
}
& $py -m pip install --quiet --disable-pip-version-check -e '.[dev]'
if ($LASTEXITCODE -ne 0) { Write-Host '✗ Falló la instalación de dependencias' -ForegroundColor Red; exit 1 }

# PHP >= 8.2 de Laragon/XAMPP si el del PATH no sirve (solo para `php -l`)
if (-not $env:DAVGEN_PHP) {
    $candidatos = @(Get-ChildItem 'C:\laragon\bin\php\php-8.*\php.exe' -ErrorAction SilentlyContinue |
                    Sort-Object FullName -Descending)
    if ($candidatos.Count -gt 0) { $env:DAVGEN_PHP = $candidatos[0].FullName }
}

$fallas = 0
Write-Host "`n── Linter (ruff) ──────────────────────────────" -ForegroundColor White
& $py -m ruff check src tests scripts
if ($LASTEXITCODE -ne 0) { $fallas++ }

Write-Host "`n── Pruebas (pytest) ───────────────────────────" -ForegroundColor White
& $py -m pytest
if ($LASTEXITCODE -ne 0) { $fallas++ }

if ($Ejemplo) {
    Write-Host "`n── Proyecto de ejemplo ────────────────────────" -ForegroundColor White
    & $py scripts\generar_ejemplo.py --extras
    if ($LASTEXITCODE -ne 0) { $fallas++ }
}

if ($Paquete) {
    Write-Host "`n── Paquete (wheel) ────────────────────────────" -ForegroundColor White
    $dist = Join-Path $raiz '.tmp\dist'
    if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }
    & $py -m build --wheel --outdir $dist .
    if ($LASTEXITCODE -ne 0) { $fallas++ }
    else {
        # instalado en un entorno LIMPIO: comprueba que las plantillas viajan en el paquete
        $limpio = Join-Path $raiz '.tmp\venv-paquete'
        if (Test-Path $limpio) { Remove-Item -Recurse -Force $limpio }
        python -m venv $limpio
        $pyl = Join-Path $limpio 'Scripts\python.exe'
        & $pyl -m pip install --quiet --disable-pip-version-check (Get-ChildItem "$dist\*.whl").FullName
        $prueba = Join-Path $raiz '.tmp\prueba-paquete'
        if (Test-Path $prueba) { Remove-Item -Recurse -Force $prueba }
        New-Item -ItemType Directory -Force $prueba | Out-Null
        Push-Location $prueba
        & (Join-Path $limpio 'Scripts\davgen.exe') nuevo
        if ($LASTEXITCODE -ne 0) { $fallas++ }
        Pop-Location
    }
}

Write-Host ''
if ($fallas -eq 0) { Write-Host '✓ Todo en orden.' -ForegroundColor Green; exit 0 }
Write-Host "✗ $fallas paso(s) fallaron." -ForegroundColor Red
exit 1

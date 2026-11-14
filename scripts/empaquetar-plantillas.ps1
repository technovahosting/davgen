# empaquetar-plantillas.ps1 — OPCIONAL: caché local de un proyecto Laravel base.
#
# davgen crea el proyecto Laravel de cada sistema con `composer create-project`
# (necesita red y tarda unos minutos). Este script hace esa descarga UNA vez y
# la guarda en  %USERPROFILE%\.davgen\_laravel.zip ; a partir de ahí davgen
# extrae el zip en segundos y sin red.
#
# El zip contiene vendor\ (paquetes de terceros, cada uno con su licencia): es
# para USO PROPIO en este equipo. No lo publiques ni lo subas a un repositorio;
# ver AVISOS-TERCEROS.md.
#
# Requiere composer y PHP >= 8.2 en el PATH (o -Php con la ruta a php.exe).
param([string]$Php = '')

$ErrorActionPreference = 'Continue'
$cache = Join-Path $env:USERPROFILE '.davgen'
$trabajo = Join-Path $env:TEMP "davgen-laravel-$(Get-Random)"
New-Item -ItemType Directory -Force $cache, $trabajo | Out-Null

if ($Php) { $env:PATH = "$(Split-Path $Php);$env:PATH" }
$v = (php -r "echo PHP_MAJOR_VERSION.'.'.PHP_MINOR_VERSION;")
if ([version]$v -lt [version]'8.2') {
    Write-Host "✗ PHP $v es insuficiente (Laravel requiere 8.2+). Usar -Php <ruta a php.exe>" -ForegroundColor Red
    exit 1
}

Push-Location $trabajo
Write-Host "→ composer create-project laravel/laravel (PHP $v)…" -ForegroundColor Cyan
composer create-project laravel/laravel base --no-interaction --quiet
if (-not (Test-Path 'base\artisan')) { Pop-Location; Write-Host '✗ composer falló' -ForegroundColor Red; exit 1 }
Set-Location base
Write-Host '→ php artisan install:api (Sanctum)…' -ForegroundColor Cyan
php artisan install:api --no-interaction | Out-Null
# el .env y la BD sqlite de muestra no viajan: davgen escribe el .env del proyecto
Remove-Item -Force -ErrorAction SilentlyContinue .env, database\database.sqlite
$zip = Join-Path $cache '_laravel.zip'
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path (Get-ChildItem -Force | Select-Object -ExpandProperty FullName) -DestinationPath $zip
Pop-Location
Remove-Item -Recurse -Force $trabajo -ErrorAction SilentlyContinue

Write-Host "✓ $zip ($([math]::Round((Get-Item $zip).Length / 1MB, 1)) MB) — solo para uso en este equipo." -ForegroundColor Green

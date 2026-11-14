# compilar-exe.ps1 — ejecutable de Windows OPCIONAL (dist\davgen-<version>.exe).
#
# La forma normal de instalar davgen es `pip install davgen`. El .exe es para
# equipos sin Python. Va a GitHub Releases, NUNCA al repositorio (está en
# .gitignore). Al distribuirlo, acompañarlo de LICENSE y AVISOS-TERCEROS.md.
#
# Requiere:  pip install pyinstaller bcrypt pymysql cryptography
$ErrorActionPreference = 'Continue'   # pyinstaller escribe su log en stderr
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$version = (python -c "import sys; sys.path.insert(0, 'src'); from davgen.nucleo.version import VERSION; print(VERSION)").Trim()
if (-not $version) { Write-Host '✗ No se pudo leer la versión' -ForegroundColor Red; exit 1 }
$nombre = "davgen-$version"
Write-Host "→ Compilando $nombre.exe…" -ForegroundColor Cyan

$entrada = Join-Path $raiz '.tmp\entrada_exe.py'
New-Item -ItemType Directory -Force (Split-Path $entrada) | Out-Null
Set-Content -Path $entrada -Encoding utf8 -Value "from davgen.cli import ejecutar`nejecutar()"

python -m PyInstaller --noconfirm --clean --onefile --console `
    --name $nombre `
    --paths (Join-Path $raiz 'src') `
    --add-data "$raiz\src\davgen\plantillas;davgen\plantillas" `
    --collect-submodules pymysql `
    --hidden-import bcrypt `
    --collect-submodules cryptography `
    --specpath .tmp --workpath .tmp\build --distpath dist `
    $entrada | Out-Null

$exe = Join-Path $raiz "dist\$nombre.exe"
if (-not (Test-Path $exe)) { Write-Host '✗ No se generó el ejecutable' -ForegroundColor Red; exit 1 }
$salida = & $exe --version
Write-Host "✓ $exe  ($([math]::Round((Get-Item $exe).Length / 1MB, 1)) MB) — $salida" -ForegroundColor Green

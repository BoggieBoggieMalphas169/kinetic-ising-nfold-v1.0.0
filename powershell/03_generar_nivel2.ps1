# Crea figuras nuevas del Nivel 2 sin tocar los archivos historicos.
[CmdletBinding()]
param([string]$Python = '',
      [ValidateSet('all','distribuciones','rendimiento')][string]$Solo = 'all')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    & $exe -m scripts.practica_cierre.nivel2 --solo $Solo
    if ($LASTEXITCODE -ne 0) {
        throw "Nivel 2 fallo (codigo $LASTEXITCODE). Revisa results/practica_cierre/<id>_nivel2/RESUMEN.md"
    }
} finally {
    Pop-Location
}

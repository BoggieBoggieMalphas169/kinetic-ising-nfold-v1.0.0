# Bloque 7: reanalizar muestras ya generadas SIN resimular ni sobrescribir.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$DirectorioB7, [string]$Python = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    & $exe -m scripts.practica_cierre.inconclusos_b7 analizar --directorio $DirectorioB7
    if ($LASTEXITCODE -ne 0) { throw "Reanalisis de B7 fallo (exit $LASTEXITCODE)" }
}
finally { Pop-Location }

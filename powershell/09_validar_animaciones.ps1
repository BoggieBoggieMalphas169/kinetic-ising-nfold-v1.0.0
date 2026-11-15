# Bloque 5: comprueba hashes, integridad B3 y tiempos/espines de cada video.
[CmdletBinding()]
param([string]$Python = '', [string]$Directorio = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    $paramsB5 = @('-m','scripts.practica_cierre.animaciones_b5','validar')
    if (-not [string]::IsNullOrWhiteSpace($Directorio)) { $paramsB5 += @('--directorio',$Directorio) }
    & $exe @paramsB5
    if ($LASTEXITCODE -ne 0) { throw "B5: la validacion ha fallado ($LASTEXITCODE)" }
} finally { Pop-Location }

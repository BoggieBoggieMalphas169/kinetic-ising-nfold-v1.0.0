# Bloque 4: verifica integridad de nuevas figuras y reconstruye el origen fisico B3.
[CmdletBinding()]
param([string]$Python = '', [string]$Directorio = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    $argsB4 = @('-m','scripts.practica_cierre.visualizacion_b4','validar')
    if (-not [string]::IsNullOrWhiteSpace($Directorio)) { $argsB4 += @('--directorio',$Directorio) }
    & $exe @argsB4
    if ($LASTEXITCODE -ne 0) { throw "B4: validacion fallida ($LASTEXITCODE)" }
} finally { Pop-Location }

# Auditoria de las trazas del ultimo experimento B3 o una carpeta indicada.
[CmdletBinding()]
param([string]$Python = '', [string]$Directorio = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    $argsB3 = @('-m', 'scripts.practica_cierre.trazas_b3', 'validar')
    if (-not [string]::IsNullOrWhiteSpace($Directorio)) { $argsB3 += @('--directorio', $Directorio) }
    & $exe @argsB3
    if ($LASTEXITCODE -ne 0) { throw "La validacion de trazas B3 fallo ($LASTEXITCODE)" }
} finally { Pop-Location }

# Bloque 4: genera series temporales y mapas de espines de trazas B3.
# No ejecuta C y nunca sobrescribe datos historicos ni trazas.
[CmdletBinding()]
param(
    [string]$Python = '',
    [string]$DirectorioTrazas = '',
    [ValidateRange(72,300)][int]$Dpi = 160,
    [ValidateRange(2,12)][int]$Paneles = 5
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    $argsB4 = @('-m','scripts.practica_cierre.visualizacion_b4','generar',
                '--dpi', [string]$Dpi, '--paneles', [string]$Paneles)
    if (-not [string]::IsNullOrWhiteSpace($DirectorioTrazas)) {
        $argsB4 += @('--directorio-trazas', $DirectorioTrazas)
    }
    & $exe @argsB4
    if ($LASTEXITCODE -ne 0) { throw "B4: generacion fallida ($LASTEXITCODE)" }
} finally { Pop-Location }

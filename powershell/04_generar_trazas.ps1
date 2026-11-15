# Bloque 3: registra configuraciones y eventos reales de los cuatro motores.
# No modifica simulator/src, los CSV historicos ni results/snapshots/.
[CmdletBinding()]
param(
    [string]$Python = '',
    [ValidateRange(4,1024)][int]$L = 16,
    [double]$T = 1.5,
    [double]$J = 1.0,
    [double]$H = -3.0,
    [ValidateRange(1,100000000)][int]$Stride = 8,
    [ValidateSet('ambos','standard','nfold')][string]$Algoritmos = 'ambos',
    [ValidateSet('ambas','glauber','metropolis')][string]$Dinamicas = 'ambas',
    [ValidateRange(1,100000000)][int]$MaxAttempts = 2000000,
    [ValidateRange(1,100000000)][int]$MaxEvents = 100000,
    [long]$Seed = 1234
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
$inv = [System.Globalization.CultureInfo]::InvariantCulture
$tArg = $T.ToString('G17', $inv)
$jArg = $J.ToString('G17', $inv)
$hArg = $H.ToString('G17', $inv)
Push-Location -LiteralPath $root
try {
    & $exe -m scripts.practica_cierre.trazas_b3 generar --L $L --T $tArg `
        --J $jArg --H $hArg --seed $Seed --stride $Stride `
        --algoritmos $Algoritmos --dinamicas $Dinamicas `
        --max-attempts $MaxAttempts --max-events $MaxEvents
    if ($LASTEXITCODE -ne 0) { throw "La generacion B3 fallo ($LASTEXITCODE). Revisa results/practica_cierre" }
} finally { Pop-Location }

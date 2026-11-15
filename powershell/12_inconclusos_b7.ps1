# Bloque 7: extension prospectiva de los tres casos de T baja.
[CmdletBinding()]
param(
    [string]$Python = '',
    [ValidateSet('piloto','practica')][string]$Perfil = 'piloto',
    [int]$RunsFrio = 0,
    [int]$RunsTemplado = 0,
    [ValidateRange(200,25000)][int]$Bootstrap = 1800,
    [ValidateRange(1,9223372036854775807)][long]$MaxAttempts = 100000000,
    [long]$Seed = 2026111507
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
$cmdargs = @('-m','scripts.practica_cierre.inconclusos_b7','generar',
             '--perfil',$Perfil,'--bootstrap',[string]$Bootstrap,
             '--max-attempts',[string]$MaxAttempts,'--seed',[string]$Seed)
if ($PSBoundParameters.ContainsKey('RunsFrio')) {
    if ($RunsFrio -lt 2) { throw 'RunsFrio debe ser >=2' }
    $cmdargs += @('--runs-frio',[string]$RunsFrio)
}
if ($PSBoundParameters.ContainsKey('RunsTemplado')) {
    if ($RunsTemplado -lt 2) { throw 'RunsTemplado debe ser >=2' }
    $cmdargs += @('--runs-templado',[string]$RunsTemplado)
}
Push-Location -LiteralPath $root
try {
    & $exe @cmdargs
    if ($LASTEXITCODE -ne 0) { throw "Bloque 7 fallo (exit $LASTEXITCODE). Consultar results/practica_cierre/" }
}
finally { Pop-Location }

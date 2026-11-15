# Bloque 6: simular barrido de campo H en carpeta NUEVA; motor historico sin modificar.
[CmdletBinding()]
param(
    [string]$Python = '',
    [ValidateSet('piloto','practica')][string]$Perfil = 'piloto',
    [int]$L = 0,
    [double]$T = 0,
    [double]$J = 0,
    [int]$Runs = 0,
    [string]$Campos = '',
    [ValidateSet('ambas','glauber','metropolis')][string]$Dinamicas = 'ambas',
    [long]$MaxAttempts = 0,
    [long]$Seed = 20261115,
    [ValidateRange(100,10000)][int]$Bootstrap = 800
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
$inv = [System.Globalization.CultureInfo]::InvariantCulture
$cmdargs = @('-m','scripts.practica_cierre.barrido_campo_b6','generar',
             '--perfil',$Perfil,'--dinamicas',$Dinamicas,'--seed',[string]$Seed,
             '--bootstrap',[string]$Bootstrap)
if ($PSBoundParameters.ContainsKey('L')) { $cmdargs += @('--L',[string]$L) }
if ($PSBoundParameters.ContainsKey('T')) { $cmdargs += @('--T',$T.ToString('G17',$inv)) }
if ($PSBoundParameters.ContainsKey('J')) { $cmdargs += @('--J',$J.ToString('G17',$inv)) }
if ($PSBoundParameters.ContainsKey('Runs')) { $cmdargs += @('--runs',[string]$Runs) }
if (-not [string]::IsNullOrWhiteSpace($Campos)) { $cmdargs += ('--campos=' + $Campos) }
if ($PSBoundParameters.ContainsKey('MaxAttempts')) { $cmdargs += @('--max-attempts',[string]$MaxAttempts) }
Push-Location -LiteralPath $root
try {
    & $exe @cmdargs
    if ($LASTEXITCODE -ne 0) { throw "B6: barrido de campo ha fallado (exit $LASTEXITCODE). Revisa ERROR_B6.log." }
} finally { Pop-Location }

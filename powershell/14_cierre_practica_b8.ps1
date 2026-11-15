# Bloque 8: auditoria integral, reconstruccion C, CTest, pytest, hashes, datos y figuras de sintesis.
# No crea nuevas simulaciones ni edita los resultados historicos.
[CmdletBinding()]
param([string]$Python = '', [switch]$Rapida)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$py = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    $argv = @('-m','scripts.practica_cierre.cierre_b8')
    if (-not $Rapida) { $argv += '--tests' }
    & $py @argv
    if ($LASTEXITCODE -ne 0) { throw 'Bloque 8: auditoria fallida. Revisar ESTADO_B8.json en results/practica_cierre/.' }
}
finally { Pop-Location }

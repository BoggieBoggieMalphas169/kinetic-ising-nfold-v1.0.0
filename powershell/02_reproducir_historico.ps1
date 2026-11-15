# Reproduce figures/final y las tablas P08 en una copia temporal aislada.
# NUNCA escribe sobre el original; publica un informe de comparacion SHA-256.
[CmdletBinding()]
param([string]$Python = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Invoke-IsingDriver -Accion reproducir -Python $Python

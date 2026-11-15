# Primer bloque: compilacion C, CTest, pytest, integridad del snapshot.
# Uso desde cualquier directorio: & '.../powershell/01_validar.ps1'
[CmdletBinding()]
param([string]$Python = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Invoke-IsingDriver -Accion validar -Python $Python

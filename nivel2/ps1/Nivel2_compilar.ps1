[CmdletBinding()]
param([string]$Python='python')
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Nivel2_master.ps1') -Accion Compilar @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'Compilacion o tests fallidos' }

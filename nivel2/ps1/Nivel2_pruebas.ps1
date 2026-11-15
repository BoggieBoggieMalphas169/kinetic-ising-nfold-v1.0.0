[CmdletBinding()]
param([string]$Python='python')
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Nivel2_master.ps1') -Accion Pruebas @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'Tests fallidos' }

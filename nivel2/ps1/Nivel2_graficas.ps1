[CmdletBinding()]
param([string]$Python='python',[int]$Bootstrap=400)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Nivel2_master.ps1') -Accion Graficas @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'Fallo al generar figuras' }

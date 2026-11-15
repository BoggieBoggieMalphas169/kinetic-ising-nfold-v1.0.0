[CmdletBinding()]
param([string]$Python='python',[int]$L=32,[double]$T=1.5,[double]$J=1.,
      [double]$H=-0.75,[string[]]$Dynamics=@('glauber'),
      [long]$Seed=20261115,[long]$TraceEvery=10,
      [long]$SnapshotEvery=200,[long]$MaxFrames=120,[long]$MaxSteps=0)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Nivel2_master.ps1') -Accion Trazas @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'Fallo al generar trazas' }

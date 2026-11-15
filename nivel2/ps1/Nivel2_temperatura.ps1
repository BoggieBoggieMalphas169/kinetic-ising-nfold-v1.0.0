[CmdletBinding()]
param([string]$Python='python',[int]$L=32,[double]$J=1.,
      [double[]]$TValues=@(1.0,1.2,1.5,1.8,2.1),
      [double[]]$HValues=@(-0.75,-3.),
      [string[]]$Dynamics=@('glauber','metropolis'),
      [int]$Runs=100,[long]$Seed=20261115,[long]$MaxAttempts=0)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Nivel2_master.ps1') -Accion Temperatura @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'Fallo barrido de temperatura' }

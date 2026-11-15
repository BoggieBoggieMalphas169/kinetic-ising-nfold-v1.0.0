[CmdletBinding()]
param([string]$Python='python',[double]$T=1.5,[double]$J=1.,
      [int[]]$LValues=@(8,16,32,64,128),
      [double[]]$HValues=@(-0.75,-3.),
      [string[]]$Dynamics=@('glauber','metropolis'),
      [int]$Runs=100,[long]$Seed=20261115,[long]$MaxAttempts=0)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Nivel2_master.ps1') -Accion Tamano @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'Fallo barrido de tamano' }

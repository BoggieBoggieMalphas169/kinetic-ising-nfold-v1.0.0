[CmdletBinding()]
param([string]$Python='python',[int]$L=32,[double]$T=1.5,[double]$J=1.,
      [double[]]$HValues=@(-0.75,-1.,-1.5,-2.,-3.),
      [string[]]$Dynamics=@('glauber','metropolis'),[int]$Runs=100,
      [long]$Seed=20261115,[long]$MaxAttempts=0)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Nivel2_master.ps1') -Accion Campo @PSBoundParameters
if ($LASTEXITCODE -ne 0) { throw 'Fallo al realizar la medida' }

# Nivel 2 de Ising: menu de medidas y graficas. Ejecutar desde cualquier ruta.
# Compatible con Windows PowerShell 5.1 y PowerShell 7.
[CmdletBinding()]
param(
    [ValidateSet('Menu','Compilar','Historicas','Campo','Temperatura','Tamano','Trazas','Graficas','Pruebas','Demo')]
    [string]$Accion = 'Menu',
    [string]$Python = 'python',
    [int]$L = 32,
    [double]$T = 1.5,
    [double]$J = 1.0,
    [double]$H = -0.75,
    [double[]]$HValues = @(-0.75,-1.0,-1.5,-2.0,-3.0),
    [double[]]$TValues = @(1.0,1.2,1.5,1.8,2.1),
    [int[]]$LValues = @(8,16,32,64,128),
    [string[]]$Dynamics = @('glauber','metropolis'),
    [int]$Runs = 100,
    [long]$Seed = 20261115,
    [long]$MaxAttempts = 0,
    [long]$MaxSteps = 0,
    [long]$TraceEvery = 10,
    [long]$SnapshotEvery = 200,
    [long]$MaxFrames = 120,
    [int]$Bootstrap = 400
)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Invariant = [Globalization.CultureInfo]::InvariantCulture
function F([double]$Number) { return $Number.ToString('R', $Invariant) }
function Invoke-Nivel2([string]$Selected) {
    $actionMap = @{
        Compilar='compile'; Historicas='historical'; Campo='field';
        Temperatura='temperature'; Tamano='size'; Trazas='trace';
        Graficas='plot'; Pruebas='validate'; Demo='all-quick'
    }
    $command = $actionMap[$Selected]
    if (-not $command) { throw "Accion desconocida: $Selected" }
    $cmdArgs = @('-m','nivel2.scripts.run_level2',$command,'--root',$Repo,
                 '--L',"$L",'--T',(F $T),'--J',(F $J),'--H',(F $H),
                 '--runs',"$Runs",'--seed',"$Seed",'--bootstrap',"$Bootstrap",
                 '--max-attempts',"$MaxAttempts",'--max-steps',"$MaxSteps",
                 '--trace-every',"$TraceEvery",'--snapshot-every',"$SnapshotEvery",
                 '--max-frames',"$MaxFrames",'--dynamics')
    $cmdArgs += $Dynamics
    $cmdArgs += '--H-values'
    foreach ($value in $HValues) { $cmdArgs += (F $value) }
    $cmdArgs += '--T-values'
    foreach ($value in $TValues) { $cmdArgs += (F $value) }
    $cmdArgs += '--L-values'
    foreach ($value in $LValues) { $cmdArgs += "$value" }
    Write-Host "`n[NIVEL 2] $Selected" -ForegroundColor Cyan
    Push-Location $Repo
    try {
        & $Python @cmdArgs
        if ($LASTEXITCODE -ne 0) { throw "Fallo del proceso ($LASTEXITCODE). Se conservan los datos anteriores." }
    } finally { Pop-Location }
}
if ($Accion -ne 'Menu') { Invoke-Nivel2 $Accion; return }
while ($true) {
    Write-Host "`n========================================================"
    Write-Host ' ISING NIVEL 2 - Medidas y generacion de figuras'
    Write-Host '========================================================'
    Write-Host ' 1  Compilar C en Release + CTest'
    Write-Host ' 2  Figuras solo con los CSV historicos (sin simular)'
    Write-Host ' 3  Medir nuevo barrido de campo H (datos aislados)'
    Write-Host ' 4  Medir trayectorias y snapshots (ambos motores)'
    Write-Host ' 5  Regenerar TODAS las figuras de datos disponibles'
    Write-Host ' 6  CTest (validar simulador compilado)'
    Write-Host ' 7  Demo pequena: compilar, medir, trazar y graficar'
    Write-Host ' 8  NUEVO barrido termico T (rehacer datos de Arrhenius)'
    Write-Host ' 9  NUEVO barrido de tamano L (rehacer costes y speed-up)'
    Write-Host ' 0  Salir'
    Write-Host "Parametros: L=$L, T=$T, H=$H, runs=$Runs, seed=$Seed, dinamicas=$($Dynamics -join ',')"
    Write-Host 'NOTA: cada medicion y cada lote de figuras se guarda en carpeta nueva.'
    $option = Read-Host 'Opcion'
    $selected = switch ($option) {
        '1' {'Compilar'} '2' {'Historicas'} '3' {'Campo'} '4' {'Trazas'}
        '5' {'Graficas'} '6' {'Pruebas'} '7' {'Demo'}
        '8' {'Temperatura'} '9' {'Tamano'} '0' {'Salir'}
        default {'Desconocida'}
    }
    if ($selected -eq 'Salir') { break }
    if ($selected -eq 'Desconocida') { Write-Warning 'Opcion no valida'; continue }
    try { Invoke-Nivel2 $selected }
    catch { Write-Host "ERROR: $_" -ForegroundColor Red }
}

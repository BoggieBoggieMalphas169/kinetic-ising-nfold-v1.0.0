# Genera cuatro trazas mediante el motor C real v1.0.0 y un GIF comparativo.
# Cada ejecucion usa su propia carpeta: NUNCA borra ni pisa resultados previos.
[CmdletBinding()]
param(
    [ValidateRange(4,200)][int]$L = 32,
    [ValidateRange(0.000001,1000)][double]$T = 1.6,
    [double]$J = 1.0,
    [double]$H = -1.0,
    [ValidateRange(1,1000)][int]$MCSS = 13,
    [ValidateRange(2,500)][int]$Frames = 65,
    [ValidateRange(1,60)][int]$Fps = 9,
    [UInt64]$Seed = 250519,
    [string]$Python = 'python',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
if ($L % 2 -ne 0) { throw 'L debe ser par (el nucleo exige poder alcanzar M=0).' }
if ([double]::IsNaN($T) -or [double]::IsInfinity($T)) { throw 'T no es finita.' }
if ($L -lt 4) { throw 'L debe ser >=4.' }
$root = $PSScriptRoot
$build = Join-Path $root 'simulator\build_animations'
if (-not $SkipBuild) {
    Write-Host '[1/3] Compilando motor de simulacion y registrador...'
    & cmake -S (Join-Path $root 'simulator') -B $build -DCMAKE_BUILD_TYPE=Release
    if ($LASTEXITCODE -ne 0) { throw 'Error al configurar CMake.' }
    & cmake --build $build --config Release --target ising_animation_trace
    if ($LASTEXITCODE -ne 0) { throw 'Error al compilar el registrador.' }
}
$exes = @(
    (Join-Path $build 'Release\ising_animation_trace.exe'),
    (Join-Path $build 'ising_animation_trace.exe'),
    (Join-Path $build 'ising_animation_trace')
)
$exe = $exes | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) { throw 'No se encuentra ising_animation_trace. Compila con CMake primero.' }
& $Python -c 'import numpy,matplotlib,PIL'
if ($LASTEXITCODE -ne 0) {
    throw "Faltan dependencias. Usa: $Python -m pip install numpy matplotlib pillow"
}
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$run = Join-Path $root ("results\animations\{0}_{1}" -f $stamp, [guid]::NewGuid().ToString('N').Substring(0,6))
New-Item -ItemType Directory -Path $run | Out-Null
Write-Host "[2/3] Generando trazas (L=$L, T=$T, H=$H, MCSS=$MCSS)..."
# PowerShell invoca las funciones reales de los modulos standard_mc/nfold via el registrador.
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$Larg = $L.ToString($culture)
$Targ = $T.ToString($culture)
$Jarg = $J.ToString($culture)
$Harg = $H.ToString($culture)
$MCSSarg = $MCSS.ToString($culture)
$Seedarg = $Seed.ToString($culture)
foreach ($dyn in @('glauber', 'metropolis')) {
    foreach ($algorithm in @('standard', 'nfold')) {
        $csv = Join-Path $run "${dyn}_${algorithm}.csv"
        & $exe $algorithm $dyn $Larg $Targ $Jarg $Harg $MCSSarg $Seedarg $csv
        if ($LASTEXITCODE -ne 0) { throw "Fallo en simulacion: $dyn / $algorithm" }
    }
}
Write-Host '[3/3] Renderizando GIF y PNG...'
$gif = Join-Path $run 'ising_cuatro_dinamicas.gif'
& $Python (Join-Path $root 'scripts\render_animation.py') `
    --trace-root $run --L $Larg --T $Targ --J $Jarg --H $Harg `
    --mcss $MCSSarg --frames $Frames --fps $Fps --output $gif
if ($LASTEXITCODE -ne 0) { throw 'Fallo al crear el GIF.' }
$metadata = [ordered]@{
    version = '1.0.0'; source = 'ising_core real (C)';
    L = $L; T = $T; J = $J; H = $H; MCSS = $MCSS;
    Frames = $Frames; Fps = $Fps; Seed = $Seed;
    time = (Get-Date).ToString('o');
    stop = 'first-passage M=0, matching v1.0.0';
}
$metadata | ConvertTo-Json | Set-Content -Path (Join-Path $run 'parametros.json') -Encoding UTF8
Write-Host "TERMINADO. Resultados nuevos en: $run" -ForegroundColor Green
Write-Host "GIF: $gif"

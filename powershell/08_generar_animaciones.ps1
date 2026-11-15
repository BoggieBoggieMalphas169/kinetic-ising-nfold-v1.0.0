# Bloque 5: GIF/MP4 basados en eventos fisicos B3 validados.
[CmdletBinding()]
param(
    [string]$Python = '',
    [string]$DirectorioTrazas = '',
    [ValidateRange(2,30)][int]$Fps = 12,
    [ValidateRange(8,240)][int]$Frames = 64,
    [ValidateRange(72,180)][int]$Dpi = 96,
    [ValidateSet('gif','mp4','ambos')][string]$Formato = 'ambos'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
$exe = Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    $paramsB5 = @('-m','scripts.practica_cierre.animaciones_b5','generar',
                  '--fps',[string]$Fps,'--frames',[string]$Frames,
                  '--dpi',[string]$Dpi,'--formato',$Formato)
    if (-not [string]::IsNullOrWhiteSpace($DirectorioTrazas)) {
        $paramsB5 += @('--directorio-trazas',$DirectorioTrazas)
    }
    & $exe @paramsB5
    if ($LASTEXITCODE -ne 0) {
        throw 'B5: no se han podido generar/validar animaciones. Ejecuta: python -m pip install -r requirements_animaciones.txt'
    }
} finally { Pop-Location }

# Crear/actualizar dependencias en .venv. La ejecucion es deliberadamente explicita.
[CmdletBinding()]
param([string]$Python = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Get-IsingRoot
Push-Location -LiteralPath $root
try {
    $venv = Join-Path $root '.venv'
    if (-not (Test-Path -LiteralPath $venv -PathType Container)) {
        $launcher = Resolve-IsingPython -Root $root -Python $Python
        & $launcher -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python.' }
    }
    $candidate = Join-Path $venv 'Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { $candidate = Join-Path $venv 'bin/python' }
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { throw 'Entorno virtual incompleto: no se encontro python.' }
    $venvPython = $candidate
    & $venvPython -m pip install -r (Join-Path $root 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de dependencias.' }
    Write-Host "Entorno preparado en $venv" -ForegroundColor Green
}
finally { Pop-Location }

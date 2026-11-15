# Utilidades del bloque 1. Dot-source desde la carpeta powershell/.
Set-StrictMode -Version Latest
$script:IsingPowerShellDirectory = $PSScriptRoot

function Get-IsingRoot {
    $root = [System.IO.Path]::GetFullPath((Join-Path $script:IsingPowerShellDirectory '..'))
    if (-not (Test-Path -LiteralPath (Join-Path $root 'release/release_manifest.csv') -PathType Leaf)) {
        throw "No se ha encontrado la release completa en $root"
    }
    return $root
}

function Resolve-IsingPython {
    param([string]$Root, [string]$Python = '')

    if (-not [string]::IsNullOrWhiteSpace($Python)) {
        if (Test-Path -LiteralPath $Python -PathType Leaf) {
            return (Resolve-Path -LiteralPath $Python).Path
        }
        $found = Get-Command $Python -ErrorAction SilentlyContinue
        if ($null -ne $found) { return $found.Source }
        throw "No existe el interprete Python indicado: $Python"
    }
    foreach ($venvPath in @((Join-Path $Root '.venv/Scripts/python.exe'), (Join-Path $Root '.venv/bin/python'))) {
        if (Test-Path -LiteralPath $venvPath -PathType Leaf) { return $venvPath }
    }
    $found = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $found) { return $found.Source }
    throw 'No se encontro Python. Instala Python 3.10+ o usa -Python con la ruta del ejecutable.'
}

function Invoke-IsingDriver {
    param([ValidateSet('validar', 'reproducir')][string]$Accion,
          [string]$Python = '')
    $root = Get-IsingRoot
    $pythonExe = Resolve-IsingPython -Root $root -Python $Python
    $driver = Join-Path $root 'scripts/practica_cierre/validar_baseline.py'
    Push-Location -LiteralPath $root
    try {
        & $pythonExe $driver $Accion
        $code = $LASTEXITCODE
        if ($code -ne 0) { throw "La accion $Accion fallo (exit code $code). Consulta results/practica_cierre/." }
    }
    finally {
        Pop-Location
    }
}

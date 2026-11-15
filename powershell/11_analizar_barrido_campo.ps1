# B6: regenera figuras y estadisticas en carpeta nueva sin sobrescribir datos.
[CmdletBinding()]
param([string]$Python='', [Parameter(Mandatory=$true)][string]$DirectorioBarrido)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root=Get-IsingRoot
$exe=Resolve-IsingPython -Root $root -Python $Python
Push-Location -LiteralPath $root
try {
    & $exe -m scripts.practica_cierre.barrido_campo_b6 analizar --directorio $DirectorioBarrido
    if ($LASTEXITCODE -ne 0) { throw "B6: analisis fallo (exit $LASTEXITCODE)" }
} finally { Pop-Location }

#requires -Version 5.1
<#
 Ising: diagnostico y recopilacion no destructiva de figuras.
 Uso, desde la raiz del repositorio:
   .\Ising_Localizar_y_Recopilar_Figuras.ps1
   .\Ising_Localizar_y_Recopilar_Figuras.ps1 -Copiar
 La segunda forma copia imagenes y videos NO ubicados en figures/ a
 figures/generadas/, manteniendo su ruta relativa para evitar colisiones.
 No modifica ni borra archivos de origen ni toca resultados cientificos.
#>
[CmdletBinding()]
param(
    [string]$Repositorio = (Get-Location).Path,
    [switch]$Copiar,
    [int]$Mostrar = 35
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$raiz = (Resolve-Path -LiteralPath $Repositorio).Path.TrimEnd('\','/')
if (-not (Test-Path -LiteralPath (Join-Path $raiz 'simulator') -PathType Container)) {
    throw "No encuentro 'simulator/' en '$raiz'. Ejecuta el script desde la raiz del repositorio o pasa -Repositorio 'RUTA'."
}

$exts = @('.png','.pdf','.svg','.jpg','.jpeg','.webp','.gif','.mp4')
$ignore = '(^|/)(\.git|\.venv[^/]*|venv|build|__pycache__|node_modules)(/|$)'
$archivos = @(
    Get-ChildItem -LiteralPath $raiz -Recurse -File -ErrorAction Stop |
    Where-Object {
        $rel = $_.FullName.Substring($raiz.Length).TrimStart('\','/') -replace '\\','/'
        ($exts -contains $_.Extension.ToLowerInvariant()) -and ($rel -notmatch $ignore)
    } |
    Sort-Object LastWriteTime -Descending
)

Write-Host "`n===== ISING: LOCALIZADOR DE FIGURAS =====" -ForegroundColor Cyan
Write-Host "Repositorio: $raiz"
Write-Host "Archivos graficos y videos encontrados: $($archivos.Count)"

$hist = @($archivos | Where-Object { $_.FullName.Substring($raiz.Length).TrimStart('\','/') -replace '\\','/' -match '^figures/' })
$nuevos = @($archivos | Where-Object { $_.FullName.Substring($raiz.Length).TrimStart('\','/') -replace '\\','/' -notmatch '^figures/' })
Write-Host "Ya ubicados en figures/: $($hist.Count)"
Write-Host "Localizados fuera de figures/: $($nuevos.Count)"

if ($archivos.Count -gt 0) {
    Write-Host "`nPor formato:"
    $archivos | Group-Object Extension | Sort-Object Name | ForEach-Object {
        Write-Host ('  {0,-7} {1,5}' -f $_.Name.ToLowerInvariant(), $_.Count)
    }
    Write-Host "`nArchivos mas recientes (rutas relativas):"
    $archivos | Select-Object -First ([Math]::Max(0,$Mostrar)) | ForEach-Object {
        $rel = $_.FullName.Substring($raiz.Length).TrimStart('\','/')
        Write-Host ('  {0:yyyy-MM-dd HH:mm}  {1}' -f $_.LastWriteTime, $rel)
    }
}

if (-not $Copiar) {
    Write-Host "`nNo se ha copiado nada (modo diagnostico)." -ForegroundColor Yellow
    Write-Host "Para crear figures/generadas/ ejecuta:" -ForegroundColor Yellow
    Write-Host '  .\Ising_Localizar_y_Recopilar_Figuras.ps1 -Copiar'
    return
}

$destinoBase = Join-Path $raiz 'figures\generadas'
New-Item -ItemType Directory -Path $destinoBase -Force | Out-Null
$indice = New-Object 'System.Collections.Generic.List[object]'
$copiados = 0
$identicos = 0
$versionados = 0

foreach ($src in $nuevos) {
    $rel = ($src.FullName.Substring($raiz.Length).TrimStart('\','/') -replace '\\','/')
    $destino = Join-Path $destinoBase ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
    $dir = Split-Path -Parent $destino
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $estado = 'copiado'
    if (Test-Path -LiteralPath $destino -PathType Leaf) {
        $hashSrc = (Get-FileHash -LiteralPath $src.FullName -Algorithm SHA256).Hash
        $hashDst = (Get-FileHash -LiteralPath $destino -Algorithm SHA256).Hash
        if ($hashSrc -eq $hashDst) {
            $estado = 'ya_igual'
            $identicos++
        }
        else {
            # Nunca sobreescribir una figura generada anteriormente.
            $base = [IO.Path]::GetFileNameWithoutExtension($destino)
            $ext = [IO.Path]::GetExtension($destino)
            $tag = $hashSrc.Substring(0,10).ToLowerInvariant()
            $destino = Join-Path $dir ("{0}__{1}{2}" -f $base,$tag,$ext)
            if (Test-Path -LiteralPath $destino) {
                if ((Get-FileHash -LiteralPath $destino -Algorithm SHA256).Hash -eq $hashSrc) {
                    $estado = 'ya_igual_versionada'
                    $identicos++
                }
                else {
                    throw "Colision inesperada de nombre en $destino"
                }
            } else {
                $estado = 'copiado_versionado'
                $versionados++
            }
        }
    }
    if ($estado -like 'copiado*') {
        Copy-Item -LiteralPath $src.FullName -Destination $destino -ErrorAction Stop
        $copiados++
    }
    $destinoRel = $destino.Substring($raiz.Length).TrimStart('\','/') -replace '\\','/'
    $indice.Add([pscustomobject]@{
        original = $rel
        copia = $destinoRel
        formato = $src.Extension.ToLowerInvariant()
        bytes = $src.Length
        estado = $estado
    })
}

$indiceRuta = Join-Path $destinoBase '_indice_figuras.csv'
$indice | Export-Csv -LiteralPath $indiceRuta -NoTypeInformation -Encoding UTF8
Write-Host "`nRecopilacion terminada." -ForegroundColor Green
Write-Host "Nuevos archivos copiados: $copiados"
Write-Host "Copias ya identicas: $identicos"
Write-Host "Archivos versionados por cambio: $versionados"
Write-Host "Destino: $destinoBase"
Write-Host "Indice: $indiceRuta"
Write-Host 'No se ha modificado ningun resultado original.'

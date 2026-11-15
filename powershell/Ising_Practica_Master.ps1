# Menu maestro incremental. Solo ofrece operaciones realmente implementadas.
[CmdletBinding()]
param([string]$Python = '')
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
while ($true) {
    Write-Host ''
    Write-Host '=============================================' -ForegroundColor Cyan
    Write-Host ' ISING STANDARD vs N-FOLD | PRACTICA - CIERRE BLOQUE 8' -ForegroundColor Cyan
    Write-Host '=============================================' -ForegroundColor Cyan
    Write-Host '1. Preparar entorno Python (.venv)'
    Write-Host '2. Validar release C/Python y snapshot'
    Write-Host '3. Reproducir figuras y tablas P08 en copia segura'
    Write-Host '4. Generar TODAS las graficas Nivel 2 disponibles (N2.1-N2.6)'
    Write-Host '5. Nivel 2: supervivencia, ECDF y distribuciones (N2.1-N2.3)'
    Write-Host '6. Nivel 2: activacion, costo y speed-up (N2.4-N2.6)'
    Write-Host '7. Bloque 3: generar trazas reales (4 combinaciones)'
    Write-Host '8. Bloque 3: validar las ultimas trazas'
    Write-Host '9. Bloque 4: generar graficas M(t), E(t) y mapas de espines'
    Write-Host '10. Bloque 4: validar las ultimas figuras temporales'
    Write-Host '11. Bloque 5: generar GIF/MP4 de las cuatro dinamicas y comparaciones'
    Write-Host '12. Bloque 5: validar GIF/MP4, integridad y tiempos MCSS'
    Write-Host '13. Bloque 6: ejecutar barrido de H (perfil piloto seguro)'
    Write-Host '14. Bloque 6: analizar un barrido anterior (nuevas figuras)'
    Write-Host '15. Bloque 7: ampliar los tres INCONCLUSIVE (piloto seguro)'
    Write-Host '16. Bloque 7: reanalizar una campaña anterior'
    Write-Host '17. Bloque 8: auditoria final C/Python/datos/figuras'
    Write-Host '0. Salir'
    Write-Host 'Animaciones B5: instalar deps con pip install -r requirements_animaciones.txt'
    $choice = Read-Host 'Selecciona opcion'
    if ($choice -eq '0') { break }
    try {
        switch ($choice) {
            '1' { & (Join-Path $here '00_preparar_entorno.ps1') -Python $Python }
            '2' { & (Join-Path $here '01_validar.ps1') -Python $Python }
            '3' { & (Join-Path $here '02_reproducir_historico.ps1') -Python $Python }
            '4' { & (Join-Path $here '03_generar_nivel2.ps1') -Python $Python -Solo all }
            '5' { & (Join-Path $here '03_generar_nivel2.ps1') -Python $Python -Solo distribuciones }
            '6' { & (Join-Path $here '03_generar_nivel2.ps1') -Python $Python -Solo rendimiento }
            '7' { & (Join-Path $here '04_generar_trazas.ps1') -Python $Python }
            '8' { & (Join-Path $here '05_validar_trazas.ps1') -Python $Python }
            '9' { & (Join-Path $here '06_generar_visualizaciones.ps1') -Python $Python }
            '10' { & (Join-Path $here '07_validar_visualizaciones.ps1') -Python $Python }
            '11' { & (Join-Path $here '08_generar_animaciones.ps1') -Python $Python }
            '12' { & (Join-Path $here '09_validar_animaciones.ps1') -Python $Python }
            '13' { & (Join-Path $here '10_barrido_campo.ps1') -Python $Python -Perfil piloto }
            '14' {
                $path = Read-Host 'Ruta del directorio de barrido B6 existente'
                if ([string]::IsNullOrWhiteSpace($path)) { throw 'Ruta vacia' }
                & (Join-Path $here '11_analizar_barrido_campo.ps1') -Python $Python -DirectorioBarrido $path
            }
            '15' { & (Join-Path $here '12_inconclusos_b7.ps1') -Python $Python -Perfil piloto }
            '16' {
                $path = Read-Host 'Ruta del directorio de campaña B7 existente'
                if ([string]::IsNullOrWhiteSpace($path)) { throw 'Ruta vacia' }
                & (Join-Path $here '13_analizar_inconclusos_b7.ps1') -Python $Python -DirectorioB7 $path
            }
            '17' { & (Join-Path $here '14_cierre_practica_b8.ps1') -Python $Python }
            default { Write-Warning 'Opcion no valida.' }
        }
    }
    catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
        Write-Host 'Se ha conservado el informe parcial, si se pudo generar.'
    }
}

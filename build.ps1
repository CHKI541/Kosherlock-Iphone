$env:SETUPTOOLS_USE_DISTUTILS = "stdlib"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Limpiando compilaciones anteriores..." -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "Compilando KosherLock_iOS.exe con PyInstaller..." -ForegroundColor Yellow
pyinstaller --noconfirm `
    --onefile `
    --windowed `
    --collect-all customtkinter `
    --collect-all qrcode `
    --collect-all PIL `
    --name "KosherLock_iOS" `
    src\main.py

if (Test-Path "dist\KosherLock_iOS.exe") {
    Write-Host "Compilacion exitosa!" -ForegroundColor Green
    Copy-Item "dist\KosherLock_iOS.exe" ".\KosherLock_iOS.exe" -Force
    Write-Host "Ejecutable copiado a la raiz del proyecto: KosherLock_iOS.exe" -ForegroundColor Green
    Get-Item ".\KosherLock_iOS.exe" | Select-Object FullName, Length, LastWriteTime
} else {
    Write-Host "Error: No se encontro el archivo compilado en dist." -ForegroundColor Red
}

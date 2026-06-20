# PassSimple build script
# Usage (from the project root): .\build.ps1

Set-StrictMode -Version 1

# Clean previous PyInstaller artefacts so we always get a reproducible build.
Remove-Item -Recurse -Force "build\dist"  -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "build\build" -ErrorAction SilentlyContinue

Write-Host "Building PassSimple.exe ..." -ForegroundColor Cyan

pyinstaller build\passsimple.spec `
    --distpath build\dist `
    --workpath build\build `
    --noconfirm

$exe = "build\dist\PassSimple.exe"
if (Test-Path $exe) {
    $size = (Get-Item $exe).Length / 1MB
    Write-Host ("Build erfolgreich: {0} ({1:N1} MB)" -f $exe, $size) -ForegroundColor Green
} else {
    Write-Host "Build fehlgeschlagen - kein PassSimple.exe in build\dist\" -ForegroundColor Red
    exit 1
}

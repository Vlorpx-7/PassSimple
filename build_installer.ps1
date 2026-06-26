# PassSimple full build: app + NSIS installer
# Usage (from project root): .\build_installer.ps1

Set-StrictMode -Version 1

# 1. Build the app .exe first
& .\build.ps1
if (-not (Test-Path "build\dist\PassSimple.exe")) {
    Write-Host "App-Build fehlgeschlagen, Installer abgebrochen" -ForegroundColor Red
    exit 1
}

# 2. Locate makensis
$makensis = "C:\Program Files (x86)\NSIS\makensis.exe"
if (-not (Test-Path $makensis)) {
    Write-Host "NSIS nicht gefunden: $makensis" -ForegroundColor Red
    Write-Host "NSIS 3.x von https://nsis.sourceforge.io herunterladen und installieren." -ForegroundColor Yellow
    exit 1
}

# 3. Build the installer
Write-Host "Baue Installer..." -ForegroundColor Cyan
& $makensis "installer\passsimple.nsi"

$installer = "build\dist\PassSimple-Setup-0.2.0.exe"
if (Test-Path $installer) {
    $size = (Get-Item $installer).Length / 1MB
    Write-Host ("Installer fertig: {0} ({1:N1} MB)" -f $installer, $size) -ForegroundColor Green
} else {
    Write-Host "Installer-Build fehlgeschlagen - kein PassSimple-Setup-0.2.0.exe in build\dist\" -ForegroundColor Red
    exit 1
}

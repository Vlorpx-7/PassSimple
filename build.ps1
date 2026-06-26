# PassSimple build script
# Usage (from the project root): .\build.ps1

Set-StrictMode -Version 1

# Clean previous PyInstaller artefacts so we always get a reproducible build.
Remove-Item -Recurse -Force "build\dist"  -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "build\build" -ErrorAction SilentlyContinue

# Inject build metadata so the bundled .exe shows the real commit and date
# instead of falling back to subprocess/git at runtime (which fails in Program Files).
$hash = (git rev-parse --short HEAD).Trim()
$date = (Get-Date -Format "yyyy-MM-dd")
$buildInfoContent = @"
"""Build-time metadata injected by build.ps1 before PyInstaller runs.

In development (default state) COMMIT_HASH is 'dev' and BUILD_DATE is empty.
build.ps1 overwrites this file with the real values before bundling, then
restores the defaults so the working tree stays clean between builds.
Do NOT add this file to .gitignore -- the defaults must be committed.
"""

COMMIT_HASH: str = "$hash"
BUILD_DATE: str = "$date"
"@
Set-Content -Path src\_build_info.py -Value $buildInfoContent -Encoding UTF8
Write-Host "Build info: $hash ($date)" -ForegroundColor DarkGray

Write-Host "Building PassSimple.exe ..." -ForegroundColor Cyan

pyinstaller build\passsimple.spec `
    --distpath build\dist `
    --workpath build\build `
    --noconfirm

# Restore _build_info.py to defaults unconditionally so the working tree
# stays clean regardless of whether the build succeeded or failed.
$defaultContent = @"
"""Build-time metadata injected by build.ps1 before PyInstaller runs.

In development (default state) COMMIT_HASH is 'dev' and BUILD_DATE is empty.
build.ps1 overwrites this file with the real values before bundling, then
restores the defaults so the working tree stays clean between builds.
Do NOT add this file to .gitignore -- the defaults must be committed.
"""

COMMIT_HASH: str = "dev"
BUILD_DATE: str = ""
"@
Set-Content -Path src\_build_info.py -Value $defaultContent -Encoding UTF8

$exe = "build\dist\PassSimple.exe"
if (Test-Path $exe) {
    $size = (Get-Item $exe).Length / 1MB
    Write-Host ("Build erfolgreich: {0} ({1:N1} MB)" -f $exe, $size) -ForegroundColor Green
} else {
    Write-Host "Build fehlgeschlagen - kein PassSimple.exe in build\dist\" -ForegroundColor Red
    exit 1
}

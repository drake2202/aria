Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Building Aria for Windows..."

if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..."
    . .\.venv\Scripts\Activate.ps1
}

pyinstaller --clean -y aria.spec

$arch = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "ia32" }
$artifactName = "Aria-Windows-$arch.zip"
$artifactPath = Join-Path "dist" $artifactName

if (Test-Path $artifactPath) {
    Remove-Item $artifactPath -Force
}

Compress-Archive -Path "dist\aria\*" -DestinationPath $artifactPath -Force

Write-Host "Done! Windows artifact: $artifactPath"

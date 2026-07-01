$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "ExileFilterStudio" `
    --paths "src" `
    "app.py"

Write-Host "Executável criado em dist\ExileFilterStudio\ExileFilterStudio.exe"

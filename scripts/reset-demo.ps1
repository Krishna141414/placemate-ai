# Puts the demo back to its clean state before a recording: removes asked
# questions, agent runs, plans, applications added during demos, events and
# uploaded documents, restores the seeded data and rebuilds the search index.
#
#   .\scripts\reset-demo.ps1
#
# If the backend is running it is stopped first and started again afterwards,
# because it holds the search index in memory.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Backend virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*uvicorn*app.main:app*" }
if ($running) {
    Write-Host "Stopping the running backend..."
    $running | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 1
}

Push-Location $backend
try {
    & $venvPython -m app.seed --reset
    if ($LASTEXITCODE -ne 0) { throw "Reset failed." }
}
finally {
    Pop-Location
}
Write-Host "Demo data reset." -ForegroundColor Green

if ($running) {
    Write-Host "Starting the backend again in a new window..."
    $command = "Set-Location '$backend'; `$host.UI.RawUI.WindowTitle = 'PlaceMate backend'; & '$venvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-Command", $command | Out-Null
}

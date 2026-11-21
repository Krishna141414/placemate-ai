# Starts the backend (FastAPI, port 8000) and the frontend (Next.js, port 3000) together.
#
#   .\scripts\dev.ps1            # or, from the repository root:  npm run dev:all
#
# The backend runs in its own window so its log stays readable; the frontend
# runs here. Close the backend window (or press Ctrl+C in it) to stop it.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Backend virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Frontend packages not installed. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Test-Backend {
    try {
        Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null
        return $true
    }
    catch { return $false }
}

# --- Backend -------------------------------------------------------------
if (Test-Backend) {
    Write-Host "Backend already running on http://127.0.0.1:8000"
}
elseif (Test-Port 8000) {
    Write-Host "Port 8000 is used by another program. Stop it and run this again." -ForegroundColor Red
    exit 1
}
else {
    Write-Host "Starting the backend in a new window..."
    $command = "Set-Location '$backend'; `$host.UI.RawUI.WindowTitle = 'PlaceMate backend'; & '$venvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-NoProfile", "-Command", $command | Out-Null
    # The first start builds the search index and loads two small models.
    $deadline = (Get-Date).AddMinutes(4)
    while (-not (Test-Backend)) {
        if ((Get-Date) -gt $deadline) {
            Write-Host "The backend did not answer within 4 minutes. Check its window for errors." -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "Backend ready on http://127.0.0.1:8000 (API docs at /docs)" -ForegroundColor Green
}

# --- Frontend ------------------------------------------------------------
if (Test-Port 3000) {
    Write-Host "Port 3000 is already in use; the frontend is probably running. Open http://localhost:3000" -ForegroundColor Yellow
    exit 0
}
Write-Host "Starting the frontend on http://localhost:3000 (Ctrl+C to stop)" -ForegroundColor Green
Write-Host "Demo logins: student@placemate.demo / Student@123, coordinator@placemate.demo / Coord@123"
Push-Location $frontend
try {
    npm run dev -- --port 3000
}
finally {
    Pop-Location
}

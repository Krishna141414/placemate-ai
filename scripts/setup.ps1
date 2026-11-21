# One-time setup on Windows: backend virtual environment, Python packages
# (CPU-only PyTorch), frontend packages and a local .env.
#
#   .\scripts\setup.ps1
#   .\scripts\setup.ps1 -Python "py -3.12"     # use another interpreter
#   .\scripts\setup.ps1 -WithBrowsers           # also install Playwright's Chromium for the e2e tests
#
# Safe to run again: it reuses what is already there.

param(
    [string]$Python = "",
    [switch]$WithBrowsers
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

function Write-Step($text) { Write-Host "`n== $text ==" -ForegroundColor Cyan }

# --- Python interpreter --------------------------------------------------
if (-not $Python) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $versions = (& py -0) -join " "
        if ($versions -match "3\.14") { $Python = "py -3.14" }
        elseif ($versions -match "3\.12") { $Python = "py -3.12" }
        else { $Python = "py -3" }
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $Python = "python" }
    else {
        Write-Host "Python was not found. Install Python 3.12 or newer from python.org, then run this again." -ForegroundColor Red
        exit 1
    }
}

Write-Step "Backend virtual environment ($Python)"
if (-not (Test-Path $venvPython)) {
    $parts = $Python.Split(" ")
    $exe = $parts[0]
    $rest = @($parts | Select-Object -Skip 1)
    & $exe @rest -m venv (Join-Path $backend ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}
else {
    Write-Host "Reusing backend\.venv"
}

Write-Step "Python packages (CPU-only PyTorch)"
& $venvPython -m pip install --upgrade pip --quiet
# requirements.txt points pip at the PyTorch CPU wheel index; the CUDA build is never installed.
& $venvPython -m pip install -r (Join-Path $backend "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

Write-Step "Configuration"
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $root ".env.example") $envFile
    Write-Host "Created .env from .env.example. Add GEMINI_API_KEY there to use Gemini (optional)."
}
else {
    Write-Host ".env already exists; left as it is."
}

Write-Step "Frontend packages"
Push-Location $frontend
try {
    npm ci --fetch-retries=5
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
    if ($WithBrowsers) {
        npx playwright install chromium
    }
}
finally {
    Pop-Location
}

Write-Host "`nSetup finished. Start the app with:  .\scripts\dev.ps1" -ForegroundColor Green
Write-Host "The first start downloads the embedding and reranker models (about 170 MB) if they are not cached yet."

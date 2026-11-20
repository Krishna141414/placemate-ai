# Runs the backend test suite with coverage and saves the evidence files to docs/evidence/.
#
#   .\scripts\test.ps1              # everything, including the slow local-LLM test
#   .\scripts\test.ps1 -m "not slow" # skip the test that loads the 0.5B model
#
# Tests never call the Gemini API: they force LLM_PROVIDER=extractive and an empty key.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$evidence = Join-Path $root "docs\evidence"
$python = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Backend virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force $evidence | Out-Null
Push-Location (Join-Path $root "backend")
try {
    & $python -m pytest `
        --cov=app `
        --cov-report=term `
        --cov-report="json:$evidence\coverage.json" `
        --junitxml="$evidence\pytest-junit.xml" `
        -p no:cacheprovider `
        @args | Tee-Object -FilePath "$evidence\pytest-output.txt"
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}

& $python (Join-Path $root "eval\collect_tests.py")
exit $code

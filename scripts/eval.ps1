# Runs the evaluation (baseline vs final), draws the charts and publishes the summary.
#
#   .\scripts\eval.ps1                          # Gemini (needs GEMINI_API_KEY) and the offline extractive run
#   .\scripts\eval.ps1 -Providers extractive    # offline only, no key needed
#
# Results: eval/results/<provider>/ (cases, summary, charts, run.log) and eval/results/summary.json.

param(
    [string[]]$Providers = @("gemini", "extractive")
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Backend virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

$env:PYTHONIOENCODING = "utf-8"
Push-Location $root
try {
    foreach ($provider in $Providers) {
        Write-Host "`n== Evaluating with provider: $provider ==" -ForegroundColor Cyan
        New-Item -ItemType Directory -Force "eval\results\$provider" | Out-Null
        & $python eval\run_eval.py --provider $provider | Tee-Object -FilePath "eval\results\$provider\run.log"
        if ($LASTEXITCODE -ne 0) { throw "Evaluation failed for $provider" }
        & $python eval\charts.py --provider $provider
    }
    & $python eval\publish.py
}
finally {
    Pop-Location
}

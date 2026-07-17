$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONIOENCODING = "utf-8"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = $null

if ($env:CONDA_PREFIX) {
    $ActiveCondaPython = Join-Path $env:CONDA_PREFIX "python.exe"
    if (Test-Path -LiteralPath $ActiveCondaPython) {
        $Python = $ActiveCondaPython
    }
}

if (-not $Python) {
    $DefaultCondaPython = Join-Path $env:USERPROFILE "anaconda3\envs\ai-vision\python.exe"
    if (Test-Path -LiteralPath $DefaultCondaPython) {
        $Python = $DefaultCondaPython
    }
}

if (-not $Python) {
    $Command = Get-Command python -ErrorAction SilentlyContinue
    if ($Command) {
        $Python = $Command.Source
    }
}

if (-not $Python) {
    throw "Python was not found. Run: conda activate ai-vision"
}

Set-Location -LiteralPath $ProjectRoot
& $Python "scripts\check_environment.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python -m ruff check app core scripts tests main.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python -m pytest --cov=app --cov=core --cov-report=term-missing
exit $LASTEXITCODE

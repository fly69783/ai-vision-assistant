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
    throw "Python was not found. Create and activate the ai-vision environment first."
}

Set-Location -LiteralPath $ProjectRoot
& $Python "scripts\check_environment.py"
if ($LASTEXITCODE -ne 0) {
    throw "The environment check failed. Fix the reported items before starting."
}

Write-Host "Web app: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "API docs: http://127.0.0.1:8000/api/v1/docs" -ForegroundColor Cyan
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

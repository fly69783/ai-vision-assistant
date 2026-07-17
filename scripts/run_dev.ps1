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

$LocalVisionEnabled = $env:AI_VISION_LOCAL_VISION_ENABLED -in @("1", "true", "yes", "on")
$UsesLocalVision = $env:AI_VISION_VISION_BACKEND -in @("ollama", "hybrid")
if ($LocalVisionEnabled -and $UsesLocalVision) {
    try {
        $OllamaVersion = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 3
        Write-Host "Ollama ready: $($OllamaVersion.version)" -ForegroundColor Green
    } catch {
        Write-Warning "Local vision is enabled, but Ollama is unavailable. Run scripts\install_local_vlm.ps1 -Enable first."
    }
}

Write-Host "Web app: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "API docs: http://127.0.0.1:8000/api/v1/docs" -ForegroundColor Cyan
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

param(
    [string]$Model = "qwen3-vl:4b-instruct-q4_K_M",
    [switch]$Enable
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

function Find-Ollama {
    $Candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
        (Join-Path $env:ProgramFiles "Ollama\ollama.exe")
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path -LiteralPath $Candidate) { return $Candidate }
    }
    $Command = Get-Command ollama -ErrorAction SilentlyContinue
    if ($Command) { return $Command.Source }
    return $null
}

$Ollama = Find-Ollama
if (-not $Ollama) {
    Write-Host "Ollama is not installed. Installing with winget..." -ForegroundColor Yellow
    winget install --id Ollama.Ollama --exact --silent `
        --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $Ollama = Find-Ollama
}
if (-not $Ollama) { throw "ollama.exe was not found. Open a new terminal and retry." }

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 3 | Out-Null
} catch {
    Write-Host "Starting the Ollama service in the background..." -ForegroundColor Yellow
    Start-Process -FilePath $Ollama -ArgumentList "serve" -WindowStyle Hidden
    $Ready = $false
    foreach ($Attempt in 1..10) {
        Start-Sleep -Milliseconds 500
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 1 | Out-Null
            $Ready = $true
            break
        } catch { }
    }
    if (-not $Ready) { throw "Ollama did not start at http://127.0.0.1:11434." }
}

Write-Host "Pulling and verifying $Model..." -ForegroundColor Cyan
& $Ollama pull $Model
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
$Installed = $Tags.models | Where-Object { $_.name -eq $Model }
if (-not $Installed) { throw "$Model is missing from the local model list." }

if ($Enable) {
    setx AI_VISION_LOCAL_VISION_ENABLED "true" | Out-Null
    setx AI_VISION_VISION_BACKEND "ollama" | Out-Null
    setx AI_VISION_LOCAL_VISION_MODEL $Model | Out-Null
    Write-Host "Local vision settings were saved. Open a new terminal before starting the app." -ForegroundColor Green
} else {
    Write-Host "The model is installed. Add -Enable to save the project settings." -ForegroundColor Green
}

Write-Host "Model: $($Installed.name); disk size: $([math]::Round($Installed.size / 1GB, 2)) GB"

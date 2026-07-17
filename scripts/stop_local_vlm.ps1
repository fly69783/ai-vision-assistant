param(
    [string]$Model = "qwen3-vl:4b-instruct-q4_K_M"
)

$ErrorActionPreference = "Stop"
$Candidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
    (Join-Path $env:ProgramFiles "Ollama\ollama.exe")
)
$Ollama = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $Ollama) {
    $Command = Get-Command ollama -ErrorAction SilentlyContinue
    if ($Command) { $Ollama = $Command.Source }
}
if (-not $Ollama) { throw "Ollama was not found." }

& $Ollama stop $Model
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Stopped $Model. Model files remain on disk."

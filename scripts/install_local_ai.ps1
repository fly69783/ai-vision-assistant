param(
    [switch]$Enable
)

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
    throw "The ai-vision environment was not found. Run: conda activate ai-vision"
}

Set-Location -LiteralPath $ProjectRoot

& $Python -c "import torch, torchvision; print('PyTorch and Torchvision are installed.')"
if ($LASTEXITCODE -ne 0) {
    throw "Install torch and torchvision for this GPU from the official PyTorch selector first."
}

# RapidOCR declares opencv-python, while this project uses opencv-python-headless.
# They share the cv2 namespace, so install the remaining dependencies explicitly
# and install RapidOCR itself with --no-deps.
$OcrDependencies = @(
    "onnxruntime>=1.20,<2",
    "pyclipper>=1.2,<2",
    "Shapely>=2.0,<3",
    "tqdm>=4.60,<5",
    "omegaconf!=2.2.1",
    "colorlog>=6,<7"
)

& $Python -m pip install @OcrDependencies
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python -m pip install "rapidocr>=3.8,<4" --no-deps
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python scripts\check_local_ai.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Enable) {
    setx AI_VISION_DETECTOR_ENABLED "true" | Out-Null
    setx AI_VISION_OCR_ENABLED "true" | Out-Null
    Write-Host "Local AI switches were saved. Open a new terminal before starting the app."
} else {
    Write-Host "Install complete. To enable: powershell -ExecutionPolicy Bypass -File scripts\install_local_ai.ps1 -Enable"
}

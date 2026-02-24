param(
    [string]$Question = "",
    [string]$Model = "",
    [string]$OllamaHost = "",
    [switch]$OpenImage
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Question)) {
    $Question = Read-Host 'Pixel7画面に質問（例: これは何？ このエラーの意味は？）'
}
if ([string]::IsNullOrWhiteSpace($Question)) {
    Write-Host 'Question is empty.' -ForegroundColor Yellow
    exit 2
}

if ([string]::IsNullOrWhiteSpace($Model)) {
    $Model = if ($env:MANA_VISION_MODEL) { $env:MANA_VISION_MODEL } else { 'llava:latest' }
}
if ([string]::IsNullOrWhiteSpace($OllamaHost)) {
    $OllamaHost = if ($env:OLLAMA_HOST) { $env:OLLAMA_HOST } else { 'http://127.0.0.1:11434' }
}

# まずスクショを取る（最新ファイルを拾う）
$ssDir = Join-Path $env:USERPROFILE 'Desktop\screenshots'
& "$PSScriptRoot\pixel7_take_screenshot.ps1" | Out-Null

$after = @()
if (Test-Path $ssDir) {
    $after = Get-ChildItem -Path $ssDir -Filter 'pixel7_screenshot_*.png' -File -ErrorAction SilentlyContinue
}

$img = ($after | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
if (-not $img) {
    Write-Host 'スクショが見つかりません。' -ForegroundColor Yellow
    exit 3
}

if ($OpenImage) {
    Start-Process -FilePath $img.FullName
}

Write-Host ('Image: {0}' -f $img.FullName) -ForegroundColor Cyan
Write-Host ('Model: {0}' -f $Model) -ForegroundColor Gray

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $py) {
    Write-Host 'python/py が見つかりません。' -ForegroundColor Yellow
    exit 4
}

& $py.Source "$PSScriptRoot\pixel7_ask_vision.py" $($img.FullName) --prompt $Question --model $Model --host $OllamaHost

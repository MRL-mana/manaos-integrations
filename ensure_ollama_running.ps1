# Ollama常時起動確保スクリプト
# Ollamaが停止している場合、自動的に起動します

Write-Host "Ollama常時起動確認中..." -ForegroundColor Cyan

# URL（環境変数で上書き可能）
$ollamaBaseUrl = if ($env:OLLAMA_URL) { $env:OLLAMA_URL.TrimEnd('/') } else { "http://127.0.0.1:11434" }

function Get-UriSafe {
    param([string]$Url)
    try {
        return [uri]$Url
    } catch {
        return $null
    }
}

$ollamaUri = Get-UriSafe -Url $ollamaBaseUrl
$ollamaHost = if ($ollamaUri) { $ollamaUri.Host } else { "127.0.0.1" }
$ollamaPort = if ($ollamaUri) { $ollamaUri.Port } else { 11434 }

# Ollamaの起動確認
$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "$ollamaBaseUrl/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    $ollamaRunning = $true
    Write-Host "[OK] Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Ollama is not responding" -ForegroundColor Yellow
}

# ポート確認
$portCheck = Test-NetConnection -ComputerName $ollamaHost -Port $ollamaPort -WarningAction SilentlyContinue -InformationLevel Quiet -ErrorAction SilentlyContinue

if (-not $portCheck -and -not $ollamaRunning) {
    Write-Host "`nOllamaを起動します..." -ForegroundColor Yellow
    
    # Ollamaのパスを検索
    $ollamaPaths = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "C:\Program Files\Ollama\ollama.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Ollama\ollama.exe"
    )
    
    $ollamaPath = $null
    foreach ($path in $ollamaPaths) {
        if (Test-Path $path) {
            $ollamaPath = $path
            break
        }
    }
    
    if ($null -eq $ollamaPath) {
        $ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
        if ($ollamaCheck) {
            $ollamaPath = "ollama"
        }
    }
    
    if ($null -ne $ollamaPath) {
        try {
            Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
            Write-Host "[OK] Ollama started" -ForegroundColor Green
            Start-Sleep -Seconds 5
            
            # 起動確認
            $retryCount = 0
            $maxRetries = 6
            while ($retryCount -lt $maxRetries) {
                try {
                    $response = Invoke-WebRequest -Uri "$ollamaBaseUrl/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
                    Write-Host "[OK] Ollama is now running" -ForegroundColor Green
                    break
                } catch {
                    $retryCount++
                    if ($retryCount -lt $maxRetries) {
                        Start-Sleep -Seconds 5
                    } else {
                        Write-Host "[WARN] Ollama may still be starting up" -ForegroundColor Yellow
                    }
                }
            }
        } catch {
            Write-Host "[ERROR] Failed to start Ollama: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "[ERROR] Ollama executable not found" -ForegroundColor Red
    }
} else {
    Write-Host "`n[OK] Ollama is already running" -ForegroundColor Green
}

Write-Host "`nOllama常時起動確認完了" -ForegroundColor Cyan


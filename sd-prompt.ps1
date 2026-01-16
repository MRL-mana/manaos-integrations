# Stable Diffusion 専用プロンプターコマンド (PowerShell版)
# Uncensored Llama3モデルを使用して画像生成プロンプトを生成

param(
    [string]$Model = "llama3-uncensored",
    [double]$Temperature = 0.9,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Prompt
)

$OllamaUrl = $env:OLLAMA_URL
if ([string]::IsNullOrEmpty($OllamaUrl)) {
    $OllamaUrl = "http://localhost:11434"
}

# 使用方法を表示
function Show-Usage {
    Write-Host @"
使用方法: sd-prompt.ps1 [オプション] <日本語の説明>

Stable Diffusion用の画像生成プロンプトを生成します。

オプション:
  -Model NAME          使用するモデル名（デフォルト: llama3-uncensored）
  -Temperature N       温度パラメータ（0.0-1.0、デフォルト: 0.9）
  -Prompt "説明"       プロンプトの説明

例:
  .\sd-prompt.ps1 "猫がベッドで寝ている"
  .\sd-prompt.ps1 "美しい夕日と海"
  .\sd-prompt.ps1 -Temperature 0.8 "宇宙船が星間空間を航行している"

"@
}

# プロンプトが指定されていない場合
if ($null -eq $Prompt -or $Prompt.Count -eq 0) {
    Write-Host "エラー: プロンプトを指定してください" -ForegroundColor Red
    Show-Usage
    exit 1
}

$UserInput = $Prompt -join " "

# Ollamaサービスが起動しているか確認
try {
    $null = Invoke-WebRequest -Uri "$OllamaUrl/api/tags" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
} catch {
    Write-Host "エラー: Ollamaサービスに接続できません ($OllamaUrl)" -ForegroundColor Red
    Write-Host "Ollamaが起動しているか確認してください" -ForegroundColor Yellow
    exit 1
}

# プロンプト生成のリクエストを作成
$SystemPrompt = "You are an expert at creating detailed prompts for Stable Diffusion image generation. Convert the following Japanese description into a detailed, descriptive English prompt suitable for Stable Diffusion. Include style, composition, lighting, and other relevant details. Output only the prompt, no explanations."

$RequestBody = @{
    model = $Model
    prompt = "$SystemPrompt`n`nJapanese description: $UserInput`n`nEnglish prompt for Stable Diffusion:"
    stream = $false
    options = @{
        temperature = $Temperature
        top_p = 0.95
        top_k = 40
    }
} | ConvertTo-Json -Depth 10

# Ollama APIを呼び出し
Write-Host "プロンプトを生成中..." -ForegroundColor Yellow
Write-Host ""

try {
    $Response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" -Method Post -Body $RequestBody -ContentType "application/json"
    
    $GeneratedPrompt = $Response.response
    
    if ([string]::IsNullOrEmpty($GeneratedPrompt)) {
        Write-Host "エラー: プロンプトの生成に失敗しました" -ForegroundColor Red
        exit 1
    }
    
    # 結果を表示
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "生成されたプロンプト:" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host $GeneratedPrompt -ForegroundColor White
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # クリップボードにコピー
    $GeneratedPrompt | Set-Clipboard
    Write-Host "✓ クリップボードにコピーしました" -ForegroundColor Green
    
} catch {
    Write-Host "エラー: Ollama APIの呼び出しに失敗しました" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
